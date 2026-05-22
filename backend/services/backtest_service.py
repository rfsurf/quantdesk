"""
Backtest Service — 回测执行 + 结果查询 + 历史列表
"""

import uuid
from datetime import datetime, timezone

from ..core import BacktestConfig
from ..dependencies import _backtests, _strategies, execute_backtest, find_latest_backtest


def trigger_backtest(strategy_id: str, user_id: str, params: dict) -> str:
    """触发回测，返回 task_id"""
    s = _strategies.get(strategy_id)
    if not s or s["user_id"] != user_id:
        raise ValueError("策略不存在")

    task_id = str(uuid.uuid4())
    _backtests[task_id] = {
        "id": task_id, "strategy_id": strategy_id, "user_id": user_id,
        "status": "pending", "params": params,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    execute_backtest(task_id)
    return task_id


def get_result(task_id: str, user_id: str) -> dict | None:
    """获取回测结果"""
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise ValueError("回测不存在")
    return bt


def get_trades(task_id: str, user_id: str) -> list:
    """获取回测交易明细"""
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise ValueError("回测不存在")
    return bt.get("trades", [])


def get_nav(task_id: str, user_id: str) -> list:
    """获取回测净值序列"""
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise ValueError("回测不存在")
    nav_series = bt.get("nav_series", [])
    return [
        {"date": str(n.date), "nav": n.nav, "daily_return": n.daily_return,
         "benchmark_nav": n.benchmark_nav}
        for n in nav_series
    ]


def list_user_backtests(user_id: str) -> dict:
    """列出用户的所有回测记录"""
    mine = [bt for bt in _backtests.values() if bt.get("user_id") == user_id]
    mine.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    result = []
    for bt in mine:
        s = _strategies.get(bt.get("strategy_id", ""), {})
        result.append({
            "id": bt["id"],
            "strategy_id": bt.get("strategy_id"),
            "strategy_name": s.get("name", "未知策略"),
            "status": bt["status"],
            "created_at": bt.get("created_at"),
            "result": bt.get("result"),
            "error_message": bt.get("error_message"),
        })
    return {"items": result, "total": len(result)}
