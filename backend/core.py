"""
QuantDesk 核心数据类型
所有引擎模块共享的基础数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import date, datetime


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class StrategyStage(Enum):
    DRAFT = "draft"
    STAGED = "staged"
    TESTED = "tested"
    VERIFIED = "verified"
    LIVE = "live"


@dataclass
class PositionInfo:
    shares: int
    avg_cost: float


@dataclass
class Trade:
    date: date
    symbol: str
    side: Side
    price: float
    volume: int
    pnl: Optional[float] = None
    note: Optional[str] = None


@dataclass
class NavPoint:
    date: date
    nav: float
    daily_return: Optional[float] = None
    benchmark_nav: Optional[float] = None


@dataclass
class BacktestConfig:
    initial_cash: float = 100000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0001
    max_positions: int = 10
    stop_loss_pct: Optional[float] = None
    stop_profit_pct: Optional[float] = None

    def __post_init__(self):
        if self.commission_rate < 0:
            raise ValueError("费率不能为负")
        if self.slippage_rate < 0:
            raise ValueError("滑点不能为负")
        if self.max_positions <= 0:
            raise ValueError("最大持仓数必须大于0")


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    volatility: float
    total_trades: int
    profit_factor: float
    calmar_ratio: float = 0.0
    max_dd_days: int = 0
    trades: list = field(default_factory=list)
    nav_series: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "volatility": self.volatility,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "calmar_ratio": self.calmar_ratio,
            "max_dd_days": self.max_dd_days,
        }


@dataclass
class WFAResult:
    window: int
    is_start: Optional[date] = None
    is_end: Optional[date] = None
    oos_start: Optional[date] = None
    oos_end: Optional[date] = None
    is_sharpe: float = 0.0
    oos_sharpe: float = 0.0
    oos_return: float = 0.0
    oos_max_dd: float = 0.0
    win_rate: float = 0.0
    passed: bool = False
