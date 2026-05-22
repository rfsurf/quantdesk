"""
QuantDesk 数据管线
AKShare → TimescaleDB → 因子预计算

用法:
  python -m backend.data_pipeline sync-daily       # 增量同步
  python -m backend.data_pipeline sync-full         # 全量同步
  python -m backend.data_pipeline precompute-factors # 因子预计算
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd
from sqlalchemy import text, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

# 禁用代理（akshare 数据源都是国内网站）
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(k, None)

from .database import sync_engine
from .factors import compute_all_factors

logger = logging.getLogger(__name__)

SYNC_BATCH_SIZE = 100
AKSHARE_DELAY = 0.3  # 请求间隔，秒（增加避免被封）


def _get_all_symbols() -> list[str]:
    """获取全A股代码列表"""
    import akshare as ak
    try:
        df = ak.stock_info_a_code_name()
        # stock_info_a_code_name 比 stock_zh_a_spot_em 更稳定
        symbols = []
        for _, row in df.iterrows():
            code = str(row["code"]).zfill(6)
            symbols.append(code)
        return symbols
    except Exception:
        # Fallback: 使用 spot 接口
        try:
            df = ak.stock_zh_a_spot_em()
            return df["代码"].tolist()
        except Exception:
            logger.warning("无法获取全A股列表，使用默认股票池")
            return ["000001", "000002", "600000", "600519", "000858"]


def sync_incremental():
    """增量同步：只拉取缺失的交易日数据"""
    import akshare as ak
    from .models import MarketDaily

    today = datetime.now().strftime("%Y%m%d")

    with sync_engine.connect() as conn:
        # 找出最新日期
        max_date = conn.execute(
            text("SELECT COALESCE(MAX(trade_date), '2020-01-01') FROM market_daily")
        ).fetchone()[0]
        if isinstance(max_date, str):
            max_date = pd.Timestamp(max_date).to_pydatetime()
        start_date = (max_date + timedelta(days=1)).strftime("%Y%m%d")
        if start_date >= today:
            logger.info("数据已是最新")
            return

    symbols = _get_all_symbols()
    logger.info(f"增量同步: {start_date} ~ {today}, {len(symbols)} 只股票")

    success = _sync_symbols_range(symbols, start_date, today)
    logger.info(f"增量同步完成: {success}/{len(symbols)} 只")


def sync_full(start_year: int = 2020):
    """全量同步: 拉取全部历史数据"""
    import akshare as ak

    symbols = _get_all_symbols()
    today = datetime.now().strftime("%Y%m%d")
    start_date = f"{start_year}0101"

    logger.info(f"全量同步: {start_date} ~ {today}, {len(symbols)} 只股票")
    logger.warning(f"预计耗时: {len(symbols) * AKSHARE_DELAY / 3600:.1f} 小时")

    success = _sync_symbols_range(symbols, start_date, today)
    logger.info(f"全量同步完成: {success}/{len(symbols)} 只")


def _to_sina_symbol(raw: str) -> str:
    """转换股票代码为新浪格式 (000001 → sz000001, 600000 → sh600000)"""
    code = str(raw).zfill(6)
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def _sync_symbols_range(symbols: List[str], start_date: str, end_date: str) -> int:
    """批量同步股票日线数据到 PostgreSQL（新浪源）"""
    import akshare as ak

    success = 0
    batch = []
    table_name = "market_daily"
    max_retries = 3

    for i, symbol in enumerate(symbols):
        for attempt in range(max_retries):
            try:
                sina_sym = _to_sina_symbol(symbol)
                df = ak.stock_zh_a_daily(
                    symbol=sina_sym,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
                if df is None or df.empty:
                    break  # 停牌/退市

                for _, row in df.iterrows():
                    batch.append({
                        "symbol": symbol,
                        "trade_date": pd.Timestamp(row["date"]).to_pydatetime().date(),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": int(row["volume"]),
                        "amount": float(row.get("amount", 0)),
                    })
                success += 1
                break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                else:
                    # 静默跳过
                    pass

        # 批量写入
        if len(batch) >= 5000 or i == len(symbols) - 1:
            _batch_upsert(table_name, batch)
            batch = []

        # 进度
        if (i + 1) % 200 == 0:
            logger.info(f"  进度: {i+1}/{len(symbols)} ({success} 成功)")

        time.sleep(AKSHARE_DELAY)

    return success


def _batch_upsert(table_name: str, rows: list[dict]):
    """批量 upsert 到数据库（冲突时更新）"""
    if not rows:
        return

    # 动态获取 ORM 表对象
    from . import models
    table = getattr(models, {
        "market_daily": "MarketDaily",
        "factor_cache": "FactorCache",
    }.get(table_name, table_name), None)

    if table is not None and hasattr(table, "__table__"):
        table_obj = table.__table__
    else:
        # Fallback: raw SQL
        table_obj = None

    with sync_engine.connect() as conn:
        if table_obj is not None:
            stmt = pg_insert(table_obj).values(rows)
            update_cols = {k: stmt.excluded[k] for k in rows[0]
                          if k not in ("symbol", "trade_date", "factor_name")}
            conn.execute(stmt.on_conflict_do_update(
                constraint=f"{table_name}_pkey", set_=update_cols
            ))
        else:
            # Raw SQL fallback
            cols = ", ".join(rows[0].keys())
            placeholders = ", ".join(f":{k}" for k in rows[0])
            update_set = ", ".join(
                f"{k}=EXCLUDED.{k}" for k in rows[0]
                if k not in ("symbol", "trade_date", "factor_name")
            )
            sql = (
                f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT ON CONSTRAINT {table_name}_pkey DO UPDATE SET {update_set}"
            )
            for row in rows:
                conn.execute(text(sql), row)
        conn.commit()


def precompute_factors():
    """预计算所有因子，写入 factor_cache"""
    from .models import MarketDaily, FactorCache

    with sync_engine.connect() as conn:
        # 获取需要计算的股票列表
        symbols = [
            row[0] for row in
            conn.execute(text("SELECT DISTINCT symbol FROM market_daily ORDER BY symbol")).fetchall()
        ]

    logger.info(f"因子预计算: {len(symbols)} 只股票")

    FIELDS = [
        "ma_5", "ma_10", "ma_20", "ma_60", "ma_120",
        "ema_12", "ema_26",
        "volume_ma_5", "volume_ma_20",
        "rsi_14",
        "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14",
        "kdj_k", "kdj_d", "kdj_j",
        "wr_14",
        "volatility_20",
        "momentum_5", "momentum_20", "momentum_60",
        "volume_ratio",
    ]

    batch = []
    processed = 0

    for symbol in symbols:
        try:
            df = _load_symbol_data(symbol)
            if df is None or len(df) < 30:
                continue

            facs = compute_all_factors(
                df["open"], df["high"], df["low"],
                df["close"], df["volume"],
            )

            for _, row in df.iterrows():
                td = row["trade_date"]
                for fname in FIELDS:
                    if fname in facs:
                        val = facs[fname].get(td)
                        if val is not None and not pd.isna(val):
                            batch.append({
                                "symbol": symbol,
                                "trade_date": td,
                                "factor_name": fname,
                                "factor_value": float(val),
                            })

            processed += 1
        except Exception:
            continue

        if len(batch) >= 10000:
            _batch_upsert("factor_cache", batch)
            batch = []
            logger.info(f"  进度: {processed}/{len(symbols)}")

    _batch_upsert("factor_cache", batch)
    logger.info(f"因子预计算完成: {processed}/{len(symbols)}")


def _load_symbol_data(symbol: str) -> pd.DataFrame:
    """从数据库加载单只股票的完整历史数据"""
    from .models import MarketDaily
    with sync_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM market_daily WHERE symbol=:sym ORDER BY trade_date"),
            {"sym": symbol},
        ).fetchall()

    if not rows:
        return None

    data = []
    for r in rows:
        r = r._mapping
        data.append({
            "trade_date": r["trade_date"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
        })
    df = pd.DataFrame(data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")


def query_market_data(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """回测引擎专用：从数据库加载行情数据"""
    with sync_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM market_daily "
                "WHERE symbol = ANY(:syms) AND trade_date BETWEEN :start AND :end "
                "ORDER BY trade_date, symbol"
            ),
            {"syms": symbols, "start": start, "end": end},
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    data = []
    for r in rows:
        r = r._mapping
        data.append({
            "symbol": r["symbol"],
            "trade_date": pd.Timestamp(r["trade_date"]),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
        })

    df = pd.DataFrame(data)
    if df.empty:
        return df

    df = df.set_index(["trade_date", "symbol"]).sort_index()
    return df


def query_market_data_with_factors(
    symbols: list[str], start: str, end: str
) -> pd.DataFrame:
    """回测引擎专用：加载行情数据并合并预计算的因子"""
    df = query_market_data(symbols, start, end)
    if df.empty:
        return df

    # 加载因子
    with sync_engine.connect() as conn:
        fac_rows = conn.execute(
            text(
                "SELECT symbol, trade_date, factor_name, factor_value "
                "FROM factor_cache "
                "WHERE symbol = ANY(:syms) AND trade_date BETWEEN :start AND :end"
            ),
            {"syms": symbols, "start": start, "end": end},
        ).fetchall()

    if fac_rows:
        fac_data = {}
        for r in fac_rows:
            r = r._mapping
            key = (r["symbol"], pd.Timestamp(r["trade_date"]).to_pydatetime().date())
            if key not in fac_data:
                fac_data[key] = {}
            fac_data[key][r["factor_name"]] = r["factor_value"]

        for idx in df.index:
            td, sym = idx
            td_date = td.to_pydatetime().date() if hasattr(td, "to_pydatetime") else td
            key = (sym, td_date)
            if key in fac_data:
                for fname, fval in fac_data[key].items():
                    df.loc[idx, fname] = fval

    return df


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "sync-full":
            sync_full()
        elif cmd == "sync-daily":
            sync_incremental()
        elif cmd == "precompute-factors":
            precompute_factors()
        else:
            print(f"未知命令: {cmd}")
            print("可用: sync-full, sync-daily, precompute-factors")
    else:
        print("用法: python -m backend.data_pipeline <命令>")
        print("可用: sync-full, sync-daily, precompute-factors")
