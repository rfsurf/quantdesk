"""
Strategy Service — 策略 CRUD + 版本管理
"""

import uuid
from datetime import datetime, timezone

from ..core import StrategyStage
from ..dependencies import _strategies


def list_user_strategies(user_id: str, page: int = 1, page_size: int = 20) -> dict:
    """列出用户策略（分页）"""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    mine = [s for s in _strategies.values() if s["user_id"] == user_id]
    mine.sort(key=lambda x: x["updated_at"], reverse=True)
    start = (page - 1) * page_size
    return {
        "items": mine[start: start + page_size],
        "total": len(mine),
        "page": page,
        "page_size": page_size,
    }


def create_strategy(name: str, config: dict, user_id: str) -> dict:
    """创建新策略"""
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    s = {
        "id": sid, "user_id": user_id, "name": name,
        "status": "draft", "stage": StrategyStage.DRAFT.value,
        "config": config, "created_at": now, "updated_at": now,
        "versions": [{"version": 1, "config": config, "created_at": now}],
    }
    _strategies[sid] = s
    return s


def get_strategy(sid: str, user_id: str) -> dict:
    """获取策略详情"""
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise ValueError("策略不存在")
    return s


def update_strategy(sid: str, user_id: str, name: str | None = None, config: dict | None = None) -> dict:
    """更新策略（自动版本记录）"""
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise ValueError("策略不存在")
    if name is not None:
        s["name"] = name
    if config is not None:
        s["config"] = config
        ver = s.get("versions", [])
        next_ver = len(ver) + 1
        ver.append({
            "version": next_ver, "config": config,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        s["versions"] = ver
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    return s


def delete_strategy(sid: str, user_id: str) -> None:
    """删除策略"""
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise ValueError("策略不存在")
    del _strategies[sid]


def get_versions(sid: str, user_id: str) -> list:
    """获取策略版本历史"""
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise ValueError("策略不存在")
    return s.get("versions", [])
