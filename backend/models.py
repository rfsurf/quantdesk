"""
QuantDesk SQLAlchemy 数据库模型
15张表，生产环境替换内存存储
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Date, DateTime,
    Text, ForeignKey, UniqueConstraint, Index, JSON,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid():
    return uuid4()


def _now():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------
# 1. Users
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID, primary_key=True, default=_uuid)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    plan          = Column(String(20), default="free")
    is_active     = Column(Boolean, default=True)
    is_admin      = Column(Boolean, default=False)
    ai_api_key    = Column(String(255), nullable=True)
    ai_provider   = Column(String(50), nullable=True)
    ai_calls_count = Column(Integer, default=0)
    last_login_at = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=_now)


# 2. Verification Codes
class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    email      = Column(String(255), nullable=False)
    code       = Column(String(6), nullable=False)
    purpose    = Column(String(20), nullable=False)
    used       = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


# 3. Strategies
class Strategy(Base):
    __tablename__ = "strategies"

    id         = Column(UUID, primary_key=True, default=_uuid)
    user_id    = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(100), nullable=False)
    status     = Column(String(20), default="draft")
    stage      = Column(String(20), default="draft")
    config     = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now)


# 4. Strategy Versions
class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id          = Column(UUID, primary_key=True, default=_uuid)
    strategy_id = Column(UUID, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    version     = Column(Integer, nullable=False)
    config      = Column(JSON, nullable=False)
    stage       = Column(String(20))
    backtest_id = Column(UUID, nullable=True)
    change_note = Column(String(200))
    created_at  = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (UniqueConstraint("strategy_id", "version"),)


# 5. Backtests
class Backtest(Base):
    __tablename__ = "backtests"

    id            = Column(UUID, primary_key=True, default=_uuid)
    strategy_id   = Column(UUID, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    status        = Column(String(20), default="pending")
    params        = Column(JSON, nullable=False)
    result_summary = Column(JSON)
    error_message = Column(Text)
    celery_task_id = Column(String(100))
    started_at    = Column(DateTime(timezone=True))
    finished_at   = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=_now)


# 6. Backtest Trades
class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(UUID, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    trade_date  = Column(Date, nullable=False)
    symbol      = Column(String(20), nullable=False)
    side        = Column(String(5), nullable=False)
    price       = Column(Float)
    volume      = Column(Integer)
    pnl         = Column(Float)
    created_at  = Column(DateTime(timezone=True), default=_now)


# 7. Backtest Daily NAV
class BacktestDailyNAV(Base):
    __tablename__ = "backtest_daily_nav"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id    = Column(UUID, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    trade_date     = Column(Date, nullable=False)
    nav            = Column(Float, nullable=False)
    daily_return   = Column(Float)
    benchmark_nav  = Column(Float)

    __table_args__ = (UniqueConstraint("backtest_id", "trade_date"),)


# 8. Market Daily (TimescaleDB hypertable)
class MarketDaily(Base):
    __tablename__ = "market_daily"

    symbol     = Column(String(20), primary_key=True)
    trade_date = Column(Date, primary_key=True)
    open       = Column(Float)
    high       = Column(Float)
    low        = Column(Float)
    close      = Column(Float)
    volume     = Column(Float)
    amount     = Column(Float)


# 9. Factor Cache (TimescaleDB hypertable)
class FactorCache(Base):
    __tablename__ = "factor_cache"

    symbol      = Column(String(20), primary_key=True)
    trade_date  = Column(Date, primary_key=True)
    factor_name = Column(String(50), primary_key=True)
    factor_value = Column(Float)


# 10. Audit Log
class AuditLog(Base):
    __tablename__ = "audit_log"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"))
    action        = Column(String(50), nullable=False)
    resource_type = Column(String(30))
    resource_id   = Column(UUID)
    ip_address    = Column(INET)
    user_agent    = Column(Text)
    created_at    = Column(DateTime(timezone=True), default=_now)


# 11. WFA Tasks
class WFATask(Base):
    __tablename__ = "wfa_tasks"

    id            = Column(UUID, primary_key=True, default=_uuid)
    strategy_id   = Column(UUID, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    status        = Column(String(20), default="pending")
    mode          = Column(String(20), nullable=False)
    config        = Column(JSON, nullable=False)
    result_summary = Column(JSON)
    celery_task_id = Column(String(100))
    started_at    = Column(DateTime(timezone=True))
    finished_at   = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=_now)


# 12. WFA Window
class WFAWindow(Base):
    __tablename__ = "wfa_windows"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    wfa_id       = Column(UUID, ForeignKey("wfa_tasks.id", ondelete="CASCADE"), nullable=False)
    window_index = Column(Integer, nullable=False)
    is_start     = Column(Date)
    is_end       = Column(Date)
    oos_start    = Column(Date)
    oos_end      = Column(Date)
    is_sharpe    = Column(Float)
    oos_sharpe   = Column(Float)
    oos_return   = Column(Float)
    oos_max_dd   = Column(Float)
    win_rate     = Column(Float)
    passed       = Column(Boolean)

    __table_args__ = (UniqueConstraint("wfa_id", "window_index"),)


# 13. Strategy Scorecards
class StrategyScorecard(Base):
    __tablename__ = "strategy_scorecards"

    id                 = Column(UUID, primary_key=True, default=_uuid)
    strategy_id        = Column(UUID, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    backtest_id        = Column(UUID, ForeignKey("backtests.id"))
    total_score        = Column(Integer, nullable=False)
    earnings_score     = Column(Integer)
    risk_score         = Column(Integer)
    stability_score    = Column(Integer)
    generalization_score = Column(Integer)
    dimension_scores   = Column(JSON, nullable=False)
    grade              = Column(String(2))
    ai_summary         = Column(Text)
    created_at         = Column(DateTime(timezone=True), default=_now)


# 14. Agent Tokens
class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id                  = Column(UUID, primary_key=True, default=_uuid)
    user_id             = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name                = Column(String(100), nullable=False)
    token_hash          = Column(String(64), unique=True, nullable=False)
    scopes              = Column(JSON, nullable=False)
    market_whitelist    = Column(JSON)
    rate_limit_per_min  = Column(Integer, default=30)
    paper_trading_only  = Column(Boolean, default=True)
    is_revoked          = Column(Boolean, default=False)
    last_used_at        = Column(DateTime(timezone=True))
    expires_at          = Column(DateTime(timezone=True))
    created_at          = Column(DateTime(timezone=True), default=_now)


# 15. Agent Audit Log
class AgentAuditLog(Base):
    __tablename__ = "agent_audit_log"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    token_id         = Column(UUID, ForeignKey("agent_tokens.id"))
    user_id          = Column(UUID)
    method           = Column(String(10), nullable=False)
    route            = Column(String(200), nullable=False)
    scope_class      = Column(String(2))
    status_code      = Column(Integer)
    duration_ms      = Column(Integer)
    ip_address       = Column(INET)
    summary          = Column(Text)
    idempotency_key  = Column(String(100))
    created_at       = Column(DateTime(timezone=True), default=_now)


# 16. AI Conversations
class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id            = Column(UUID, primary_key=True, default=_uuid)
    user_id       = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id   = Column(UUID, ForeignKey("strategies.id"))
    messages      = Column(JSON, nullable=False)
    result_config = Column(JSON)
    created_at    = Column(DateTime(timezone=True), default=_now)


# 17. Sync Status (数据同步状态追踪)
class SyncStatus(Base):
    __tablename__ = "sync_status"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    sync_type      = Column(String(20), nullable=False)  # 'market_daily' | 'factor_cache'
    status         = Column(String(20), default="pending")  # 'pending' | 'running' | 'success' | 'failed' | 'skipped'
    started_at     = Column(DateTime(timezone=True))
    finished_at    = Column(DateTime(timezone=True))
    symbols_synced = Column(Integer, default=0)
    records_added  = Column(Integer, default=0)
    error_message  = Column(Text)
    trigger_source = Column(String(20))  # 'scheduled' | 'manual' | 'cli'
    created_at     = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (Index("ix_sync_status_type_finished", "sync_type", "finished_at"),)
