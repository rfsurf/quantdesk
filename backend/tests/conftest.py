"""
QuantDesk 测试 fixtures 和公共配置
"""

import sys
import os
import socket

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# 设置测试环境变量（必须在导入 backend 之前）
os.environ["QUANTDESK_JWT_SECRET"] = "test-secret-key-for-unit-tests-min-32-chars!!"
os.environ["QUANTDESK_DEBUG"] = "true"
os.environ["QUANTDESK_USE_POSTGRES"] = "false"
os.environ["QUANTDESK_REDIS_URL"] = "redis://localhost:6379/0"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


def redis_available():
    """检测 Redis 是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()
        return result == 0
    except:
        return False


REDIS_IS_AVAILABLE = redis_available()

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
