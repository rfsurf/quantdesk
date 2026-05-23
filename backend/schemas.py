"""
QuantDesk Pydantic 数据模型
所有 API 请求/响应的类型定义
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=4, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ------------------------------------------------------------------
# Strategy
# ------------------------------------------------------------------

class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    config: dict = Field(max_length=102400)   # 序列化后最多100KB

    @field_validator("name")
    @classmethod
    def name_no_xss(cls, v: str) -> str:
        v = v.strip()
        if any(tag in v.lower() for tag in ("<script", "<img", "<iframe", "onerror=")):
            raise ValueError("策略名称包含非法字符")
        return v

    @field_validator("config")
    @classmethod
    def config_depth_check(cls, v: dict) -> dict:
        if _json_depth(v) > 5:
            raise ValueError("配置JSON递归深度不能超过5层")
        return v


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    config: Optional[dict] = None


class StrategyResponse(BaseModel):
    id: UUID
    name: str
    status: str
    config: dict
    stage: str = "draft"
    created_at: datetime
    updated_at: datetime


class StrategyListItem(BaseModel):
    id: UUID
    name: str
    status: str
    stage: str
    last_backtest_at: Optional[datetime] = None
    updated_at: datetime


# ------------------------------------------------------------------
# Backtest
# ------------------------------------------------------------------

class BacktestRequest(BaseModel):
    initial_cash: float = Field(default=100000, ge=10000, le=1_000_000_000)
    start_date: date = Field(default_factory=lambda: date.today() - timedelta(days=365))
    end_date: date = Field(default_factory=date.today)
    commission_rate: float = Field(default=0.0003, ge=0, le=0.05)
    slippage_rate: float = Field(default=0.0001, ge=0, le=0.05)
    max_positions: int = Field(default=10, ge=1, le=100)
    stop_loss_pct: Optional[float] = Field(default=None, ge=0, le=50)
    stop_profit_pct: Optional[float] = Field(default=None, ge=0, le=200)

    @model_validator(mode="after")
    def check_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("结束日期必须晚于开始日期")
        days = (self.end_date - self.start_date).days
        if days < 30:
            raise ValueError("回测区间至少30个交易日")
        if days > 3650:
            raise ValueError("回测区间不能超过10年")
        return self


class BacktestTaskResponse(BaseModel):
    task_id: UUID
    status: str = "accepted"
    estimated_duration_s: int = 30


class BacktestResultResponse(BaseModel):
    backtest_id: UUID
    status: str
    result: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


# ------------------------------------------------------------------
# Optimize
# ------------------------------------------------------------------

class ParamRange(BaseModel):
    min: float
    max: float
    step: float

    @field_validator("step")
    @classmethod
    def step_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("步长必须大于0")
        return v


class OptimizeRequest(BaseModel):
    params: dict[str, ParamRange]
    objective: str = "sharpe_ratio"     # sharpe_ratio / calmar_ratio / total_return


# ------------------------------------------------------------------
# WFA
# ------------------------------------------------------------------

class WFARequest(BaseModel):
    mode: str = "standard"               # standard / anchored
    is_window: int = Field(ge=252)       # 最少1年
    oos_window: int = Field(ge=20)       # 最少20天
    step: int = Field(ge=20)

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v: str) -> str:
        if v not in ("standard", "anchored"):
            raise ValueError("模式必须是 standard 或 anchored")
        return v

    @field_validator("oos_window")
    @classmethod
    def oos_minimum(cls, v: int) -> int:
        if v < 20:
            raise ValueError("OOS窗口至少20天")
        return v


# ------------------------------------------------------------------
# AI
# ------------------------------------------------------------------

class AIGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class AIGenerateResponse(BaseModel):
    session_id: UUID
    config: dict
    summary: str   # AI对策略的白话解读


class AIDiagnoseRequest(BaseModel):
    strategy_id: UUID


class AIDiagnoseResponse(BaseModel):
    scorecard: dict
    suggestions: list[str]


class UserAISettingsRequest(BaseModel):
    ai_api_key: str | None = None
    ai_provider: str | None = None  # "deepseek" | "ollama" | None=platform


class UserAISettingsResponse(BaseModel):
    plan: str
    ai_enabled: bool
    ai_calls_used: int
    ai_calls_limit: int  # 0=unlimited (BYOK), -1=no access (free)
    ai_provider: str | None  # null=platform, "deepseek"=BYOK, "ollama"=local
    has_api_key: bool


class UpgradePlanRequest(BaseModel):
    plan: str  # "pro" or "free"


# ------------------------------------------------------------------
# Agent Token
# ------------------------------------------------------------------

VALID_SCOPES = {"R", "B", "W", "N", "C", "T"}


class AgentTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str]
    market_whitelist: Optional[list[str]] = None
    rate_limit_per_min: int = Field(default=30, ge=1, le=300)
    paper_trading_only: bool = True
    expires_in_days: int = Field(default=90, ge=1, le=365)

    @field_validator("scopes")
    @classmethod
    def valid_scopes(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_SCOPES
        if invalid:
            raise ValueError(f"无效的Scope: {invalid}")
        return v


class AgentTokenReveal(BaseModel):
    id: UUID
    name: str
    token: str   # 仅此一次显示
    scopes: list[str]
    expires_at: datetime


class AgentTokenListItem(BaseModel):
    id: UUID
    name: str
    scopes: list[str]
    is_revoked: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    celery_workers: int
    last_data_sync: Optional[str] = None
    uptime_hours: float = 0.0


class SyncTriggerResponse(BaseModel):
    task_id: str
    sync_type: str  # 'incremental' | 'full' | 'factors'
    status: str = "triggered"
    message: str


class SyncStatusResponse(BaseModel):
    status: str  # 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'never_synced'
    last_sync: Optional[datetime] = None
    symbols_synced: Optional[int] = None
    records_added: Optional[int] = None
    error_message: Optional[str] = None
    trigger_source: Optional[str] = None
    message: Optional[str] = None


# ------------------------------------------------------------------
# Pagination
# ------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _json_depth(obj, current=1) -> int:
    if not isinstance(obj, dict):
        return current
    max_child = current
    for v in obj.values():
        if isinstance(v, dict):
            depth = _json_depth(v, current + 1)
            max_child = max(max_child, depth)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    depth = _json_depth(item, current + 1)
                    max_child = max(max_child, depth)
    return max_child
