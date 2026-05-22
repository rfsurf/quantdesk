"""
Memory Backtest Repository — Stage 1 内存实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from .base import BaseRepository


class MemoryBacktestRepo(BaseRepository):
    """回测任务 内存存储"""

    def __init__(self, store: dict):
        self._store = store

    def create(self, entity: dict) -> dict:
        tid = entity.get("id") or str(uuid.uuid4())
        bt = {
            "id": tid,
            "strategy_id": entity["strategy_id"],
            "user_id": entity["user_id"],
            "status": "pending",
            "params": entity.get("params", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error_message": None,
            "trades": [],
            "nav_series": [],
        }
        self._store[tid] = bt
        return bt

    def get(self, entity_id: str) -> Optional[dict]:
        return self._store.get(entity_id)

    def update(self, entity_id: str, **fields) -> Optional[dict]:
        bt = self._store.get(entity_id)
        if not bt:
            return None
        for k, v in fields.items():
            bt[k] = v
        return bt

    def delete(self, entity_id: str) -> bool:
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    def list(self, **filters) -> list[dict]:
        user_id = filters.get("user_id")
        strategy_id = filters.get("strategy_id")
        items = list(self._store.values())
        if user_id:
            items = [b for b in items if b.get("user_id") == user_id]
        if strategy_id:
            items = [b for b in items if b.get("strategy_id") == strategy_id]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def find_latest_done(self, strategy_id: str) -> Optional[dict]:
        best = None
        for bt in self._store.values():
            if bt.get("strategy_id") == strategy_id and bt.get("status") == "done":
                if best is None or bt.get("created_at", "") > best.get("created_at", ""):
                    best = bt
        return best
