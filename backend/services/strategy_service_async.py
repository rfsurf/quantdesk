"""
Strategy Service 异步版本 — 支持 PostgreSQL 存储
使用 sync_engine 进行数据库操作
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ..core import StrategyStage
from ..config import settings
from ..database import sync_engine
from ..models import Strategy


def list_user_strategies_pg(user_id: str, page: int = 1, page_size: int = 20) -> dict:
    """列出用户策略（分页）- PostgreSQL"""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    user_uuid = uuid.UUID(user_id)

    with sync_engine.connect() as conn:
        # 查询总数
        count_result = conn.execute(
            text("SELECT COUNT(*) FROM strategies WHERE user_id = :uid"),
            {"uid": user_uuid}
        )
        total = count_result.scalar() or 0

        # 查询列表
        offset = (page - 1) * page_size
        result = conn.execute(
            text("""
                SELECT id, name, status, config, updated_at
                FROM strategies
                WHERE user_id = :uid
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"uid": user_uuid, "limit": page_size, "offset": offset}
        )
        rows = result.fetchall()

    items = []
    for row in rows:
        items.append({
            "id": str(row[0]),
            "name": row[1],
            "status": row[2] or "draft",
            "stage": StrategyStage.DRAFT.value,
            "config": row[3] or {},
            "updated_at": row[4].isoformat() if row[4] else None,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def create_strategy_pg(name: str, config: dict, user_id: str) -> dict:
    """创建新策略 - PostgreSQL"""
    sid = uuid.uuid4()
    user_uuid = uuid.UUID(user_id)  # 转换为 UUID
    now = datetime.now(timezone.utc)

    with sync_engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO strategies (id, user_id, name, status, config, created_at, updated_at)
                VALUES (:id, :user_id, :name, 'draft', :config::json, :created_at, :updated_at)
            """),
            {"id": sid, "user_id": user_uuid, "name": name, "config": json.dumps(config), "created_at": now, "updated_at": now}
        )
        conn.commit()

    return {
        "id": str(sid),
        "user_id": user_id,
        "name": name,
        "status": "draft",
        "stage": StrategyStage.DRAFT.value,
        "config": config,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def get_strategy_pg(sid: str, user_id: str) -> dict:
    """获取策略详情 - PostgreSQL"""
    user_uuid = uuid.UUID(user_id)
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, user_id, name, status, config, created_at, updated_at FROM strategies WHERE id = :sid"),
            {"sid": sid}
        )
        row = result.fetchone()

    if not row or row[1] != user_uuid:
        raise ValueError("策略不存在")

    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "name": row[2],
        "status": row[3] or "draft",
        "stage": StrategyStage.DRAFT.value,
        "config": row[4] or {},
        "created_at": row[5].isoformat() if row[5] else None,
        "updated_at": row[6].isoformat() if row[6] else None,
    }


def update_strategy_pg(sid: str, user_id: str, name: Optional[str] = None, config: Optional[dict] = None) -> dict:
    """更新策略 - PostgreSQL"""
    user_uuid = uuid.UUID(user_id)
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, user_id FROM strategies WHERE id = :sid"),
            {"sid": sid}
        )
        row = result.fetchone()

        if not row or row[1] != user_uuid:
            raise ValueError("策略不存在")

        now = datetime.now(timezone.utc)
        conn.execute(
            text("UPDATE strategies SET name = COALESCE(:name, name), config = COALESCE(:config::json, config), updated_at = :updated_at WHERE id = :sid"),
            {"sid": sid, "name": name, "config": json.dumps(config) if config else None, "updated_at": now}
        )
        conn.commit()

    return get_strategy_pg(sid, user_id)


def delete_strategy_pg(sid: str, user_id: str) -> None:
    """删除策略 - PostgreSQL"""
    user_uuid = uuid.UUID(user_id)
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, user_id FROM strategies WHERE id = :sid"),
            {"sid": sid}
        )
        row = result.fetchone()

        if not row or row[1] != user_uuid:
            raise ValueError("策略不存在")

        conn.execute(text("DELETE FROM strategies WHERE id = :sid"), {"sid": sid})
        conn.commit()