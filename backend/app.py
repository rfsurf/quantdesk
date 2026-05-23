"""
QuantDesk FastAPI 应用
完整的 REST API + Agent Gateway

架构: thin assembler — 路由定义见 backend/routers/
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings, validate_settings

# ---------------------------------------------------------------------------
# Limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# App 组装
# ---------------------------------------------------------------------------

app = FastAPI(title="QuantDesk", version="2.0.0", docs_url="/docs")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

# ---------------------------------------------------------------------------
# 启动校验
# ---------------------------------------------------------------------------

_warnings = validate_settings()
if _warnings:
    import logging
    for w in _warnings:
        logging.getLogger("quantdesk").warning(f"Config: {w}")
    if settings.DEBUG:
        logging.getLogger("quantdesk").warning("JWT_SECRET 未设置，使用临时密钥（仅 DEV 模式）。")
    else:
        raise RuntimeError(f"配置错误: {'; '.join(_warnings)}")

# ---------------------------------------------------------------------------
# 启动时创建默认管理员
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def create_default_admin():
    """应用启动时检查并创建默认管理员账号"""
    import logging
    logger = logging.getLogger("quantdesk")

    if not settings.USE_POSTGRES:
        logger.info("内存模式：跳过默认管理员创建")
        return

    from .database import async_engine
    from .models import User
    from .dependencies import hash_password
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    admin_email = settings.ADMIN_EMAIL
    admin_password = os.getenv("QUANTDESK_ADMIN_PASSWORD", "quantdesk")

    async with async_session() as session:
        # 检查管理员是否已存在
        result = await session.execute(select(User).where(User.email == admin_email))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"管理员账号已存在: {admin_email}")
            return

        # 创建默认管理员
        admin = User(
            email=admin_email,
            password_hash=hash_password(admin_password),
            plan="pro",
            is_admin=True,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        logger.info(f"已创建默认管理员: {admin_email} (密码: {admin_password})")

# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------

from .routers.auth import router as auth_router
from .routers.strategy import router as strategy_router
from .routers.backtest import router as backtest_router
from .routers.optimize import router as optimize_router
from .routers.wfa import router as wfa_router
from .routers.ai import router as ai_router
from .routers.admin import router as admin_router
from .routers.agent import router as agent_router
from .routers.data import router as data_router

app.include_router(auth_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(optimize_router)
app.include_router(wfa_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(agent_router)
app.include_router(data_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
