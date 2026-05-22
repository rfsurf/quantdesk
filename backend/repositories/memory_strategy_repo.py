"""
Memory Strategy Repository — Stage 1 内存实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from .base import BaseRepository


class MemoryStrategyRepo(BaseRepository):
    """策略 + 版本 内存存储"""

    def __init__(self, store: dict):
        self._store = store

    def create(self, entity: dict) -> dict:
        sid = entity.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        s = {
            "id": sid,
            "user_id": entity["user_id"],
            "name": entity["name"],
            "status": "draft",
            "stage": entity.get("stage", "draft"),
            "config": entity["config"],
            "created_at": now,
            "updated_at": now,
            "versions": [{"version": 1, "config": entity["config"], "created_at": now}],
        }
        self._store[sid] = s
        return s

    def get(self, entity_id: str) -> Optional[dict]:
        return self._store.get(entity_id)

    def update(self, entity_id: str, **fields) -> Optional[dict]:
        s = self._store.get(entity_id)
        if not s:
            return None
        if "name" in fields and fields["name"] is not None:
            s["name"] = fields["name"]
        if "config" in fields and fields["config"] is not None:
            s["config"] = fields["config"]
            ver = s.get("versions", [])
            ver.append({
                "version": len(ver) + 1,
                "config": fields["config"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            s["versions"] = ver
        s["updated_at"] = datetime.now(timezone.utc).isoformat()
        return s

    def delete(self, entity_id: str) -> bool:
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    def list(self, **filters) -> list[dict]:
        user_id = filters.get("user_id")
        items = list(self._store.values())
        if user_id:
            items = [s for s in items if s["user_id"] == user_id]
        items.sort(key=lambda x: x["updated_at"], reverse=True)
        return items
