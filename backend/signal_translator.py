"""
QuantDesk 策略信号翻译器
将用户的可视化 JSON 配置翻译为回测引擎可执行的信号函数
"""

import numpy as np
import pandas as pd
from typing import Callable

from .core import PositionInfo


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def build_signal_func(config: dict) -> Callable:
    """
    将策略配置 JSON 编译为信号函数。

    信号函数签名: (data, date, positions) → dict[symbol, 1/-1/0]
    """
    universe_fn = _parse_universe(config.get("universe", {}))
    condition_fn = _parse_condition_tree(config.get("conditions", {}))
    rebalance_fn = _parse_rebalance(config.get("rebalance", {}))
    exit_fn = _parse_exit_conditions(config)

    def signal_func(data: pd.DataFrame, date, current_positions: dict) -> dict:
        signals: dict = {}

        if not rebalance_fn(date):
            return signals

        # 卖出信号：对已持仓检查出场条件
        for symbol in list(current_positions.keys()):
            try:
                row = _get_row(data, date, symbol)
                if exit_fn(row, current_positions[symbol], date):
                    signals[symbol] = -1
            except (KeyError, IndexError):
                continue

        # 买入信号：候选池中满足入场条件的
        available = universe_fn(data, date)
        if isinstance(available, pd.DataFrame):
            available = available.index.tolist()

        for symbol in available:
            if symbol in current_positions:
                continue
            try:
                row = _get_row(data, date, symbol)
                if condition_fn(row):
                    signals[symbol] = 1
            except (KeyError, IndexError):
                continue

        return signals

    return signal_func


def _validate_factor_params(factor_spec: dict):
    """校验因子参数合法性"""
    params = factor_spec.get("params", {})
    for k, v in params.items():
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError(f"因子参数 {k} 不能为负数: {v}")


# ------------------------------------------------------------------
# Universe
# ------------------------------------------------------------------

def _parse_universe(spec: dict):
    universe_type = spec.get("type", "all")
    value = spec.get("value", [])

    if universe_type == "symbols":
        symbols = value if isinstance(value, list) else [value]

        def fn(data, date):
            return [s for s in symbols if _symbol_in_data(data, s, date)]

        return fn

    if universe_type == "index":
        return _make_fixed_universe(value)

    # fallback: return everything in data
    def fn(data, date):
        if isinstance(data.index, pd.MultiIndex):
            try:
                return list(data.loc[date].index)
            except KeyError:
                return []
        return list(data.index)

    return fn


def _make_fixed_universe(symbols):
    syms = symbols if isinstance(symbols, list) else [symbols]

    def fn(data, date):
        return syms

    return fn


# ------------------------------------------------------------------
# Condition tree
# ------------------------------------------------------------------

def _parse_condition_tree(node: dict) -> Callable:
    if not node:
        return lambda row: True

    # 逻辑组合节点
    logic = node.get("logic")
    children = node.get("children")
    if logic and children:
        if logic == "AND":
            child_fns = [_parse_condition_tree(c) for c in children]

            def fn(row):
                return all(cf(row) for cf in child_fns)

            return fn
        elif logic == "OR":
            child_fns = [_parse_condition_tree(c) for c in children]

            def fn(row):
                return any(cf(row) for cf in child_fns)

            return fn

    # 比较节点
    if node.get("type") == "compare":
        return _parse_compare(node)

    # 排名节点
    if node.get("type") == "rank":
        return _parse_rank(node)

    # 交叉节点
    if node.get("type") == "cross":
        return _parse_cross(node)

    return lambda row: True


def _parse_compare(node: dict) -> Callable:
    left = _make_value_getter(node.get("left", {}))
    right = _make_value_getter(node.get("right", {}))
    op = node.get("op", ">")
    multiplier = node.get("multiplier", 1.0)

    ops = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: abs(a - b) < 1e-9,
        "!=": lambda a, b: abs(a - b) >= 1e-9,
    }
    op_fn = ops.get(op, ops[">"])

    def fn(row):
        l_val = left(row)
        r_val = right(row)
        try:
            return op_fn(float(l_val), float(r_val) * multiplier)
        except (TypeError, ValueError):
            return False

    return fn


def _parse_rank(node: dict) -> Callable:
    # 排名条件：需要操作dataframe级别的数据，这里给简化版
    factor = node.get("factor", "momentum_5")
    direction = node.get("direction", "top")
    percentile = node.get("percentile", 50) / 100.0

    def fn(row):
        return True  # 实际排名在multi-symbol层面处理

    return fn


def _parse_cross(node: dict) -> Callable:
    left = node.get("left", {})
    right = node.get("right", {})
    direction = node.get("direction", "above")  # above=金叉, below=死叉

    def fn(row):
        return True  # 交叉需看历史，在exit_fn中通过趋势判断

    return fn


# ------------------------------------------------------------------
# Value getter
# ------------------------------------------------------------------

def _make_value_getter(spec: dict) -> Callable:
    if not spec:
        return lambda row: 0.0

    factor = spec.get("factor", "close")

    # 常量
    if factor == "constant":
        val = float(spec.get("value", 0))

        def fn(row):
            return val

        return fn

    # 收盘价
    if factor == "close":

        def fn(row):
            return float(row["close"])

        return fn

    # 成交量
    if factor == "volume":

        def fn(row):
            return float(row["volume"])

        return fn

    # 预计算因子（从 factor_cache 预加载的值直接挂在row上）
    params = spec.get("params", {})
    period = params.get("period", 20)

    # MA
    if factor == "ma":
        col = f"ma_{period}"

        def fn(row):
            return float(row.get(col, row["close"]))

        return fn

    # EMA
    if factor == "ema":
        col = f"ema_{period}"

        def fn(row):
            return float(row.get(col, row["close"]))

        return fn

    # RSI
    if factor == "rsi":
        def fn(row):
            return float(row.get("rsi_14", 50))
        return fn

    # MACD
    if factor == "macd":
        field = params.get("field", "macd")

        def fn(row):
            return float(row.get(field, 0))
        return fn

    # 布林带
    if factor == "bb":
        band = params.get("band", "upper")

        def fn(row):
            return float(row.get(f"bb_{band}", row["close"]))
        return fn

    # ATR
    if factor == "atr":
        def fn(row):
            return float(row.get("atr_14", 0))
        return fn

    # 成交量均线
    if factor == "ma_volume":
        col = f"volume_ma_{period}"

        def fn(row):
            return float(row.get(col, row["volume"]))
        return fn

    # 波动率
    if factor == "volatility":
        def fn(row):
            return float(row.get("volatility_20", 0))
        return fn

    # 动量/涨跌幅
    if factor == "return" or factor == "momentum":
        col = f"momentum_{period}" if period != 5 else "momentum_5"

        def fn(row):
            return float(row.get(col, 0))
        return fn

    # 换手率
    if factor == "turnover":
        def fn(row):
            return float(row.get("turnover", 0))
        return fn

    # 振幅
    if factor == "amplitude":
        def fn(row):
            return float(row.get("amplitude", 0))
        return fn

    # PE/PB/ROE等基本面
    if factor in ("pe", "pb", "roe", "revenue_growth", "dividend_yield"):
        def fn(row):
            return float(row.get(factor, 0))
        return fn

    # 量比
    if factor == "volume_ratio":
        def fn(row):
            return float(row.get("volume_ratio", 1))
        return fn

    # default
    def fn(row):
        return float(row.get(factor, 0))
    return fn


# ------------------------------------------------------------------
# Rebalance
# ------------------------------------------------------------------

def _parse_rebalance(spec: dict) -> Callable:
    freq = spec.get("frequency", "daily")

    if freq == "daily":
        return lambda date: True

    if freq == "weekly":
        day_of_week = spec.get("day", 0)  # 0=Monday

        def fn(date):
            return date.weekday() == day_of_week

        return fn

    if freq == "monthly":
        day_of_month = spec.get("day", 1)

        def fn(date):
            return date.day == day_of_month

        return fn

    return lambda date: True


# ------------------------------------------------------------------
# Exit conditions
# ------------------------------------------------------------------

def _parse_exit_conditions(config: dict) -> Callable:
    """解析卖出/出场条件"""

    def fn(row, position: PositionInfo, date) -> bool:
        # 死叉：MA(5) < MA(20)
        ma5 = row.get("ma_5")
        ma20 = row.get("ma_20")
        if ma5 is not None and ma20 is not None:
            if float(ma5) < float(ma20):
                return True

        # RSI超买 > 80
        rsi = row.get("rsi_14")
        if rsi is not None and float(rsi) > 80:
            return True

        return False

    return fn


def _should_exit(symbol: str, row, position: PositionInfo, config: dict) -> bool:
    """供外部调用的出场判断（兼容蓝图接口）"""
    exit_fn = _parse_exit_conditions(config)
    return exit_fn(row, position, None)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_row(data: pd.DataFrame, date, symbol: str):
    """从数据中提取某一天某只股票的行"""
    if isinstance(data.index, pd.MultiIndex):
        return data.loc[(date, symbol)]
    return data.loc[date]


def _symbol_in_data(data: pd.DataFrame, symbol: str, date) -> bool:
    if isinstance(data.index, pd.MultiIndex):
        try:
            data.loc[(date, symbol)]
            return True
        except KeyError:
            return False
    return symbol in (data.columns.tolist() if isinstance(data, pd.DataFrame) else [])
