"""
QuantDesk AI 输出校验器
校验 LLM 生成的策略配置的合法性、安全性
"""

import jsonschema
import re
from typing import Any

from .factors import FACTOR_NAMES


VALID_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["universe", "conditions", "weights", "rebalance"],
    "properties": {
        "universe": {"type": "object", "required": ["type", "value"]},
        "conditions": {"type": "object"},
        "weights": {"type": "string", "enum": ["equal", "market_cap", "custom"]},
        "rebalance": {"type": "object", "required": ["frequency"]},
        "position_pct": {"type": "number", "minimum": 0.01, "maximum": 1.0},
    },
}


def validate_config_schema(config: dict):
    """校验 AI 输出的 JSON 结构是否完整"""
    jsonschema.validate(config, VALID_CONFIG_SCHEMA)


def validate_config_factors(config: dict):
    """校验 config 中所有因子名是否在合法因子库中"""
    factors_used = _extract_factors(config.get("conditions", {}))

    unknown = []
    for f in factors_used:
        if f not in FACTOR_NAMES and f not in _LEGACY_FACTORS:
            unknown.append(f)

    if unknown:
        raise ValueError(f"未知因子: {unknown}")

    # 至少有1个条件
    conditions = config.get("conditions", {})
    children = conditions.get("children", [])
    if not children:
        raise ValueError("策略至少需要包含一个条件")


def validate_config_params(config: dict):
    """校验参数是否在合法范围"""
    position_pct = config.get("position_pct")
    if position_pct is not None:
        if not (0.01 <= position_pct <= 1.0):
            raise ValueError(f"仓位参数必须在 0.01-1.0 之间: {position_pct}")

    # 检查所有因子参数
    conditions = config.get("conditions", {})
    _validate_params_recursive(conditions)


def validate_market_state_switching(config: dict) -> dict:
    """校验市场状态双模策略配置"""
    has_state = "market_state" in config
    has_trending = "trending" in config
    has_ranging = "ranging" in config

    if has_state and (not has_trending or not has_ranging):
        return {"valid": False, "message": "市场状态模式下需要同时配置趋势策略和震荡策略"}
    return {"valid": True, "message": ""}


def detect_cycle(conditions: dict) -> bool:
    """检测条件树中的自循环引用"""
    visited = set()

    def _walk(node):
        node_id = id(node)
        if node_id in visited:
            return True
        visited.add(node_id)

        if isinstance(node, dict):
            for v in node.values():
                if isinstance(v, (dict, list)):
                    if _walk(v):
                        return True
        elif isinstance(node, list):
            for item in node:
                if _walk(item):
                    return True
        return False

    return _walk(conditions)


def sanitize_ai_output(data: dict) -> dict:
    """清洗 AI 输出中的危险内容"""
    if "name" in data:
        name = data["name"]
        name = re.sub(r'[;\'"\\]', '', name)
        name = re.sub(r'(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)',
                      '', name, flags=re.IGNORECASE)
        data["name"] = name[:100]

    # 递归清洗 JSON 中的脚本注入
    def _sanitize_value(v):
        if isinstance(v, str):
            v = re.sub(r'<script[^>]*>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
            v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
            v = re.sub(r'(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET)',
                      '', v, flags=re.IGNORECASE)
        elif isinstance(v, dict):
            return {k: _sanitize_value(v) for k, v in v.items()}
        elif isinstance(v, list):
            return [_sanitize_value(item) for item in v]
        return v

    return {k: _sanitize_value(v) for k, v in data.items()}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_LEGACY_FACTORS = {
    "close", "open", "high", "low", "volume",
    "pe", "pb", "roe", "revenue_growth", "dividend_yield",
    "turnover", "amplitude",
    "volume_ratio",
}


def _extract_factors(conditions: dict) -> set:
    """递归提取条件树中所有因子名"""
    factors = set()

    def _walk(node):
        if not node:
            return
        if isinstance(node, dict):
            # 比较节点
            if "left" in node:
                if isinstance(node["left"], dict):
                    factors.add(node["left"].get("factor", ""))
            if "right" in node:
                if isinstance(node["right"], dict):
                    factors.add(node["right"].get("factor", ""))
            # 排名节点
            if "factor" in node:
                factors.add(node["factor"])
            # 递归
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(conditions)
    return {f for f in factors if f}


def _validate_params_recursive(node):
    """递归校验因子参数"""
    if not node:
        return
    if isinstance(node, dict):
        params = node.get("params", {})
        for k, v in params.items():
            if isinstance(v, (int, float)) and v < 0:
                raise ValueError(f"因子参数 {k} 不能为负数: {v}")
        for v in node.values():
            _validate_params_recursive(v)
    elif isinstance(node, list):
        for item in node:
            _validate_params_recursive(item)
