"""
Memory User Repository — Stage 1 内存实现
包装 _users / _verification_codes dict，提供与 PostgreSQL 版本一致的接口。
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from passlib.context import CryptContext

from .base import BaseRepository

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MemoryUserRepo(BaseRepository):
    """用户 + 验证码 内存存储"""

    def __init__(self, users: dict, codes: dict):
        self._users = users
        self._codes = codes

    # ---- User CRUD ----

    def create(self, entity: dict) -> dict:
        email = entity["email"]
        user_id = entity.get("id") or str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password_hash": pwd.hash(entity["password"]),
            "plan": entity.get("plan", "free"),
            "ai_api_key": entity.get("ai_api_key"),
            "ai_provider": entity.get("ai_provider"),
            "ai_calls_count": entity.get("ai_calls_count", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[email] = user
        return user

    def get(self, entity_id: str) -> Optional[dict]:
        for u in self._users.values():
            if u["id"] == entity_id:
                return u
        return None

    def get_by_email(self, email: str) -> Optional[dict]:
        return self._users.get(email)

    def update(self, entity_id: str, **fields) -> Optional[dict]:
        user = self.get(entity_id)
        if not user:
            return None
        for k, v in fields.items():
            user[k] = v
        return user

    def delete(self, entity_id: str) -> bool:
        for email, u in list(self._users.items()):
            if u["id"] == entity_id:
                del self._users[email]
                return True
        return False

    def list(self, **filters) -> list[dict]:
        return list(self._users.values())

    # ---- Verification Codes ----

    def create_code(self, email: str, code: str, purpose: str = "register") -> dict:
        stored = {
            "code": code,
            "expires": datetime.now(timezone.utc).replace(minute=datetime.now(timezone.utc).minute + 5),
            "purpose": purpose,
            "attempts": 0,
        }
        self._codes[email] = stored
        return stored

    def get_code(self, email: str) -> Optional[dict]:
        return self._codes.get(email)

    def delete_code(self, email: str) -> None:
        self._codes.pop(email, None)

    def incr_attempts(self, email: str) -> int:
        stored = self._codes.get(email)
        if stored:
            stored["attempts"] = stored.get("attempts", 0) + 1
            return stored["attempts"]
        return 0
