"""
QuantDesk AI 客户端 — OpenAI 兼容接口
支持 DeepSeek / Ollama / 任意 OpenAI-compatible 端点
"""

import json
import re
import httpx
from .config import settings
from .ai_validator import validate_config_schema, validate_config_factors, validate_config_params


SYSTEM_PROMPT = """你是 QuantDesk 的量化策略专家。你的任务是把用户的自然语言描述，转换成 QuantDesk 策略配置 JSON。

## 因子库（可用因子列表）

技术指标：
- ma_{N}: N日均线 (N=5,10,20,60,120)
- ema_{N}: N日指数均线 (N=12,26)
- rsi_{N}: N日RSI相对强弱指数 (N=14)
- macd / macd_signal / macd_hist: MACD指标三线
- bb_upper / bb_lower / bb_width: 布林带上轨/下轨/宽度
- atr_{N}: N日ATR平均真实波幅 (N=14)
- kdj_k / kdj_d / kdj_j: KDJ指标
- wr_{N}: N日威廉指标 (N=14)
- volume_ma_{N}: N日成交量均线 (N=5,20)
- volume_ratio: 量比

行情统计：
- momentum_{N}: N日涨跌幅 (N=5,20,60)
- volatility_{N}: N日历史波动率 (N=20)

基本面（需AKShare数据）：
- pe: 市盈率
- pb: 市净率
- roe: ROE净资产收益率
- revenue_growth: 营收增速
- dividend_yield: 股息率

原始数据：
- close / open / high / low / volume

## 比较算子
- ">" / "<" / ">=" / "<=" / "==" : 数值比较
- "cross_above": 金叉（快线上穿慢线）
- "cross_below": 死叉（快线下穿慢线）
- "between": 数值在区间内

## 逻辑算子
- "AND": 所有子条件同时满足
- "OR": 任一子条件满足

## 输出 JSON Schema
{
  "universe": {"type": "index", "value": "000300"},
  "conditions": {
    "logic": "AND",
    "children": [
      {
        "type": "compare",
        "left": {"factor": "ma_5", "params": {"period": 5}},
        "op": ">",
        "right": {"factor": "ma_20", "params": {"period": 20}}
      }
    ]
  },
  "weights": "equal",
  "rebalance": {"frequency": "daily"},
  "position_pct": 1.0
}

## 规则
1. universe.type 可以是 "index"（指数成分股）或 "symbols"（指定股票列表）
2. 常用指数: "000300"=沪深300, "000905"=中证500, "000852"=中证1000
3. conditions 是嵌套条件树，logic 取 "AND" 或 "OR"
4. 每个 child 可以是 compare 节点或嵌套的条件组
5. 如果有趋势/震荡双模式需求，使用 market_state 切换
6. weights 取 "equal"（等权）
7. rebalance.frequency 取 "daily" / "weekly" / "monthly"
8. position_pct 是最多使用的仓位比例，0-1

只输出 JSON，不要解释，不要 markdown 代码块标记。"""


def _build_prompt(user_input: str) -> str:
    return f"用户需求：{user_input}\n\n请输出策略配置JSON："


async def generate_strategy_config(user_prompt: str, user_api_key: str | None = None, user_api_base: str | None = None) -> dict:
    """调用 AI 生成策略配置 JSON，校验后返回

    Args:
        user_prompt: 用户自然语言输入
        user_api_key: 用户自己的 API key（BYOK），None 则用平台 key
        user_api_base: 用户自定义 base URL（Ollama 等）
    """
    api_key = user_api_key or settings.DEEPSEEK_API_KEY
    api_base = user_api_base or settings.DEEPSEEK_BASE_URL

    if not api_key:
        return _fallback_config(user_prompt)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_prompt(user_prompt)},
    ]

    raw_json = await _call_llm(messages, temperature=0.3, api_key=api_key, api_base=api_base)

    # 清洗输出：去除可能的 markdown 代码块包装
    raw_json = _strip_code_fence(raw_json)
    config = json.loads(raw_json)

    # 安全校验
    validate_config_schema(config)
    validate_config_factors(config)
    validate_config_params(config)

    return config


async def diagnose_strategy(config: dict, metrics: dict, user_api_key: str | None = None, user_api_base: str | None = None) -> dict:
    """调用 AI 诊断策略并给出优化建议"""
    api_key = user_api_key or settings.DEEPSEEK_API_KEY
    api_base = user_api_base or settings.DEEPSEEK_BASE_URL

    if not api_key:
        return _fallback_diagnose(metrics)

    messages = [
        {"role": "system", "content": DIAGNOSE_PROMPT},
        {"role": "user", "content": json.dumps({
            "config": _summarize_config(config),
            "metrics": metrics,
        }, ensure_ascii=False)},
    ]

    raw = await _call_llm(messages, temperature=0.5)
    raw = _strip_code_fence(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": raw, "suggestions": [], "score": 50}


DIAGNOSE_PROMPT = """你是量化策略诊断专家。分析策略回测结果给出优化建议。

输出JSON格式：
{
  "summary": "3句话大白话总结策略表现",
  "suggestions": ["建议1", "建议2", "建议3"],
  "score": 70
}

只输出JSON，不要解释。"""


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

async def _call_llm(messages: list[dict], temperature: float = 0.3, api_key: str = "", api_base: str | None = None) -> str:
    """调用 OpenAI 兼容 API，返回原始文本"""
    base = (api_base or settings.DEEPSEEK_BASE_URL).rstrip("/")
    url = f"{base}/chat/completions"

    payload = {
        "model": settings.AI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


def _strip_code_fence(text: str) -> str:
    """去掉 ```json ... ``` 或 ``` ... ``` 包裹"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _summarize_config(config: dict) -> dict:
    """精简 config 用于诊断 prompt（减少 token）"""
    conditions = config.get("conditions", {})
    factor_count = _count_factors(conditions)
    return {
        "universe": config.get("universe", {}),
        "logic": conditions.get("logic", "AND"),
        "factor_count": factor_count,
        "weights": config.get("weights", "equal"),
        "rebalance_freq": config.get("rebalance", {}).get("frequency", "daily"),
    }


def _count_factors(conditions: dict) -> int:
    count = 0

    def _walk(node):
        nonlocal count
        if not node:
            return
        if isinstance(node, dict):
            for side in ("left", "right"):
                if side in node and isinstance(node[side], dict):
                    if node[side].get("factor"):
                        count += 1
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(conditions)
    return count


# ------------------------------------------------------------------
# Fallback（无 API key 时的模板生成）
# ------------------------------------------------------------------

_FALLBACK_TEMPLATES = {
    "震荡": {
        "universe": {"type": "index", "value": "000300"},
        "conditions": {
            "logic": "AND",
            "children": [
                {"type": "compare",
                 "left": {"factor": "rsi_14", "params": {"period": 14}},
                 "op": "<", "right": {"constant": 30}},
                {"type": "compare",
                 "left": {"factor": "volume"},
                 "op": ">", "right": {"factor": "volume_ma_20"},
                 "multiplier": 1.2},
            ],
        },
        "weights": "equal",
        "rebalance": {"frequency": "daily"},
    },
    "趋势": {
        "universe": {"type": "index", "value": "000300"},
        "conditions": {
            "logic": "AND",
            "children": [
                {"type": "compare",
                 "left": {"factor": "ma_5", "params": {"period": 5}},
                 "op": "cross_above",
                 "right": {"factor": "ma_20", "params": {"period": 20}}},
                {"type": "compare",
                 "left": {"factor": "volume"},
                 "op": ">", "right": {"factor": "volume_ma_5"},
                 "multiplier": 1.5},
            ],
        },
        "weights": "equal",
        "rebalance": {"frequency": "daily"},
    },
    "突破": {
        "universe": {"type": "index", "value": "000300"},
        "conditions": {
            "logic": "AND",
            "children": [
                {"type": "compare",
                 "left": {"factor": "momentum_20", "params": {"period": 20}},
                 "op": ">", "right": {"constant": 5}},
                {"type": "compare",
                 "left": {"factor": "volume_ratio"},
                 "op": ">", "right": {"constant": 2.0}},
                {"type": "compare",
                 "left": {"factor": "bb_width"},
                 "op": ">", "right": {"constant": 0.1}},
            ],
        },
        "weights": "equal",
        "rebalance": {"frequency": "daily"},
    },
}


def _fallback_config(user_prompt: str) -> dict:
    """无 API key 时，按关键词返回模板策略"""
    for keyword, template in _FALLBACK_TEMPLATES.items():
        if keyword in user_prompt:
            return template
    return _FALLBACK_TEMPLATES["趋势"]


def _fallback_diagnose(metrics: dict) -> dict:
    sharpe = metrics.get("sharpe_ratio", 1.0)
    if sharpe > 1.5:
        summary = "策略整体表现良好，收益风险比不错。在趋势行情中捕捉到了主要波段。可以考虑小仓位实盘验证。"
        score = 78
    elif sharpe > 0.8:
        summary = "策略有盈利能力但不够稳定。部分时间段回撤较大，建议加入风控条件如止损或仓位管理。"
        score = 62
    else:
        summary = "策略表现较弱，可能因子组合有问题或参数需要重新调整。建议简化条件或更换股票池。"
        score = 45

    return {
        "summary": summary,
        "suggestions": [
            "建议加入ADX趋势过滤器，只在趋势明确时交易",
            "止损设置在6-8%可有效控制尾部风险",
            "考虑在震荡市自动降低仓位到50%",
        ],
        "score": score,
    }
