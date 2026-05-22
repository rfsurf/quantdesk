"""
Auth Service 异步版本 — 支持 PostgreSQL 存储
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select

from ..dependencies import hash_password, verify_password, JWT_SECRET, JWT_ALGORITHM, _refresh_tokens
from ..config import settings
from ..models import User, VerificationCode
from ..schemas import TokenResponse


async def send_verification_code_async(email: str, session) -> str:
    """生成并存储验证码到数据库"""
    if settings.DEBUG:
        code = "000000"
    else:
        code = str(secrets.randbelow(900000) + 100000)

    vc = VerificationCode(
        email=email,
        code=code,
        purpose="register",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(vc)
    await session.commit()
    return code


async def verify_code_async(email: str, code: str, session) -> bool:
    """验证验证码"""
    result = await session.execute(
        select(VerificationCode)
        .where(VerificationCode.email == email)
        .where(VerificationCode.used == False)
        .where(VerificationCode.expires_at > datetime.now(timezone.utc))
        .order_by(VerificationCode.created_at.desc())
    )
    vc = result.scalar_one_or_none()
    if not vc:
        raise ValueError("请先获取验证码")
    if vc.purpose != "register":
        raise ValueError("验证码用途不匹配")
    if vc.code != code:
        raise ValueError("验证码错误")

    vc.used = True
    await session.commit()
    return True


async def register_user_async(email: str, password: str, session) -> dict:
    """注册新用户到数据库"""
    # 检查邮箱是否已存在
    result = await session.execute(
        select(User).where(User.email == email)
    )
    if result.scalar_one_or_none():
        raise ValueError("该邮箱已注册")

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(password),
        plan="free",
        is_admin=(email == settings.ADMIN_EMAIL),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return _user_to_dict(user)


async def login_user_async(email: str, password: str, session) -> dict:
    """验证凭证并返回 tokens"""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("邮箱或密码错误")

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    return _issue_tokens(_user_to_dict(user))


def _issue_tokens(user: dict) -> dict:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user["id"],
        "plan": user["plan"],
        "exp": now + timedelta(days=7),
        "iat": now,
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    refresh = str(uuid.uuid4())
    _refresh_tokens[refresh] = {
        "user_id": user["id"],
        "expires": now + timedelta(days=30),
    }

    return TokenResponse(access_token=access_token, refresh_token=refresh).model_dump()


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "password_hash": user.password_hash,
        "plan": user.plan,
        "is_admin": user.is_admin,
        "ai_api_key": user.ai_api_key,
        "ai_provider": user.ai_provider,
        "ai_calls_count": user.ai_calls_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }