"""
中国A股交易日历
使用 akshare.trade_date_hist_sina() 获取历史交易日
"""

import logging
from datetime import date, datetime, timedelta
from typing import Set

logger = logging.getLogger(__name__)

# 交易日缓存（年度缓存，避免重复请求）
_trade_dates_cache: Set[date] = set()
_cache_year: int = 0


def get_trading_dates(year: int = None) -> Set[date]:
    """
    获取指定年份的交易日集合
    从 akshare 拉取，失败时使用工作日fallback
    """
    global _trade_dates_cache, _cache_year

    target_year = year or datetime.now().year

    # 返回缓存（同一年份）
    if _cache_year == target_year and _trade_dates_cache:
        return _trade_dates_cache

    try:
        import akshare as ak

        # akshare.tool_trade_date_hist_sina() 返回所有历史交易日
        df = ak.tool_trade_date_hist_sina()
        dates: Set[date] = set()
        for d in df["trade_date"]:
            # 支持两种日期格式：YYYY-MM-DD 或 YYYYMMDD
            d_str = str(d)
            if "-" in d_str:
                dt = datetime.strptime(d_str, "%Y-%m-%d").date()
            else:
                dt = datetime.strptime(d_str, "%Y%m%d").date()
            if dt.year == target_year:
                dates.add(dt)

        _trade_dates_cache = dates
        _cache_year = target_year
        logger.info(f"Loaded {len(dates)} trading dates for year {target_year}")
        return dates
    except Exception as e:
        logger.warning(f"Failed to fetch trading calendar: {e}, using weekday fallback")
        return _generate_weekday_calendar(target_year)


def _generate_weekday_calendar(year: int) -> Set[date]:
    """生成工作日日历（不包含周末，但无法排除节假日）"""
    dates: Set[date] = set()
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday=0, Friday=4
            dates.add(current)
        current += timedelta(days=1)
    return dates


def is_trading_day(d: date = None) -> bool:
    """判断指定日期是否为交易日"""
    if d is None:
        d = date.today()

    # 先检查周末
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # 再检查交易日历（排除节假日）
    trading_dates = get_trading_dates(d.year)
    return d in trading_dates


def get_last_trading_day(d: date = None) -> date:
    """获取上一个交易日"""
    if d is None:
        d = date.today()

    prev_day = d - timedelta(days=1)
    max_search = 30  # 最多回溯 30 天（处理春节等长假）

    while not is_trading_day(prev_day) and max_search > 0:
        prev_day -= timedelta(days=1)
        max_search -= 1

    return prev_day


def get_next_trading_day(d: date = None) -> date:
    """获取下一个交易日"""
    if d is None:
        d = date.today()

    next_day = d + timedelta(days=1)
    max_search = 30

    while not is_trading_day(next_day) and max_search > 0:
        next_day += timedelta(days=1)
        max_search -= 1

    return next_day