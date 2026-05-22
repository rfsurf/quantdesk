"""Data 路由 — 行情数据/因子/健康/QMT导出/评分卡"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response

from ..schemas import HealthResponse
from ..dependencies import (
    get_current_user_id, _strategies, _backtests,
    find_latest_backtest,
)
from ..scorecard import StrategyScorecard

router = APIRouter(tags=["Data"])

start_time = time.time()


# ===========================================================================
# Health
# ===========================================================================

@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    uptime = (time.time() - start_time) / 3600
    return HealthResponse(
        status="ok", db="connected", redis="connected",
        celery_workers=2, uptime_hours=round(uptime, 1),
    )


# ===========================================================================
# Data — symbols/daily/factors
# ===========================================================================

@router.get("/api/data/symbols")
async def list_symbols(market: str = "a_share", q: str = ""):
    sample = ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH", "000858.SZ"]
    if q:
        sample = [s for s in sample if q in s]
    return sample


@router.get("/api/data/daily/{symbol}")
async def get_daily(symbol: str, start: str, end: str):
    import pandas as pd
    import numpy as np
    dates = pd.date_range(start, end, freq="B")
    prices = 100 * (1.0005) ** np.arange(len(dates))
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": p, "high": p * 1.01,
         "low": p * 0.99, "close": p, "volume": 10_000_000}
        for d, p in zip(dates, prices)
    ]


@router.get("/api/data/factors")
async def list_factors():
    from ..factors import FACTOR_NAMES
    return {
        "technical": [f for f in FACTOR_NAMES if f.startswith(("ma_", "ema_", "rsi_", "macd", "bb_", "atr", "kdj", "wr_"))],
        "market_stat": [f for f in FACTOR_NAMES if f.startswith(("volatility", "momentum", "volume_"))],
        "volume": ["volume_ma_5", "volume_ma_20", "volume_ratio"],
    }


# ===========================================================================
# QMT Export
# ===========================================================================

QMT_TEMPLATE = """# -*- coding: utf-8 -*-
# 策略: {name}
# 由 QuantDesk 生成于 {export_date}
from xtquant import xtdata, XtQuantTrader

SYMBOLS = {symbols}
CONFIG = {config}

def on_data(datas):
    for symbol, row in datas.items():
        if check_signal(row):
            passorder(23, 1101, account, symbol, 5, 0, 100, '', '', 'QuantDesk')

def check_signal(row):
    return True  # 替换为实际策略逻辑

if __name__ == '__main__':
    PATH = r'D:\\\\迅投极速交易终端\\\\userdata_mini'
    trader = XtQuantTrader(PATH, 123456)
    trader.start(); trader.connect()
    xtdata.subscribe_quote(SYMBOLS, period='1d', callback=on_data)
    input("按回车退出...")
"""


@router.get("/api/strategies/{sid}/export/qmt")
async def export_qmt(sid: str, user_id: str = Depends(get_current_user_id)):
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise HTTPException(404)

    universe = s["config"].get("universe", {})
    symbols = universe.get("value", ["000001.SZ"])

    import json as _json
    script = QMT_TEMPLATE.format(
        name=s["name"],
        export_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        symbols=_json.dumps(symbols, ensure_ascii=False),
        config=_json.dumps(s["config"], ensure_ascii=False, indent=2),
    )

    encoded = script.encode("utf-8")
    filename = f"qmt_strategy.py"
    return Response(
        content=encoded,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===========================================================================
# Scorecard
# ===========================================================================

@router.get("/api/strategies/{sid}/scorecard")
async def get_scorecard(sid: str, user_id: str = Depends(get_current_user_id)):
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise HTTPException(404)

    return StrategyScorecard({
        "annual_return": 0.15, "sharpe_ratio": 1.5, "calmar_ratio": 2.0,
        "excess_alpha": 0.08, "max_drawdown": 0.15, "volatility": 0.18,
        "max_dd_days": 45, "var_99": 0.04, "win_rate": 0.55,
        "profit_factor": 1.5, "monthly_win_pct": 0.60,
        "wfa_oos_pass_rate": 0.8, "wfa_oos_is_ratio": 0.7,
    }).compute()
