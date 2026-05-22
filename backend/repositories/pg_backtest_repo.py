"""
PostgreSQL Backtest Repository — Stage 2 实现
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Backtest, BacktestTrade, BacktestDailyNAV
from .base import BaseRepository


class PgBacktestRepo(BaseRepository):
    """回测 PostgreSQL 存储"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, entity: dict) -> dict:
        bt_id = entity.get("id") or uuid.uuid4()
        backtest = Backtest(
            id=bt_id,
            strategy_id=entity["strategy_id"],
            params=entity["params"],
            status="pending",
        )
        self._session.add(backtest)
        await self._session.commit()
        await self._session.refresh(backtest)
        return self._to_dict(backtest)

    async def get(self, entity_id: str) -> Optional[dict]:
        result = await self._session.execute(
            select(Backtest).where(Backtest.id == entity_id)
        )
        bt = result.scalar_one_or_none()
        return self._to_dict(bt) if bt else None

    async def update(self, entity_id: str, **fields) -> Optional[dict]:
        result = await self._session.execute(
            select(Backtest).where(Backtest.id == entity_id)
        )
        bt = result.scalar_one_or_none()
        if not bt:
            return None

        if "status" in fields:
            bt.status = fields["status"]
        if "result" in fields:
            bt.result_summary = fields["result"]
        if "error_message" in fields:
            bt.error_message = fields["error_message"]
        if fields.get("status") == "running":
            bt.started_at = datetime.now(timezone.utc)
        if fields.get("status") in ("done", "failed"):
            bt.finished_at = datetime.now(timezone.utc)

        await self._session.commit()
        await self._session.refresh(bt)
        return self._to_dict(bt)

    async def delete(self, entity_id: str) -> bool:
        result = await self._session.execute(
            delete(Backtest).where(Backtest.id == entity_id)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def list(self, **filters) -> list[dict]:
        query = select(Backtest)
        if "user_id" in filters:
            # 需要关联 strategy 表获取 user_id
            from ..models import Strategy
            query = query.join(Strategy).where(Strategy.user_id == filters["user_id"])
        if "strategy_id" in filters:
            query = query.where(Backtest.strategy_id == filters["strategy_id"])
        query = query.order_by(Backtest.created_at.desc())
        result = await self._session.execute(query)
        backtests = result.scalars().all()
        return [self._to_dict(bt) for bt in backtests]

    async def save_trades(self, backtest_id: str, trades: list[dict]) -> None:
        """保存交易明细"""
        for t in trades:
            trade = BacktestTrade(
                backtest_id=backtest_id,
                trade_date=t["date"],
                symbol=t["symbol"],
                side=t["side"],
                price=t["price"],
                volume=t["volume"],
                pnl=t.get("pnl"),
            )
            self._session.add(trade)
        await self._session.commit()

    async def get_trades(self, backtest_id: str) -> list[dict]:
        """获取交易明细"""
        result = await self._session.execute(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)
            .order_by(BacktestTrade.trade_date)
        )
        trades = result.scalars().all()
        return [
            {
                "date": str(t.trade_date),
                "symbol": t.symbol,
                "side": t.side,
                "price": t.price,
                "volume": t.volume,
                "pnl": t.pnl,
            }
            for t in trades
        ]

    async def save_nav(self, backtest_id: str, nav_series: list[dict]) -> None:
        """保存净值曲线"""
        for item in nav_series:
            nav = BacktestDailyNAV(
                backtest_id=backtest_id,
                trade_date=item["date"],
                nav=item["nav"],
                daily_return=item.get("daily_return"),
            )
            self._session.add(nav)
        await self._session.commit()

    async def get_nav(self, backtest_id: str) -> list[dict]:
        """获取净值曲线"""
        result = await self._session.execute(
            select(BacktestDailyNAV)
            .where(BacktestDailyNAV.backtest_id == backtest_id)
            .order_by(BacktestDailyNAV.trade_date)
        )
        navs = result.scalars().all()
        return [
            {
                "date": str(n.trade_date),
                "nav": n.nav,
                "daily_return": n.daily_return,
            }
            for n in navs
        ]

    def _to_dict(self, bt: Backtest) -> dict:
        return {
            "id": str(bt.id),
            "strategy_id": str(bt.strategy_id),
            "status": bt.status,
            "params": bt.params,
            "result": bt.result_summary,
            "error_message": bt.error_message,
            "celery_task_id": bt.celery_task_id,
            "started_at": bt.started_at.isoformat() if bt.started_at else None,
            "finished_at": bt.finished_at.isoformat() if bt.finished_at else None,
            "created_at": bt.created_at.isoformat() if bt.created_at else None,
        }