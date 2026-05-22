"""
QuantDesk 回测引擎
事件驱动的向量化回测，支持多股票、止损止盈、滑点费率的完整模拟
"""

import numpy as np
import pandas as pd
from datetime import date
from typing import Optional

from .core import (
    BacktestConfig,
    BacktestResult,
    NavPoint,
    PositionInfo,
    Side,
    Trade,
)


class BacktestEngine:
    """事件驱动的向量化回测引擎"""

    def __init__(self, config: BacktestConfig):
        if config.commission_rate < 0:
            raise ValueError("费率不能为负")
        if config.max_positions <= 0:
            raise ValueError("最大持仓数必须大于0")
        self.config = config
        self.initial_cash = config.initial_cash
        self.cash = config.initial_cash
        self.positions: dict[str, PositionInfo] = {}
        self.trades: list[Trade] = []
        self.daily_nav: list[NavPoint] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, data: pd.DataFrame, signal_func) -> BacktestResult:
        """
        运行完整回测。

        Parameters
        ----------
        data : DataFrame
            必须包含列 [open, high, low, close, volume]，
            index 为 trade_date 或 [trade_date, symbol] 的 MultiIndex。
        signal_func : callable
            签名 (data, date, positions) → dict[symbol, 1/-1/0]
        """
        if data.empty:
            return self._empty_result()

        if isinstance(data.index, pd.MultiIndex):
            return self._run_multi_symbol(data, signal_func)

        return self._run_single_symbol(data, signal_func)

    # ------------------------------------------------------------------
    # Internal: single-symbol
    # ------------------------------------------------------------------

    def _run_single_symbol(self, data: pd.DataFrame, signal_func) -> BacktestResult:
        symbol = data["symbol"].iloc[0] if "symbol" in data.columns else "UNKNOWN"
        unique_dates = sorted(data.index.unique())
        benchmark_prices = self._load_benchmark(data)

        for i, dt in enumerate(unique_dates):
            day_data = data.loc[dt]
            self._check_risk_management(day_data, dt)
            signals = signal_func(data, dt, self.positions)

            # 先卖
            for sym, sig in signals.items():
                if sig < 0 and sym in self.positions:
                    self._sell(sym, day_data, dt)

            # 后买
            buy_candidates = [
                s for s, sig in signals.items() if sig > 0 and s not in self.positions
            ]
            slots_left = self.config.max_positions - len(self.positions)
            for sym in buy_candidates[:slots_left]:
                self._buy(sym, day_data, dt)

            self._mark_to_market(dt, day_data, benchmark_prices, i)

        return self._compute_result()

    def _run_multi_symbol(self, data: pd.DataFrame, signal_func) -> BacktestResult:
        unique_dates = sorted(data.index.get_level_values(0).unique())
        benchmark = None

        for i, dt in enumerate(unique_dates):
            try:
                day_data = data.loc[dt]
            except KeyError:
                continue

            if isinstance(day_data, pd.Series):
                day_data = day_data.to_frame().T

            self._check_risk_management_multi(day_data, dt)
            signals = signal_func(data, dt, self.positions)

            for sym, sig in signals.items():
                if sig < 0 and sym in self.positions:
                    row = day_data.loc[sym] if sym in day_data.index else day_data.iloc[0]
                    self._sell(sym, row, dt)

            buy_candidates = [
                s for s, sig in signals.items() if sig > 0 and s not in self.positions
            ]
            slots_left = self.config.max_positions - len(self.positions)
            for sym in buy_candidates[:slots_left]:
                row = day_data.loc[sym] if sym in day_data.index else day_data.iloc[0]
                self._buy(sym, row, dt)

            self._mark_to_market_multi(dt, day_data, benchmark, i)

        return self._compute_result()

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def _buy(self, symbol: str, row, dt):
        price = float(row["close"]) * (1 + self.config.slippage_rate)
        slots_available = max(self.config.max_positions - len(self.positions), 1)
        cash_per_slot = self.cash / slots_available
        max_shares = int(cash_per_slot / (price * (1 + self.config.commission_rate)) / 100) * 100

        # 如果按槽位分配不够一手但账户现金够买一手，也买一手
        if max_shares <= 0:
            if self.cash >= price * 100 * (1 + self.config.commission_rate):
                max_shares = 100
            else:
                return

        cost = price * max_shares * (1 + self.config.commission_rate)
        self.cash -= cost
        self.positions[symbol] = PositionInfo(shares=max_shares, avg_cost=price)
        self.trades.append(
            Trade(date=dt, symbol=symbol, side=Side.BUY, price=price, volume=max_shares)
        )

    def _sell(self, symbol: str, row, dt):
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return
        price = float(row["close"]) * (1 - self.config.slippage_rate)
        proceeds = price * pos.shares * (1 - self.config.commission_rate)
        self.cash += proceeds
        pnl = (price - pos.avg_cost) * pos.shares
        self.trades.append(
            Trade(
                date=dt, symbol=symbol, side=Side.SELL,
                price=price, volume=pos.shares, pnl=pnl,
            )
        )

    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------

    def _check_risk_management(self, day_data, dt):
        to_sell = []
        # 确保拿到标量行 — 如果传入多行DataFrame，用dt定位具体行
        if isinstance(day_data, pd.DataFrame):
            if len(day_data) == 1:
                day_data = day_data.iloc[0]
            elif dt is not None and dt in day_data.index:
                day_data = day_data.loc[dt]
                if isinstance(day_data, pd.DataFrame):
                    day_data = day_data.iloc[0]
            else:
                day_data = day_data.iloc[0]
        for symbol, pos in list(self.positions.items()):
            try:
                close = float(day_data["close"])
            except (KeyError, TypeError):
                continue
            if pd.isna(close):
                continue
            pnl_pct = (close / pos.avg_cost - 1) * 100
            if self.config.stop_loss_pct and pnl_pct <= -self.config.stop_loss_pct:
                to_sell.append((symbol, "stop_loss"))
            elif self.config.stop_profit_pct and pnl_pct >= self.config.stop_profit_pct:
                to_sell.append((symbol, "stop_profit"))
        for symbol, reason in to_sell:
            self._sell(symbol, day_data, dt)
            if self.trades:
                self.trades[-1].note = reason

    def _check_risk_management_multi(self, day_data, dt):
        to_sell = []
        for symbol, pos in list(self.positions.items()):
            try:
                row = day_data.loc[symbol]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
            except KeyError:
                continue
            close = float(row["close"])
            if pd.isna(close):
                continue
            pnl_pct = (close / pos.avg_cost - 1) * 100
            if self.config.stop_loss_pct and pnl_pct <= -self.config.stop_loss_pct:
                to_sell.append((symbol, "stop_loss"))
            elif self.config.stop_profit_pct and pnl_pct >= self.config.stop_profit_pct:
                to_sell.append((symbol, "stop_profit"))
        for symbol, reason in to_sell:
            self._sell(symbol, day_data.loc[symbol], dt)
            if self.trades:
                self.trades[-1].note = reason

    # ------------------------------------------------------------------
    # NAV
    # ------------------------------------------------------------------

    def _mark_to_market(self, dt, day_data, benchmark_prices, idx: int):
        if isinstance(day_data, pd.DataFrame):
            day_data = day_data.iloc[0]
        market_value = sum(
            pos.shares * float(day_data["close"]) for pos in self.positions.values()
        )
        total_nav = self.cash + market_value
        prev_nav = self.daily_nav[-1].nav if self.daily_nav else total_nav
        daily_return = (
            (total_nav / prev_nav - 1) if self.daily_nav else 0.0
        )

        bm = None
        if benchmark_prices is not None and idx < len(benchmark_prices):
            bm = float(benchmark_prices[idx])

        self.daily_nav.append(
            NavPoint(date=dt, nav=total_nav, daily_return=daily_return, benchmark_nav=bm)
        )

    def _mark_to_market_multi(self, dt, day_data, benchmark, idx: int):
        market_value = 0.0
        for symbol, pos in self.positions.items():
            try:
                price = day_data.loc[symbol]["close"]
            except KeyError:
                price = pos.avg_cost
            market_value += pos.shares * price
        total_nav = self.cash + market_value
        prev_nav = self.daily_nav[-1].nav if self.daily_nav else total_nav
        daily_return = (total_nav / prev_nav - 1) if self.daily_nav else 0.0
        self.daily_nav.append(
            NavPoint(date=dt, nav=total_nav, daily_return=daily_return, benchmark_nav=benchmark)
        )

    # ------------------------------------------------------------------
    # Result computation
    # ------------------------------------------------------------------

    def _compute_result(self) -> BacktestResult:
        navs = [float(p.nav) if hasattr(p, 'nav') else float(p)
                for p in self.daily_nav]
        returns = [
            float(p.daily_return) if hasattr(p, 'daily_return') and p.daily_return is not None else 0.0
            for p in self.daily_nav
        ]

        if not returns:
            return self._empty_result()

        total_return = (navs[-1] / self.initial_cash - 1.0) if navs else 0.0
        annual_return = self._annualize(total_return, len(returns))
        # 过滤掉首日的0 return
        valid_returns = [r for r in returns if r != 0.0] or returns
        max_dd, max_dd_days = self._calc_max_drawdown(navs)
        sharpe = self._calc_sharpe(valid_returns)
        vol = float(np.std(valid_returns) * np.sqrt(252)) if len(valid_returns) > 1 else 0.0

        completed_trades = [t for t in self.trades if t.side == Side.SELL and t.pnl is not None]
        total_trades = len(completed_trades)
        win_count = sum(1 for t in completed_trades if (t.pnl or 0) > 0)
        win_rate = win_count / max(total_trades, 1)

        profit_factor = self._calc_profit_factor(completed_trades)
        calmar = annual_return / max(max_dd, 0.0001) if max_dd > 0 else 0.0

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            volatility=vol,
            total_trades=total_trades,
            profit_factor=profit_factor,
            calmar_ratio=calmar,
            max_dd_days=max_dd_days,
            trades=self.trades.copy(),
            nav_series=[NavPoint(p.date, p.nav, p.daily_return, p.benchmark_nav)
                       for p in self.daily_nav],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_result(self) -> BacktestResult:
        return BacktestResult(
            total_return=0.0, annual_return=0.0, sharpe_ratio=0.0,
            max_drawdown=0.0, win_rate=0.0, volatility=0.0,
            total_trades=0, profit_factor=0.0,
        )

    def _load_benchmark(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        if "benchmark_nav" in data.columns:
            return data["benchmark_nav"].values
        return None

    def _annualize(self, total_return: float, n_days: int) -> float:
        if n_days <= 0 or total_return <= -1:
            return total_return
        return (1 + total_return) ** (252 / n_days) - 1

    def _calc_sharpe(self, daily_returns: list[float], rf: float = 0.02) -> float:
        if not daily_returns:
            return 0.0
        arr = np.array(daily_returns, dtype=float)
        mean = np.mean(arr) * 252
        std = np.std(arr, ddof=1) * np.sqrt(252)
        if std == 0:
            return 0.0
        return (mean - rf) / std

    def _calc_max_drawdown(self, navs: list[float]) -> tuple[float, int]:
        if not navs:
            return 0.0, 0
        peak = navs[0]
        max_dd = 0.0
        max_dd_days = 0
        dd_start = 0
        in_dd = False

        for i, n in enumerate(navs):
            if n > peak:
                peak = n
                if in_dd:
                    max_dd_days = max(max_dd_days, i - dd_start)
                in_dd = False
            else:
                dd = (peak - n) / peak
                if dd > max_dd:
                    max_dd = dd
                if not in_dd:
                    dd_start = i
                    in_dd = True

        if in_dd:
            max_dd_days = max(max_dd_days, len(navs) - dd_start)

        return max_dd, max_dd_days

    def _calc_profit_factor(self, trades: list[Trade]) -> float:
        gross_profit = sum(t.pnl for t in trades if (t.pnl or 0) > 0)
        gross_loss = abs(sum(t.pnl for t in trades if (t.pnl or 0) < 0))
        return gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
