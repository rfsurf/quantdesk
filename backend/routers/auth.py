"""Auth 路由 — 注册/登录/验证码/Token刷新/修改密码"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from ..schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, ChangePasswordRequest
from ..dependencies import (
    _users, _verification_codes, _refresh_tokens,
    get_current_user_id, find_user_by_id, hash_password, verify_password,
)
from ..config import settings
from ..app import limiter
from ..database import get_db
from ..services import auth_service
from ..services.auth_service_async import (
    send_verification_code_async, verify_code_async,
    register_user_async, login_user_async, change_password_async,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/send-code", status_code=204)
@limiter.limit("5/minute")
async def send_code(request: Request, body: dict, db=Depends(get_db)):
    email = body.get("email", "")
    if settings.USE_POSTGRES:
        await send_verification_code_async(email, db)
    else:
        auth_service.send_verification_code(email)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db=Depends(get_db)):
    try:
        if settings.USE_POSTGRES:
            await verify_code_async(body.email, body.code, db)
            user = await register_user_async(body.email, body.password, db)
        else:
            user = await run_in_threadpool(
                auth_service.register_user, body.email, body.password, body.code
            )
        return {"id": user["id"], "email": user["email"]}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db=Depends(get_db)):
    try:
        if settings.USE_POSTGRES:
            tokens = await login_user_async(body.email, body.password, db)
        else:
            tokens = await run_in_threadpool(
                auth_service.login_user, body.email, body.password
            )
        return tokens
    except ValueError as e:
        raise HTTPException(401, str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    try:
        return auth_service.refresh_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(401, str(e))


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """修改当前用户密码"""
    try:
        if settings.USE_POSTGRES:
            return await change_password_async(user_id, body.old_password, body.new_password, db)
        else:
            # 内存模式
            user = find_user_by_id(user_id)
            if not user:
                raise HTTPException(401, "用户不存在")
            if not verify_password(body.old_password, user["password_hash"]):
                raise HTTPException(400, "原密码错误")
            user["password_hash"] = hash_password(body.new_password)
            return {"message": "密码已更新"}
    except ValueError as e:
        raise HTTPException(400, str(e))
