"""
QuantDesk 测试 fixtures 和公共配置
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_rising_data():
    """标准上涨行情 fixture — 252天的单边上涨数据"""
    dates = pd.date_range("2024-01-01", periods=252, freq="B")
    prices = 100 * (1.001) ** np.arange(252)
    records = []
    for i, d in enumerate(dates):
        records.append({
            "symbol": "TEST.SH", "trade_date": d,
            "open": prices[i], "high": prices[i] * 1.01,
            "low": prices[i] * 0.99, "close": prices[i],
            "volume": 10_000_000,
        })
    df = pd.DataFrame(records)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")


@pytest.fixture
def default_config():
    """默认回测配置"""
    from backend.core import BacktestConfig
    return BacktestConfig(
        initial_cash=100000, commission_rate=0.0003,
        slippage_rate=0.0001, max_positions=10,
    )


@pytest.fixture
def valid_ma_config():
    """标准MA金叉策略配置"""
    return {
        "universe": {"type": "index", "value": "000300"},
        "conditions": {
            "logic": "AND",
            "children": [
                {
                    "type": "compare",
                    "left": {"factor": "ma", "params": {"period": 5}},
                    "op": ">",
                    "right": {"factor": "ma", "params": {"period": 20}},
                },
                {
                    "type": "compare",
                    "left": {"factor": "volume"},
                    "op": ">",
                    "right": {"factor": "ma_volume", "params": {"period": 20}},
                    "multiplier": 1.5,
                },
            ],
        },
        "weights": "equal",
        "rebalance": {"frequency": "daily"},
    }
