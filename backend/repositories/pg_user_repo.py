"""
PostgreSQL User Repository — Stage 2 实现
使用 SQLAlchemy 异步会话操作数据库。
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, VerificationCode
from ..dependencies import hash_password, verify_password
from .base import BaseRepository


class PgUserRepo(BaseRepository):
    """用户 + 验证码 PostgreSQL 存储"""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ---- User CRUD ----

    async def create(self, entity: dict) -> dict:
        user = User(
            id=entity.get("id") or uuid.uuid4(),
            email=entity["email"],
            password_hash=hash_password(entity["password"]),
            plan=entity.get("plan", "free"),
            is_active=True,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_dict(user)

    async def get(self, entity_id: str) -> Optional[dict]:
        result = await self._session.execute(
            select(User).where(User.id == entity_id)
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None

    async def get_by_email(self, email: str) -> Optional[dict]:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None

    async def update(self, entity_id: str, **fields) -> Optional[dict]:
        result = await self._session.execute(
            select(User).where(User.id == entity_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        for k, v in fields.items():
            if hasattr(user, k):
                setattr(user, k, v)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_dict(user)

    async def delete(self, entity_id: str) -> bool:
        result = await self._session.execute(
            delete(User).where(User.id == entity_id)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def list(self, **filters) -> list[dict]:
        result = await self._session.execute(select(User))
        users = result.scalars().all()
        return [self._to_dict(u) for u in users]

    async def verify_password(self, email: str, password: str) -> Optional[dict]:
        """验证密码并返回用户"""
        user = await self.get_by_email(email)
        if not user:
            return None
        if verify_password(password, user["password_hash"]):
            return user
        return None

    # ---- Verification Codes ----

    async def create_code(self, email: str, code: str, purpose: str = "register") -> dict:
        vc = VerificationCode(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self._session.add(vc)
        await self._session.commit()
        return {
            "code": code,
            "expires": vc.expires_at,
            "purpose": purpose,
            "attempts": 0,
        }

    async def get_code(self, email: str) -> Optional[dict]:
        result = await self._session.execute(
            select(VerificationCode)
            .where(VerificationCode.email == email)
            .where(VerificationCode.used == False)
            .order_by(VerificationCode.created_at.desc())
        )
        vc = result.scalar_one_or_none()
        if not vc:
            return None
        return {
            "code": vc.code,
            "expires": vc.expires_at,
            "purpose": vc.purpose,
            "attempts": vc.id,  # 用 id 作为 attempts 的替代
        }

    async def delete_code(self, email: str) -> None:
        await self._session.execute(
            delete(VerificationCode).where(VerificationCode.email == email)
        )
        await self._session.commit()

    # ---- Helpers ----

    def _to_dict(self, user: User) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "password_hash": user.password_hash,
            "plan": user.plan,
            "is_active": user.is_active,
            "ai_api_key": getattr(user, "ai_api_key", None),
            "ai_provider": getattr(user, "ai_provider", None),
            "ai_calls_count": getattr(user, "ai_calls_count", 0),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }