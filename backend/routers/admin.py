"""Admin 路由 — 管理后台: 用户/策略/回测/Token 管理 + 审计日志 + 数据同步"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from ..dependencies import (
    get_current_user_id, check_admin, find_user_by_id, set_admin,
    _users, _strategies, _backtests, _agent_tokens, _agent_audit,
)
from ..schemas import SyncTriggerResponse, SyncStatusResponse
from ..database import sync_engine

router = APIRouter(prefix="/api/admin", tags=["Admin"])

start_time = time.time()


@router.get("/stats")
async def admin_stats(user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    uptime = (time.time() - start_time) / 3600
    done_bt = [b for b in _backtests.values() if b["status"] == "done"]
    failed_bt = [b for b in _backtests.values() if b["status"] == "failed"]
    admin_count = len([u for u in _users.values() if u.get("is_admin")])
    return {
        "users": len(_users),
        "admins": admin_count,
        "strategies": len(_strategies),
        "backtests": len(_backtests),
        "backtests_done": len(done_bt),
        "backtests_failed": len(failed_bt),
        "agent_tokens": len([t for t in _agent_tokens.values() if not t.get("is_revoked")]),
        "agent_tokens_revoked": len([t for t in _agent_tokens.values() if t.get("is_revoked")]),
        "api_health": "ok",
        "uptime_hours": round(uptime, 1),
        "audit_logs": len(_agent_audit),
    }


@router.get("/audit-logs")
async def admin_get_audit_logs(user_id: str = Depends(get_current_user_id)):
    """获取审计日志"""
    check_admin(user_id)
    logs = _agent_audit[-100:] if _agent_audit else []
    return {"items": logs, "total": len(_agent_audit)}


@router.post("/users/{uid}/set-admin")
async def admin_set_admin_role(uid: str, user_id: str = Depends(get_current_user_id)):
    """设置用户为管理员"""
    check_admin(user_id)
    if uid == user_id:
        raise HTTPException(400, "您已是管理员")
    if not set_admin(uid):
        raise HTTPException(404, "用户不存在")
    return {"message": "已设置为管理员"}


@router.get("/users")
async def admin_list_users(user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    result = []
    for email, u in _users.items():
        strategies = [s for s in _strategies.values() if s["user_id"] == u["id"]]
        bts = [b for b in _backtests.values() if b.get("user_id") == u["id"]]
        result.append({
            "id": u["id"], "email": u["email"], "plan": u.get("plan", "free"),
            "strategy_count": len(strategies), "backtest_count": len(bts),
            "created_at": u.get("created_at"),
        })
    return {"items": result, "total": len(result)}


@router.delete("/users/{uid}", status_code=204)
async def admin_delete_user(uid: str, user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    if uid == user_id:
        raise HTTPException(400, "不能删除自己")
    target = find_user_by_id(uid)
    if not target:
        raise HTTPException(404, "用户不存在")
    email = target["email"]
    for k, v in list(_strategies.items()):
        if v["user_id"] == uid:
            del _strategies[k]
    for k, v in list(_backtests.items()):
        if v.get("user_id") == uid:
            del _backtests[k]
    for k, v in list(_agent_tokens.items()):
        if v["user_id"] == uid:
            del _agent_tokens[k]
    del _users[email]


@router.get("/strategies")
async def admin_list_all_strategies(user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    result = []
    for sid, s in _strategies.items():
        user = find_user_by_id(s["user_id"])
        result.append({
            "id": s["id"], "name": s["name"], "status": s["status"],
            "stage": s.get("stage", "draft"),
            "user_email": user["email"] if user else "unknown",
            "user_id": s["user_id"],
            "created_at": s["created_at"], "updated_at": s["updated_at"],
        })
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"items": result, "total": len(result)}


@router.delete("/strategies/{sid}", status_code=204)
async def admin_delete_strategy(sid: str, user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    if sid not in _strategies:
        raise HTTPException(404, "策略不存在")
    for k, v in list(_backtests.items()):
        if v.get("strategy_id") == sid:
            del _backtests[k]
    del _strategies[sid]


@router.get("/backtests")
async def admin_list_all_backtests(user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    result = []
    for bid, b in _backtests.items():
        strategy = _strategies.get(b.get("strategy_id", ""), {})
        user = find_user_by_id(b.get("user_id", ""))
        result.append({
            "id": b["id"],
            "strategy_name": strategy.get("name", "unknown"),
            "status": b["status"],
            "user_email": user["email"] if user else "unknown",
            "created_at": b.get("created_at"),
        })
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": result, "total": len(result)}


@router.delete("/backtests/{bid}", status_code=204)
async def admin_delete_backtest(bid: str, user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    if bid not in _backtests:
        raise HTTPException(404, "回测不存在")
    del _backtests[bid]


@router.get("/agent-tokens")
async def admin_list_all_agent_tokens(user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    result = []
    for hashed, t in _agent_tokens.items():
        user = find_user_by_id(t["user_id"])
        result.append({
            "id": str(t["id"]), "name": t["name"], "scopes": t["scopes"],
            "is_revoked": t.get("is_revoked", False),
            "user_email": user["email"] if user else "unknown",
            "created_at": t["created_at"].isoformat(),
            "last_used_at": t["last_used_at"].isoformat() if t.get("last_used_at") else None,
        })
    return {"items": result, "total": len(result)}


@router.delete("/agent-tokens/{tid}", status_code=204)
async def admin_revoke_agent_token(tid: str, user_id: str = Depends(get_current_user_id)):
    check_admin(user_id)
    for h, t in list(_agent_tokens.items()):
        if str(t["id"]) == tid:
            t["is_revoked"] = True
            return
    raise HTTPException(404)


# ====================================================================
# 数据同步管理
# ====================================================================

@router.post("/sync/market-daily", response_model=SyncTriggerResponse)
async def admin_trigger_market_sync(
    user_id: str = Depends(get_current_user_id),
    full_sync: bool = False,
):
    """手动触发行情数据同步"""
    check_admin(user_id)

    from ..tasks import sync_market_data

    task = sync_market_data.apply_async(args=["manual"])
    return SyncTriggerResponse(
        task_id=str(task.id),
        sync_type="incremental" if not full_sync else "full",
        status="triggered",
        message="增量同步已触发，请通过 /sync/status 查看进度",
    )


@router.post("/sync/factors", response_model=SyncTriggerResponse)
async def admin_trigger_factors_sync(user_id: str = Depends(get_current_user_id)):
    """手动触发因子预计算"""
    check_admin(user_id)

    from ..tasks import precompute_factors_task

    task = precompute_factors_task.apply_async(args=["manual"])
    return SyncTriggerResponse(
        task_id=str(task.id),
        sync_type="factors",
        status="triggered",
        message="因子预计算已触发",
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
async def admin_get_sync_status(
    user_id: str = Depends(get_current_user_id),
    sync_type: str = "market_daily",
):
    """获取最近同步状态"""
    check_admin(user_id)

    with sync_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT * FROM sync_status
                WHERE sync_type = :stype
                ORDER BY created_at DESC LIMIT 1
            """),
            {"stype": sync_type},
        ).fetchone()

        if result is None:
            return SyncStatusResponse(
                status="never_synced",
                message="从未执行同步",
            )

        r = result._mapping
        return SyncStatusResponse(
            status=r["status"],
            last_sync=r["finished_at"],
            symbols_synced=r["symbols_synced"],
            records_added=r["records_added"],
            error_message=r["error_message"],
            trigger_source=r["trigger_source"],
        )
