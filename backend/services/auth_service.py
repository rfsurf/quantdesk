"""
Auth Service — 注册/登录/Token签发/密码校验
可脱离 FastAPI 独立单元测试。
"""

import uuid
from datetime import datetime, timedelta, timezone

from ..dependencies import (
    hash_password, verify_password, _users, _verification_codes, _refresh_tokens,
    find_user_by_id, JWT_SECRET, JWT_ALGORITHM,
)
from ..config import settings


def send_verification_code(email: str) -> str:
    """生成并存储验证码，返回 code。生产环境应通过邮件发送。"""
    if settings.DEBUG:
        code = "000000"
    else:
        import secrets
        code = str(secrets.randbelow(900000) + 100000)

    _verification_codes[email] = {
        "code": code,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=5),
        "purpose": "register",
        "attempts": 0,
    }
    return code


def register_user(email: str, password: str, code: str) -> dict:
    """注册新用户，返回 user dict"""
    stored = _verification_codes.get(email)
    if stored is None:
        raise ValueError("请先获取验证码")
    if stored.get("purpose") != "register":
        raise ValueError("验证码用途不匹配")
    if stored["attempts"] >= 3:
        del _verification_codes[email]
        raise ValueError("验证码尝试次数过多，请重新获取")
    stored["attempts"] = stored.get("attempts", 0) + 1
    if stored["code"] != code:
        raise ValueError("验证码错误")
    if datetime.now(timezone.utc) > stored["expires"]:
        raise ValueError("验证码已过期")

    del _verification_codes[email]

    if email in _users:
        raise ValueError("该邮箱已注册")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "plan": "free",
        "ai_api_key": None,
        "ai_provider": None,
        "ai_calls_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users[email] = user
    return user


def login_user(email: str, password: str) -> dict:
    """验证凭证，返回 tokens"""
    user = _users.get(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("邮箱或密码错误")
    return _issue_tokens(user)


def refresh_token(refresh_token: str) -> dict:
    """使用 refresh token 换取新 tokens"""
    stored = _refresh_tokens.pop(refresh_token, None)
    if stored is None or datetime.now(timezone.utc) > stored["expires"]:
        raise ValueError("refresh token无效或已过期")

    user = find_user_by_id(stored["user_id"])
    if not user:
        raise ValueError("用户不存在")
    return _issue_tokens(user)


def _issue_tokens(user: dict) -> dict:
    from jose import jwt
    from ..schemas import TokenResponse

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
