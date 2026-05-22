"""
QuantDesk WFA 滚动前向分析引擎
支持 Standard (滚动) 和 Anchored (锚定起点) 两种模式
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from .core import WFAResult


class WFAEngine:
    """Walk-Forward Analysis 引擎"""

    MIN_IS_DAYS = 252        # 训练集最少1年
    MIN_OOS_DAYS = 20        # 样本外至少20天

    def __init__(self, config: dict):
        self.total_days = config.get("total_days", 0)
        self.is_window = config.get("is_window", 500)
        self.oos_window = config.get("oos_window", 180)
        self.step = config.get("step", 180)
        self.mode = config.get("mode", "standard")

    def _generate_windows(self) -> list[dict]:
        """生成时间窗口列表"""
        if self.total_days < self.is_window + self.oos_window:
            raise ValueError(
                f"数据不足: 需要至少 {self.is_window + self.oos_window} 天，只有 {self.total_days} 天"
            )
        if self.is_window < self.MIN_IS_DAYS:
            raise ValueError(f"训练窗口至少 {self.MIN_IS_DAYS} 天（1年）")
        if self.oos_window < self.MIN_OOS_DAYS:
            raise ValueError(f"OOS窗口至少 {self.MIN_OOS_DAYS} 天")

        windows = []
        if self.mode == "standard":
            is_start = 0
            while is_start + self.is_window + self.oos_window <= self.total_days:
                windows.append({
                    "is_start": is_start,
                    "is_end": is_start + self.is_window - 1,
                    "oos_start": is_start + self.is_window,
                    "oos_end": is_start + self.is_window + self.oos_window - 1,
                    "index": len(windows) + 1,
                })
                is_start += self.step

        elif self.mode == "anchored":
            oos_start = self.is_window
            while oos_start + self.oos_window <= self.total_days:
                windows.append({
                    "is_start": 0,
                    "is_end": oos_start - 1,
                    "oos_start": oos_start,
                    "oos_end": oos_start + self.oos_window - 1,
                    "index": len(windows) + 1,
                })
                oos_start += self.step

        return windows

    @staticmethod
    def _compute_summary(results: list[WFAResult]) -> dict:
        """计算WFA汇总结论"""
        if not results:
            return {
                "overall_passed": False,
                "oos_pass_rate": 0.0,
                "wfa_score": 0,
                "overfitting_warning": False,
                "windows": [],
            }

        pass_count = sum(1 for r in results if r.passed)
        pass_rate = pass_count / len(results)
        overall_passed = pass_rate >= 0.6       # 至少60%窗口通过

        # 过拟合检测：OOS夏普平均值远低于IS夏普
        is_sharpes = [r.is_sharpe for r in results if r.is_sharpe != 0]
        oos_sharpes = [r.oos_sharpe for r in results]
        avg_is = sum(is_sharpes) / len(is_sharpes) if is_sharpes else 0
        avg_oos = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0
        overfitting = avg_is > 0 and avg_oos < avg_is * 0.3

        # WFA评分: 通过率×100
        wfa_score = int(pass_rate * 100)

        return {
            "overall_passed": overall_passed,
            "oos_pass_rate": round(pass_rate, 3),
            "wfa_score": wfa_score,
            "overfitting_warning": overfitting,
            "avg_is_sharpe": round(avg_is, 4),
            "avg_oos_sharpe": round(avg_oos, 4),
            "windows": [
                {
                    "window": r.window,
                    "oos_sharpe": r.oos_sharpe,
                    "oos_return": r.oos_return,
                    "passed": r.passed,
                }
                for r in results
            ],
        }
