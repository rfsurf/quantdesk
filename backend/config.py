"""
QuantDesk 环境配置
所有配置项通过环境变量注入，生产环境强制要求 JWT_SECRET、DB 密码等关键变量。
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


class Settings:
    APP_NAME: str = "QuantDesk"
    VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("QUANTDESK_DEBUG", "false").lower() == "true"
    USE_POSTGRES: bool = os.getenv("QUANTDESK_USE_POSTGRES", "true").lower() == "true"

    DATABASE_URL: str = os.getenv(
        "QUANTDESK_DATABASE_URL",
        "postgresql+asyncpg://quantdesk:quantdesk2024@localhost:5432/quantdesk",
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "QUANTDESK_DATABASE_URL_SYNC",
        "postgresql://quantdesk:quantdesk2024@localhost:5432/quantdesk",
    )
    REDIS_URL: str = os.getenv("QUANTDESK_REDIS_URL", "redis://redis:6379/0")

    JWT_SECRET: str = os.getenv("QUANTDESK_JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DEEPSEEK_API_KEY: str = os.getenv("QUANTDESK_DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv(
        "QUANTDESK_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )
    AI_MODEL: str = os.getenv("QUANTDESK_AI_MODEL", "deepseek-chat")

    AGENT_LIVE_TRADING_ENABLED: bool = (
        os.getenv("QUANTDESK_AGENT_LIVE_TRADING_ENABLED", "false").lower() == "true"
    )
    AGENT_JOBS_MAX_WORKERS: int = int(os.getenv("QUANTDESK_AGENT_JOBS_MAX_WORKERS", "4"))

    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv(
            "QUANTDESK_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if o.strip()
    ]

    ADMIN_EMAIL: str = os.getenv("QUANTDESK_ADMIN_EMAIL", "admin@quantdesk.dev")

    # 数据库连接池
    DB_POOL_SIZE: int = int(os.getenv("QUANTDESK_DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("QUANTDESK_DB_MAX_OVERFLOW", "20"))


settings = Settings()


def validate_settings() -> list[str]:
    """启动时校验关键配置，返回错误列表。为空表示通过。"""
    errors = []

    # JWT_SECRET 必须设置且足够强
    if not settings.JWT_SECRET:
        errors.append("QUANTDESK_JWT_SECRET 环境变量未设置。请生成至少32字符的随机密钥。")
    elif len(settings.JWT_SECRET) < 32:
        errors.append(f"QUANTDESK_JWT_SECRET 长度不足（当前 {len(settings.JWT_SECRET)} 字符，需要至少 32）。")
    elif settings.JWT_SECRET in ("change-me-to-64-random-hex-chars", "your-secret-key",
                                  "secret", "changeme", "test"):
        errors.append("QUANTDESK_JWT_SECRET 使用了已知弱密码，请更换为随机生成的强密钥。")

    # 生产环境额外检查
    if not settings.DEBUG:
        if "CHANGE_ME" in settings.DATABASE_URL:
            errors.append("生产环境必须设置 QUANTDESK_DATABASE_URL（当前包含占位符 CHANGE_ME）。")
        if settings.CORS_ORIGINS and "localhost" in str(settings.CORS_ORIGINS).lower():
            logger.warning("生产环境 CORS_ORIGINS 包含 localhost，请确认是否为预期行为。")

    return errors
