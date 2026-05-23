"""Strategy 路由 — 策略 CRUD + 版本历史"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import (
    StrategyCreate, StrategyUpdate, StrategyResponse, StrategyListItem, PaginatedResponse,
)
from ..dependencies import get_current_user_id
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


def _serialize_strategy(s: dict) -> StrategyResponse:
    return StrategyResponse(
        id=s["id"], name=s["name"], status=s["status"],
        config=s["config"], stage=s.get("stage", "draft"),
        created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
        updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
    )


@router.get("", response_model=PaginatedResponse)
async def list_strategies(
    user_id: str = Depends(get_current_user_id),
    page: int = 1,
    page_size: int = 20,
):
    if settings.USE_POSTGRES:
        from ..services.strategy_service_async import list_user_strategies_pg
        result = list_user_strategies_pg(user_id, page, page_size)
    else:
        from ..services import strategy_service
        result = strategy_service.list_user_strategies(user_id, page, page_size)

    items = [
        StrategyListItem(
            id=s["id"], name=s["name"], status=s["status"],
            stage=s.get("stage", "draft"),
            updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
        )
        for s in result["items"]
    ]
    return PaginatedResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("", status_code=201, response_model=StrategyResponse)
async def create_strategy(body: StrategyCreate, user_id: str = Depends(get_current_user_id)):
    if settings.USE_POSTGRES:
        from ..services.strategy_service_async import create_strategy_pg
        s = create_strategy_pg(body.name, body.config, user_id)
    else:
        from ..services import strategy_service
        s = strategy_service.create_strategy(body.name, body.config, user_id)
    return _serialize_strategy(s)


@router.get("/{sid}", response_model=StrategyResponse)
async def get_strategy(sid: str, user_id: str = Depends(get_current_user_id)):
    try:
        if settings.USE_POSTGRES:
            from ..services.strategy_service_async import get_strategy_pg
            s = get_strategy_pg(sid, user_id)
        else:
            from ..services import strategy_service
            s = strategy_service.get_strategy(sid, user_id)
        return _serialize_strategy(s)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.put("/{sid}", response_model=StrategyResponse)
async def update_strategy(sid: str, body: StrategyUpdate, user_id: str = Depends(get_current_user_id)):
    try:
        if settings.USE_POSTGRES:
            from ..services.strategy_service_async import update_strategy_pg
            s = update_strategy_pg(sid, user_id, body.name, body.config)
        else:
            from ..services import strategy_service
            s = strategy_service.update_strategy(sid, user_id, body.name, body.config)
        return _serialize_strategy(s)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{sid}", status_code=204)
async def delete_strategy(sid: str, user_id: str = Depends(get_current_user_id)):
    try:
        if settings.USE_POSTGRES:
            from ..services.strategy_service_async import delete_strategy_pg
            delete_strategy_pg(sid, user_id)
        else:
            from ..services import strategy_service
            strategy_service.delete_strategy(sid, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/{sid}/versions")
async def list_versions(sid: str, user_id: str = Depends(get_current_user_id), db=Depends(get_db)):
    # PostgreSQL 模式暂不支持版本历史
    if settings.USE_POSTGRES:
        return [{"version": 1, "config": {}, "created_at": datetime.now(timezone.utc).isoformat()}]
    else:
        from ..services import strategy_service
        try:
            return strategy_service.get_versions(sid, user_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
