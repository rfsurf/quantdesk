"""
QuantDesk 数据库连接管理
异步 SQLAlchemy + PostgreSQL/TimescaleDB
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine, text

from .config import settings
from .models import Base

# 异步引擎（FastAPI 使用）
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 同步引擎（Celery / 数据管线使用）
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)


async def init_db():
    """创建所有表（开发环境，生产用 Alembic 迁移）"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 激活 TimescaleDB 扩展
    async with async_engine.connect() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            await conn.commit()
        except Exception:
            pass  # 可能已安装

    # 将 market_daily 转为 hypertable（如果尚未转换）
    async with async_engine.connect() as conn:
        try:
            await conn.execute(text(
                "SELECT create_hypertable('market_daily', 'trade_date', if_not_exists => true)"
            ))
            await conn.execute(text(
                "SELECT add_dimension('market_daily', 'symbol', number_partitions => 10, if_not_exists => true)"
            ))
            await conn.commit()
        except Exception:
            pass

    # factor_cache hypertable
    async with async_engine.connect() as conn:
        try:
            await conn.execute(text(
                "SELECT create_hypertable('factor_cache', 'trade_date', if_not_exists => true)"
            ))
            await conn.execute(text(
                "SELECT add_dimension('factor_cache', 'factor_name', number_partitions => 8, if_not_exists => true)"
            ))
            await conn.commit()
        except Exception:
            pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
