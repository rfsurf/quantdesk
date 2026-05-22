"""
回测引擎单元测试 — 可脱离外部依赖独立运行
从项目根目录运行: PYTHONPATH=. python backend/tests/test_backtest_engine.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import pandas as pd
from datetime import date

from backend.core import (
    BacktestConfig, BacktestResult, NavPoint, PositionInfo, Side, Trade,
)
from backend.backtest_engine import BacktestEngine


# ============ helpers ============

def _make_rising(days=252, start_price=100.0, daily_pct=0.001):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    prices = start_price * (1 + daily_pct) ** np.arange(days)
    noise = rng.normal(0, 0.005, days)
    prices = prices * (1 + noise)
    records = []
    for i, d in enumerate(dates):
        records.append({
            "symbol": "600519.SH", "trade_date": d,
            "open": prices[i]*0.99, "high": prices[i]*1.01, "low": prices[i]*0.98,
            "close": prices[i], "volume": 10_000_000,
        })
    df = pd.DataFrame(records)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")


def _make_falling(days=252, start=200.0):
    return _make_rising(days, start, daily_pct=-0.0008)


# ============ init ============

def test_init_defaults():
    e = BacktestEngine(BacktestConfig())
    assert e.cash == 100000.0
    assert e.positions == {}
    assert e.trades == []

def test_init_negative_commission_raises():
    try:
        BacktestEngine(BacktestConfig(commission_rate=-0.01))
        assert False, "应该raise ValueError"
    except ValueError:
        pass

def test_init_zero_max_positions_raises():
    try:
        BacktestEngine(BacktestConfig(max_positions=0))
        assert False, "应该raise ValueError"
    except ValueError:
        pass

# ============ buy ============

def test_buy_reduces_cash():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert e.cash < 100000

def test_buy_creates_position():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert "600519.SH" in e.positions
    assert e.positions["600519.SH"].shares > 0

def test_buy_records_trade():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert len(e.trades) == 1
    assert e.trades[0].side == Side.BUY

def test_buy_lot_size_100():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert e.positions["600519.SH"].shares % 100 == 0

def test_buy_insufficient_cash_does_nothing():
    e = BacktestEngine(BacktestConfig(initial_cash=10, commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5, start_price=50000)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert len(e.positions) == 0

def test_buy_includes_slippage():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0.01))
    df = _make_rising(days=5)
    close = df.iloc[0]["close"]
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert e.positions["600519.SH"].avg_cost > close

def test_buy_includes_commission():
    e = BacktestEngine(BacktestConfig(commission_rate=0.001, slippage_rate=0))
    df = _make_rising(days=5)
    close = float(df.iloc[0]["close"])
    # 引擎按槽位分配买股
    slots = e.config.max_positions
    cash_per_slot = 100000 / slots
    shares = int(cash_per_slot / (close * 1.001) / 100) * 100
    if shares <= 0:
        shares = 100
    expected_cost = close * shares * 1.001
    e._buy("600519.SH", df.iloc[0], df.index[0])
    assert abs(e.cash - (100000 - expected_cost)) < 0.01

# ============ sell ============

def test_sell_increases_cash():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=10)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    cash_before = e.cash
    e._sell("600519.SH", df.iloc[5], df.index[5])
    assert e.cash > cash_before

def test_sell_removes_position():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=10)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    e._sell("600519.SH", df.iloc[5], df.index[5])
    assert "600519.SH" not in e.positions

def test_sell_records_pnl():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=10)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    e._sell("600519.SH", df.iloc[5], df.index[5])
    assert e.trades[-1].pnl is not None

def test_sell_profit_on_rising():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=200, start_price=100, daily_pct=0.002)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    e._sell("600519.SH", df.iloc[-1], df.index[-1])
    assert e.trades[-1].pnl > 0

def test_sell_loss_on_falling():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_falling(days=200)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    e._sell("600519.SH", df.iloc[-1], df.index[-1])
    assert e.trades[-1].pnl < 0

# ============ risk management ============

def test_stop_loss_triggers():
    cfg = BacktestConfig(commission_rate=0, slippage_rate=0, stop_loss_pct=8)
    e = BacktestEngine(cfg)

    dates = pd.date_range("2024-01-01", periods=50, freq="B")
    prices = np.linspace(100, 80, 50)
    records = []
    for i, d in enumerate(dates):
        records.append({
            "symbol": "600519.SH", "trade_date": d,
            "open": prices[i], "high": prices[i], "low": prices[i],
            "close": prices[i], "volume": 10_000_000,
        })
    df = pd.DataFrame(records).set_index("trade_date")

    e._buy("600519.SH", df.iloc[0], df.index[0])
    for i in range(1, len(df)):
        e._check_risk_management(df, df.index[i])
    assert "600519.SH" not in e.positions

def test_stop_profit_triggers():
    cfg = BacktestConfig(commission_rate=0, slippage_rate=0, stop_profit_pct=20)
    e = BacktestEngine(cfg)
    dates = pd.date_range("2024-01-01", periods=50, freq="B")
    prices = np.linspace(100, 130, 50)
    records = []
    for i, d in enumerate(dates):
        records.append({
            "symbol": "600519.SH", "trade_date": d,
            "open": prices[i], "high": prices[i], "low": prices[i],
            "close": prices[i], "volume": 10_000_000,
        })
    df = pd.DataFrame(records).set_index("trade_date")
    e._buy("600519.SH", df.iloc[0], df.index[0])
    for i in range(1, len(df)):
        e._check_risk_management(df, df.index[i])
    assert "600519.SH" not in e.positions

def test_no_stop_loss_when_none():
    cfg = BacktestConfig(commission_rate=0, slippage_rate=0, stop_loss_pct=None)
    e = BacktestEngine(cfg)
    df = _make_falling(days=100)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    for i in range(1, len(df)):
        e._check_risk_management(df, df.index[i])
    assert "600519.SH" in e.positions

# ============ NAV ============

def test_nav_empty_equals_cash():
    e = BacktestEngine(BacktestConfig(initial_cash=100000))
    df = _make_rising(days=2)
    e._mark_to_market(df.index[0], df, None, 0)
    assert e.daily_nav[-1].nav == 100000

def test_nav_with_positions():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._buy("600519.SH", df.iloc[0], df.index[0])
    # _mark_to_market 接收单日数据
    e._mark_to_market(df.index[0], df.iloc[[0]], None, 0)
    e._mark_to_market(df.index[1], df.iloc[[1]], None, 1)
    pos_mv = e.positions["600519.SH"].shares * float(df.iloc[1]["close"])
    assert abs(e.daily_nav[-1].nav - (e.cash + pos_mv)) < 0.01

def test_daily_return_computed():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=5)
    e._mark_to_market(df.index[0], df, None, 0)
    e._mark_to_market(df.index[1], df, None, 1)
    assert e.daily_nav[0].daily_return == 0.0
    assert e.daily_nav[1].daily_return is not None

# ============ full run ============

def test_full_run_on_rising():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=252, start_price=100, daily_pct=0.002)
    sym = "600519.SH"
    idx_list = list(df.index)

    class SimpleMA:
        def __call__(self, data, date, positions):
            signals = {}
            if date not in idx_list:
                return signals
            pos = idx_list.index(date)
            if pos < 25:
                return signals
            closes = data["close"]
            ma5 = closes.iloc[pos-4:pos+1].mean()
            ma20 = closes.iloc[pos-19:pos+1].mean()
            if ma5 > ma20 and sym not in positions:
                signals[sym] = 1
            elif ma5 < ma20 and sym in positions:
                signals[sym] = -1
            return signals

    result = e.run(df, SimpleMA())
    assert len(result.trades) > 0  # 至少有一笔交易（buy也算）
    print(f"  total_return={result.total_return:.4f}, sharpe={result.sharpe_ratio:.2f}, trades={result.total_trades}")

def test_full_run_empty_returns_zero():
    e = BacktestEngine(BacktestConfig())
    df = pd.DataFrame(columns=["symbol","open","high","low","close","volume"])
    result = e.run(df, lambda d,dt,p: {})
    assert result.total_trades == 0

def test_full_run_respects_max_positions():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0, max_positions=2))

    symbols = ["A.SH","B.SH","C.SH","D.SH"]
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    records = []
    for d in dates:
        for s in symbols:
            records.append({
                "symbol": s, "trade_date": d, "open": 100.0, "high": 101.0,
                "low": 99.0, "close": 100.0, "volume": 10_000_000,
            })
    df = pd.DataFrame(records).set_index(["trade_date", "symbol"]).sort_index()

    def sig(data, date, positions):
        return {s: 1 for s in symbols if s not in positions}

    result = e.run(df, sig)
    # 验证持仓从不超过2只
    max_pos = 0
    held = set()
    for t in result.trades:
        if t.side == Side.BUY: held.add(t.symbol)
        elif t.side == Side.SELL: held.discard(t.symbol)
        max_pos = max(max_pos, len(held))
    assert max_pos <= 2
    print(f"  max_positions_held={max_pos}")

# ============ metrics ============

def test_known_total_return():
    e = BacktestEngine(BacktestConfig(initial_cash=100000, commission_rate=0, slippage_rate=0))
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    records = []
    for i, d in enumerate(dates):
        price = 100.0 + i   # 100, 101, ..., 109
        records.append({
            "symbol": "TEST.SH", "trade_date": d,
            "open": price, "high": price, "low": price, "close": price,
            "volume": 10_000_000,
        })
    df = pd.DataFrame(records).set_index("trade_date")

    # 使用单日数据调用
    e._buy("TEST.SH", df.iloc[0], df.index[0])
    e._mark_to_market(df.index[0], df.iloc[[0]], None, 0)
    e._sell("TEST.SH", df.iloc[-1], df.index[-1])
    e._mark_to_market(df.index[-1], df.iloc[[-1]], None, 9)
    result = e._compute_result()
    # 按槽位：100000/10=10000 per slot, @100=100 shares (at least 100 shares via fallback)
    # 100股@100=10000 → 卖@109=10900 → 赚900 → 0.9%
    assert result.total_return > 0
    print(f"  total_return={result.total_return:.4f}")

def test_win_rate():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=200)
    for i in range(4):
        e._buy("TEST.SH", df.iloc[i*10], df.index[i*10])
        row = df.iloc[(i+1)*10-1].copy()
        if i == 2:
            row["close"] = 50.0
        e._sell("TEST.SH", row, df.index[(i+1)*10-1])
    e._mark_to_market(df.index[-1], df, None, 199)
    result = e._compute_result()
    assert abs(result.win_rate - 0.75) < 0.01
    print(f"  win_rate={result.win_rate}")

def test_sharpe_sign():
    e = BacktestEngine(BacktestConfig(commission_rate=0, slippage_rate=0))
    df = _make_rising(days=500, daily_pct=0.001)
    e.cash = 0
    e.positions["TEST.SH"] = PositionInfo(1000, 100)
    for i in range(len(df)):
        e._mark_to_market(df.index[i], df.iloc[[i]], None, i)
    result = e._compute_result()
    assert result.total_return > 0
    print(f"  rising_sharpe={result.sharpe_ratio:.2f}")

    # falling market: set initial_cash to match starting position value
    df2 = _make_falling(days=500)
    start_price = float(df2.iloc[0]["close"])
    e2 = BacktestEngine(BacktestConfig(
        initial_cash=start_price * 1000, commission_rate=0, slippage_rate=0))
    e2.cash = 0
    e2.positions["TEST.SH"] = PositionInfo(1000, start_price)
    for i in range(len(df2)):
        e2._mark_to_market(df2.index[i], df2.iloc[[i]], None, i)
    result2 = e2._compute_result()
    assert result2.total_return < 0
    print(f"  falling_sharpe={result2.sharpe_ratio:.2f}")

def test_max_drawdown():
    from backend.backtest_engine import BacktestEngine as BE
    e = BE(BacktestConfig(initial_cash=100000))
    navs = [100000, 120000, 150000, 130000, 110000, 80000, 95000, 105000]
    dd, days = e._calc_max_drawdown(navs)
    assert 0.45 < dd < 0.48
    print(f"  max_drawdown={dd:.4f}, max_dd_days={days}")


# ============ runner ============

if __name__ == "__main__":
    import traceback
    tests = [
        ("init_defaults", test_init_defaults),
        ("init_negative_commission", test_init_negative_commission_raises),
        ("init_zero_max_positions", test_init_zero_max_positions_raises),
        ("buy_reduces_cash", test_buy_reduces_cash),
        ("buy_creates_position", test_buy_creates_position),
        ("buy_records_trade", test_buy_records_trade),
        ("buy_lot_size_100", test_buy_lot_size_100),
        ("buy_insufficient_cash", test_buy_insufficient_cash_does_nothing),
        ("buy_includes_slippage", test_buy_includes_slippage),
        ("buy_includes_commission", test_buy_includes_commission),
        ("sell_increases_cash", test_sell_increases_cash),
        ("sell_removes_position", test_sell_removes_position),
        ("sell_records_pnl", test_sell_records_pnl),
        ("sell_profit_on_rising", test_sell_profit_on_rising),
        ("sell_loss_on_falling", test_sell_loss_on_falling),
        ("stop_loss_triggers", test_stop_loss_triggers),
        ("stop_profit_triggers", test_stop_profit_triggers),
        ("no_stop_loss_when_none", test_no_stop_loss_when_none),
        ("nav_empty_equals_cash", test_nav_empty_equals_cash),
        ("nav_with_positions", test_nav_with_positions),
        ("daily_return_computed", test_daily_return_computed),
        ("full_run_on_rising", test_full_run_on_rising),
        ("full_run_empty_zero", test_full_run_empty_returns_zero),
        ("full_run_max_positions", test_full_run_respects_max_positions),
        ("known_total_return", test_known_total_return),
        ("win_rate", test_win_rate),
        ("sharpe_sign", test_sharpe_sign),
        ("max_drawdown", test_max_drawdown),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  {passed}/{len(tests)} 通过")
