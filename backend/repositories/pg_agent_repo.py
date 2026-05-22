"""
PostgreSQL Agent Token Repository — Stage 2 实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AgentToken, AgentAuditLog
from ..dependencies import hash_password, verify_password
from .base import BaseRepository


class PgAgentRepo(BaseRepository):
    """Agent Token PostgreSQL 存储"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, entity: dict) -> dict:
        tid = entity.get("id") or uuid.uuid4()
        token_hash = hash_password(entity["raw_token"])

        token = AgentToken(
            id=tid,
            user_id=entity["user_id"],
            name=entity["name"],
            token_hash=token_hash,
            scopes=entity["scopes"],
            expires_at=entity.get("expires_at"),
            paper_trading_only=True,
        )
        self._session.add(token)
        await self._session.commit()
        await self._session.refresh(token)
        return self._to_dict(token)

    async def get(self, entity_id: str) -> Optional[dict]:
        result = await self._session.execute(
            select(AgentToken).where(AgentToken.id == entity_id)
        )
        token = result.scalar_one_or_none()
        return self._to_dict(token) if token else None

    async def get_by_hash(self, token_hash: str) -> Optional[dict]:
        """通过 hash 获取 token（用于验证）"""
        result = await self._session.execute(
            select(AgentToken).where(AgentToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        return self._to_dict(token) if token else None

    async def verify_token(self, raw_token: str) -> Optional[dict]:
        """验证原始 token 并返回记录"""
        # 需要遍历所有 token hash 进行验证
        result = await self._session.execute(
            select(AgentToken).where(AgentToken.is_revoked == False)
        )
        tokens = result.scalars().all()
        for t in tokens:
            if verify_password(raw_token, t.token_hash):
                # 更新 last_used_at
                t.last_used_at = datetime.now(timezone.utc)
                await self._session.commit()
                return self._to_dict(t)
        return None

    async def update(self, entity_id: str, **fields) -> Optional[dict]:
        result = await self._session.execute(
            select(AgentToken).where(AgentToken.id == entity_id)
        )
        token = result.scalar_one_or_none()
        if not token:
            return None
        if "is_revoked" in fields:
            token.is_revoked = fields["is_revoked"]
        if "last_used_at" in fields:
            token.last_used_at = fields["last_used_at"]
        await self._session.commit()
        return self._to_dict(token)

    async def delete(self, entity_id: str) -> bool:
        # Agent Token 不真正删除，只是 revoke
        return await self.revoke(entity_id)

    async def revoke(self, entity_id: str) -> bool:
        result = await self._session.execute(
            update(AgentToken)
            .where(AgentToken.id == entity_id)
            .values(is_revoked=True)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def list(self, **filters) -> list[dict]:
        query = select(AgentToken)
        if "user_id" in filters:
            query = query.where(AgentToken.user_id == filters["user_id"])
        query = query.order_by(AgentToken.created_at.desc())
        result = await self._session.execute(query)
        tokens = result.scalars().all()
        return [self._to_dict(t) for t in tokens]

    async def log_audit(self, log_entry: dict) -> None:
        """记录审计日志"""
        log = AgentAuditLog(
            token_id=log_entry.get("token_id"),
            user_id=log_entry.get("user_id"),
            method=log_entry.get("method"),
            route=log_entry.get("route"),
            scope_class=log_entry.get("scope_class"),
            status_code=log_entry.get("status_code"),
            duration_ms=log_entry.get("duration_ms"),
            ip_address=log_entry.get("ip_address"),
            summary=log_entry.get("summary"),
        )
        self._session.add(log)
        await self._session.commit()

    async def get_audit_logs(self, token_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        """获取审计日志"""
        query = select(AgentAuditLog).order_by(AgentAuditLog.created_at.desc()).limit(limit)
        if token_id:
            query = query.where(AgentAuditLog.token_id == token_id)
        result = await self._session.execute(query)
        logs = result.scalars().all()
        return [
            {
                "id": l.id,
                "token_id": str(l.token_id) if l.token_id else None,
                "user_id": str(l.user_id) if l.user_id else None,
                "method": l.method,
                "route": l.route,
                "scope_class": l.scope_class,
                "status_code": l.status_code,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]

    def _to_dict(self, token: AgentToken) -> dict:
        return {
            "id": str(token.id),
            "user_id": str(token.user_id),
            "name": token.name,
            "scopes": token.scopes,
            "is_revoked": token.is_revoked,
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "paper_trading_only": token.paper_trading_only,
        }