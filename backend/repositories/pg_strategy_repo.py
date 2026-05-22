"""
PostgreSQL Strategy Repository — Stage 2 实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Strategy, StrategyVersion
from .base import BaseRepository


class PgStrategyRepo(BaseRepository):
    """策略 + 版本 PostgreSQL 存储"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, entity: dict) -> dict:
        sid = entity.get("id") or uuid.uuid4()
        strategy = Strategy(
            id=sid,
            user_id=entity["user_id"],
            name=entity["name"],
            status="draft",
            stage=entity.get("stage", "draft"),
            config=entity["config"],
        )
        self._session.add(strategy)

        # 创建第一个版本
        version = StrategyVersion(
            id=uuid.uuid4(),
            strategy_id=sid,
            version=1,
            config=entity["config"],
            stage=entity.get("stage", "draft"),
        )
        self._session.add(version)
        await self._session.commit()
        await self._session.refresh(strategy)
        return await self._to_dict(strategy)

    async def get(self, entity_id: str) -> Optional[dict]:
        result = await self._session.execute(
            select(Strategy).where(Strategy.id == entity_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            return None
        return await self._to_dict(strategy)

    async def update(self, entity_id: str, **fields) -> Optional[dict]:
        result = await self._session.execute(
            select(Strategy).where(Strategy.id == entity_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            return None

        if "name" in fields and fields["name"] is not None:
            strategy.name = fields["name"]
        if "config" in fields and fields["config"] is not None:
            strategy.config = fields["config"]
            strategy.updated_at = datetime.now(timezone.utc)

            # 创建新版本
            version_num = await self._get_next_version(entity_id)
            version = StrategyVersion(
                id=uuid.uuid4(),
                strategy_id=entity_id,
                version=version_num,
                config=fields["config"],
                stage=strategy.stage,
            )
            self._session.add(version)

        if "status" in fields:
            strategy.status = fields["status"]
        if "stage" in fields:
            strategy.stage = fields["stage"]

        await self._session.commit()
        await self._session.refresh(strategy)
        return await self._to_dict(strategy)

    async def delete(self, entity_id: str) -> bool:
        result = await self._session.execute(
            delete(Strategy).where(Strategy.id == entity_id)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def list(self, **filters) -> list[dict]:
        query = select(Strategy)
        if "user_id" in filters:
            query = query.where(Strategy.user_id == filters["user_id"])
        query = query.order_by(Strategy.updated_at.desc())
        result = await self._session.execute(query)
        strategies = result.scalars().all()
        return [await self._to_dict(s) for s in strategies]

    async def get_versions(self, strategy_id: str) -> list[dict]:
        result = await self._session.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
        )
        versions = result.scalars().all()
        return [
            {
                "id": str(v.id),
                "version": v.version,
                "config": v.config,
                "stage": v.stage,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def _get_next_version(self, strategy_id: str) -> int:
        result = await self._session.execute(
            select(StrategyVersion.version)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
            .limit(1)
        )
        max_ver = result.scalar_one_or_none()
        return (max_ver or 0) + 1

    async def _to_dict(self, strategy: Strategy) -> dict:
        versions = await self.get_versions(str(strategy.id))
        return {
            "id": str(strategy.id),
            "user_id": str(strategy.user_id),
            "name": strategy.name,
            "status": strategy.status,
            "stage": strategy.stage,
            "config": strategy.config,
            "versions": versions,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
        }