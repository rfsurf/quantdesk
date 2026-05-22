"""
QuantDesk 策略健康评分卡
12维度 × 100分制，评估策略的综合质量
"""

from typing import Optional


class StrategyScorecard:
    """策略健康评分卡 — 12项标准，满分100分"""

    REQUIRED_METRICS = [
        "annual_return", "sharpe_ratio", "calmar_ratio", "excess_alpha",
        "max_drawdown", "volatility", "max_dd_days", "var_99",
        "win_rate", "profit_factor", "monthly_win_pct",
    ]

    def __init__(self, metrics: dict):
        missing = [k for k in self.REQUIRED_METRICS if k not in metrics]
        if missing:
            raise ValueError(f"缺失必需指标: {missing}")
        self.metrics = metrics

    def compute(self) -> dict:
        """计算评分卡，返回完整结果"""
        # 四个维度独立打分
        earnings = self._score_earnings()
        risk = self._score_risk()
        stability = self._score_stability()
        generalization = self._score_generalization()

        total = earnings + risk + stability + generalization
        grade = self._grade(total)

        return {
            "total_score": total,
            "grade": grade,
            "dimension_scores": {
                "earnings": earnings,
                "risk": risk,
                "stability": stability,
                "generalization": generalization,
            },
            "ai_summary": self._generate_summary(total, earnings, risk, stability, generalization),
        }

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _score_earnings(self) -> int:
        """收益质量 满分35"""
        score = 0
        m = self.metrics

        # 年化收益 (0-10)
        ar = m["annual_return"]
        if ar > 0.20: score += 10
        elif ar > 0.15: score += 8
        elif ar > 0.10: score += 6
        elif ar > 0.05: score += 4
        elif ar > 0: score += 2

        # 夏普 (0-10)
        sr = m["sharpe_ratio"]
        if sr > 2.0: score += 10
        elif sr > 1.5: score += 8
        elif sr > 1.0: score += 6
        elif sr > 0.5: score += 4
        elif sr > 0: score += 2

        # 卡玛 (0-8)
        cr = m["calmar_ratio"]
        if cr > 3: score += 8
        elif cr > 2: score += 6
        elif cr > 1: score += 4
        elif cr > 0.5: score += 2

        # 超额Alpha (0-7)
        al = m["excess_alpha"]
        if al > 0.15: score += 7
        elif al > 0.10: score += 5
        elif al > 0.05: score += 3
        elif al > 0: score += 1

        return min(score, 35)

    def _score_risk(self) -> int:
        """风险控制 满分25"""
        score = 0
        m = self.metrics

        # 最大回撤 (0-8)
        dd = abs(m["max_drawdown"])
        if dd < 0.10: score += 8
        elif dd < 0.15: score += 6
        elif dd < 0.20: score += 4
        elif dd < 0.30: score += 2

        # 波动率 (0-6)
        vol = m["volatility"]
        if vol < 0.15: score += 6
        elif vol < 0.20: score += 4
        elif vol < 0.25: score += 2

        # 最长回撤恢复期 (0-6)
        days = m["max_dd_days"]
        if days < 30: score += 6
        elif days < 60: score += 4
        elif days < 90: score += 2

        # 尾部风险 VaR99 (0-5)
        var99 = abs(m["var_99"])
        if var99 < 0.03: score += 5
        elif var99 < 0.05: score += 3
        elif var99 < 0.07: score += 1

        return min(score, 25)

    def _score_stability(self) -> int:
        """稳定性 满分20"""
        score = 0
        m = self.metrics

        # 胜率 (0-7)
        wr = m["win_rate"]
        if wr > 0.65: score += 7
        elif wr > 0.55: score += 5
        elif wr > 0.45: score += 3

        # 盈亏比 (0-7)
        pf = m["profit_factor"]
        if pf > 2.0: score += 7
        elif pf > 1.5: score += 5
        elif pf > 1.0: score += 3

        # 月度正收益占比 (0-6)
        mwp = m["monthly_win_pct"]
        if mwp > 0.70: score += 6
        elif mwp > 0.60: score += 4
        elif mwp > 0.50: score += 2

        return min(score, 20)

    def _score_generalization(self) -> int:
        """泛化能力 满分20（需WFA数据）"""
        score = 0
        m = self.metrics

        oos_pass = m.get("wfa_oos_pass_rate")
        oos_ratio = m.get("wfa_oos_is_ratio")

        if oos_pass is None or oos_ratio is None:
            return min(score, 5)

        # OOS通过率 (0-10)
        if oos_pass >= 1.0: score += 10
        elif oos_pass >= 0.8: score += 8
        elif oos_pass >= 0.6: score += 5
        elif oos_pass >= 0.4: score += 2

        # OOS/IS收益比 (0-10)
        if oos_ratio >= 0.80: score += 10
        elif oos_ratio >= 0.60: score += 7
        elif oos_ratio >= 0.40: score += 4

        return min(score, 20)

    # ------------------------------------------------------------------
    # Grade
    # ------------------------------------------------------------------

    @staticmethod
    def _grade(total: int) -> str:
        if total >= 85: return "A"
        if total >= 70: return "B"
        if total >= 55: return "C"
        if total >= 40: return "D"
        return "F"

    # ------------------------------------------------------------------
    # AI Summary
    # ------------------------------------------------------------------

    def _generate_summary(
        self, total: int, earnings: int, risk: int, stability: int, generalization: int
    ) -> str:
        """生成大白话策略诊断摘要"""
        grade = self._grade(total)

        parts = []
        if earnings >= 25:
            parts.append("收益质量不错")
        elif earnings >= 15:
            parts.append("收益尚可")
        else:
            parts.append("收益偏弱")

        if risk >= 18:
            parts.append("风控做得很好")
        elif risk >= 12:
            parts.append("风险控制在可接受范围")
        else:
            parts.append("风险控制有明显短板")

        if generalization >= 15:
            parts.append("WFA显示策略泛化能力强，不容易过拟合")
        elif generalization >= 8:
            parts.append("WFA表现一般，部分窗口出现过拟合迹象")
        else:
            parts.append("策略可能过拟合了，建议简化条件或扩大训练集")

        if grade == "A":
            summary = f"优秀的策略。{'，'.join(parts)}。可以考虑实盘。"
        elif grade == "B":
            summary = f"还不错的策略，{'，'.join(parts)}。建议继续优化参数。"
        elif grade == "C":
            summary = f"有明显缺陷。{'，'.join(parts)}。需要重新审视策略逻辑。"
        elif grade == "D":
            summary = f"风险较高。{'，'.join(parts)}。不建议直接使用。"
        else:
            summary = f"存在严重问题。{'，'.join(parts)}。建议放弃此策略。"

        return summary
