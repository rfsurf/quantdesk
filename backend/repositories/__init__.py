"""
Repository 工厂 + 初始化
支持内存存储（开发）和 PostgreSQL（生产）切换。
"""

from .memory_user_repo import MemoryUserRepo
from .memory_strategy_repo import MemoryStrategyRepo
from .memory_backtest_repo import MemoryBacktestRepo
from .memory_agent_repo import MemoryAgentRepo
from .pg_user_repo import PgUserRepo
from .pg_strategy_repo import PgStrategyRepo
from .pg_backtest_repo import PgBacktestRepo
from .pg_agent_repo import PgAgentRepo

# 全局存储实例（内存模式）
from ..dependencies import _users, _verification_codes, _strategies, _backtests, _agent_tokens
from ..config import settings

# 当前模式（从配置读取）
USE_POSTGRES = settings.USE_POSTGRES


def get_user_repo(session=None):
    """获取用户 Repository"""
    if USE_POSTGRES and session:
        return PgUserRepo(session)
    return MemoryUserRepo(_users, _verification_codes)


def get_strategy_repo(session=None):
    """获取策略 Repository"""
    if USE_POSTGRES and session:
        return PgStrategyRepo(session)
    return MemoryStrategyRepo(_strategies)


def get_backtest_repo(session=None):
    """获取回测 Repository"""
    if USE_POSTGRES and session:
        return PgBacktestRepo(session)
    return MemoryBacktestRepo(_backtests)


def get_agent_repo(session=None):
    """获取 Agent Token Repository"""
    if USE_POSTGRES and session:
        return PgAgentRepo(session)
    return MemoryAgentRepo(_agent_tokens)


def enable_postgres():
    """切换到 PostgreSQL 存储"""
    global USE_POSTGRES
    USE_POSTGRES = True


def enable_memory():
    """切换到内存存储"""
    global USE_POSTGRES
    USE_POSTGRES = False