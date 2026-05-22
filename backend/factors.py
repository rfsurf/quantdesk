"""
QuantDesk 因子计算引擎
所有因子的向量化计算，支持缓存到 factor_cache 表
"""

import numpy as np
import pandas as pd
from typing import Optional


def compute_ma(close: pd.Series, period: int) -> pd.Series:
    """简单移动均线 SMA"""
    return close.rolling(period).mean()


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    """指数移动均线 EMA"""
    return close.ewm(span=period, adjust=False).mean()


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD → (macd_line, signal_line, histogram)"""
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 相对强弱指数"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_rsi_scalar(close: pd.Series, period: int = 14) -> float:
    """RSI 最后一个值"""
    result = compute_rsi(close, period)
    return float(result.dropna().iloc[-1]) if len(result.dropna()) > 0 else 50.0


def compute_bollinger(
    close: pd.Series, period: int = 20, k: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """布林带 → (mid, upper, lower, width)"""
    mid = compute_ma(close, period)
    std = close.rolling(period).std()
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid
    return mid, upper, lower, width


def compute_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """ATR 平均真实波幅"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_atr_scalar(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> float:
    """ATR 最后一个标量值"""
    result = compute_atr(high, low, close, period)
    return float(result.dropna().iloc[-1]) if len(result.dropna()) > 0 else 0.0


def compute_kdj(
    high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ → (K, D, J)"""
    lowest_low = low.rolling(n).min()
    highest_high = high.rolling(n).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan) * 100

    k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    d = k.ewm(alpha=1 / 3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def compute_wr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """威廉指标 WR"""
    return (high.rolling(n).max() - close) / (
        high.rolling(n).max() - low.rolling(n).min()
    ).replace(0, np.nan) * -100


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV 能量潮"""
    direction = np.sign(close.diff())
    return (direction * volume).cumsum()


def compute_historical_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """历史波动率（年化）"""
    daily_ret = close.pct_change()
    return daily_ret.rolling(period).std() * np.sqrt(252)


def compute_amplitude(high: pd.Series, low: pd.Series, prev_close: pd.Series) -> pd.Series:
    """振幅"""
    return (high - low) / prev_close * 100


def compute_momentum(close: pd.Series, period: int = 20) -> pd.Series:
    """N日涨跌幅"""
    return (close / close.shift(period) - 1) * 100


def compute_volume_ratio(volume: pd.Series, period: int = 5) -> pd.Series:
    """量比"""
    return volume / volume.rolling(period).mean()


# ------------------------------------------------------------------
# 因子预计算批量接口（供 data_pipeline 调用）
# ------------------------------------------------------------------

FACTOR_NAMES = [
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


def compute_all_factors(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> dict[str, pd.Series]:
    """一次性计算所有因子，返回 {factor_name: series}"""
    factors = {}

    # MA
    for p in [5, 10, 20, 60, 120]:
        factors[f"ma_{p}"] = compute_ma(close, p)

    # EMA
    factors["ema_12"] = compute_ema(close, 12)
    factors["ema_26"] = compute_ema(close, 26)

    # Volume MA
    factors["volume_ma_5"] = volume.rolling(5).mean()
    factors["volume_ma_20"] = volume.rolling(20).mean()

    # RSI
    factors["rsi_14"] = compute_rsi(close, 14)

    # MACD
    macd, sig, hist = compute_macd(close)
    factors["macd"] = macd
    factors["macd_signal"] = sig
    factors["macd_hist"] = hist

    # Bollinger
    _, upper, lower, width = compute_bollinger(close)
    factors["bb_upper"] = upper
    factors["bb_lower"] = lower
    factors["bb_width"] = width

    # ATR
    factors["atr_14"] = compute_atr(high, low, close, 14)

    # KDJ
    k, d, j = compute_kdj(high, low, close)
    factors["kdj_k"] = k
    factors["kdj_d"] = d
    factors["kdj_j"] = j

    # WR
    factors["wr_14"] = compute_wr(high, low, close, 14)

    # Volatility
    factors["volatility_20"] = compute_historical_volatility(close, 20)

    # Momentum
    for p in [5, 20, 60]:
        factors[f"momentum_{p}"] = compute_momentum(close, p)

    # Volume ratio
    factors["volume_ratio"] = compute_volume_ratio(volume, 5)

    return factors
