"""
Memory Agent Repository — Stage 1 内存实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from passlib.context import CryptContext

from .base import BaseRepository

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MemoryAgentRepo(BaseRepository):
    """Agent Token + Audit 内存存储"""

    def __init__(self, tokens: dict, audit: list):
        self._tokens = tokens
        self._audit = audit

    # ---- Token ----

    def create(self, entity: dict) -> dict:
        import secrets
        raw = secrets.token_urlsafe(32)
        token_hash = pwd.hash(raw)
        if len(raw) > 64:
            raw = raw[:64]

        tid = entity.get("id") or uuid.uuid4()
        data = {
            "id": tid,
            "user_id": entity["user_id"],
            "name": entity["name"],
            "scopes": entity["scopes"],
            "is_revoked": False,
            "created_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "_raw": raw,  # 仅创建时返回，之后不可见
        }
        self._tokens[token_hash] = data
        return data

    def get(self, entity_id: str) -> Optional[dict]:
        for h, t in self._tokens.items():
            if str(t["id"]) == str(entity_id):
                return t
        return None

    def get_by_token(self, raw_token: str) -> Optional[dict]:
        for h, data in self._tokens.items():
            try:
                if pwd.verify(raw_token, h):
                    return data
            except Exception:
                continue
        return None

    def update(self, entity_id: str, **fields) -> Optional[dict]:
        t = self.get(entity_id)
        if not t:
            return None
        for k, v in fields.items():
            t[k] = v
        return t

    def revoke(self, entity_id: str) -> bool:
        t = self.get(entity_id)
        if not t:
            return False
        t["is_revoked"] = True
        return True

    def delete(self, entity_id: str) -> bool:
        for h, t in list(self._tokens.items()):
            if str(t["id"]) == str(entity_id):
                del self._tokens[h]
                return True
        return False

    def list(self, **filters) -> list[dict]:
        user_id = filters.get("user_id")
        items = list(self._tokens.values())
        if user_id:
            items = [t for t in items if t["user_id"] == user_id]
        return items

    def list_active(self, user_id: str) -> list[dict]:
        return [t for t in self.list(user_id=user_id) if not t.get("is_revoked")]

    # ---- Audit ----

    def add_audit(self, entry: dict) -> None:
        self._audit.append(entry)
