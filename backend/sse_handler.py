"""
QuantDesk SSE 实时进度推送
用于回测 / WFA / 参数优化 / AI生成 的长任务实时反馈
"""

import json
from datetime import datetime, timezone


class SSEMessage:
    """SSE 消息构造器"""

    @staticmethod
    def _format(event: str, data: dict) -> str:
        payload = json.dumps(data, ensure_ascii=False)
        return f"event: {event}\ndata: {payload}\n\n"

    @classmethod
    def snapshot(cls, status: str, estimated_duration_s: int, total_steps: int) -> str:
        return cls._format("snapshot", {
            "status": status,
            "estimated_duration_s": estimated_duration_s,
            "total_steps": total_steps,
        })

    @classmethod
    def progress(cls, step: int, total: int, message: str, pct: int, elapsed_s: float = 0) -> str:
        return cls._format("progress", {
            "step": step, "total": total,
            "message": message, "pct": pct,
            "elapsed_s": round(elapsed_s, 1),
            "estimated_remaining_s": round(elapsed_s / pct * (100 - pct), 1) if pct > 0 else 0,
        })

    @classmethod
    def backtest_step(cls, step_name: str, detail: str, pct: int) -> str:
        """回测特定步骤进度"""
        steps = {
            "loading_data": "加载行情数据",
            "computing_factors": "计算因子",
            "generating_signals": "生成交易信号",
            "simulating_trades": "模拟交易执行",
            "calculating_metrics": "计算绩效指标",
            "saving_results": "保存结果",
        }
        return cls._format("backtest_step", {
            "step_name": step_name,
            "step_label": steps.get(step_name, step_name),
            "detail": detail,
            "pct": pct,
        })

    @classmethod
    def result(cls, backtest_id: str, sharpe: float, total_return: float, metrics: dict = None) -> str:
        data = {
            "status": "done",
            "backtest_id": backtest_id,
            "sharpe": sharpe,
            "total_return": total_return,
        }
        if metrics:
            data["metrics"] = metrics
        return cls._format("result", data)

    @classmethod
    def error(cls, code: str, message: str, recoverable: bool = False) -> str:
        return cls._format("error", {
            "status": "failed",
            "code": code,
            "message": message,
            "recoverable": recoverable,
        })

    @classmethod
    def heartbeat(cls, ts: str = None) -> str:
        return cls._format("heartbeat", {
            "ts": ts or datetime.now(timezone.utc).isoformat(),
        })

    @classmethod
    def done(cls) -> str:
        """结束信号"""
        return cls._format("done", {})

    @classmethod
    def cancelled(cls) -> str:
        """取消信号"""
        return cls._format("cancelled", {"status": "cancelled"})


class SSEHeartbeat:
    """SSE 心跳管理器"""

    def __init__(self, interval: int = 15):
        self.interval = interval

    def generate(self) -> str:
        return SSEMessage.heartbeat()


# 回测步骤进度定义
BACKTEST_STEPS = [
    ("loading_data", 15, "正在加载行情数据..."),
    ("computing_factors", 25, "正在计算因子指标..."),
    ("generating_signals", 40, "正在生成交易信号..."),
    ("simulating_trades", 60, "正在模拟交易执行..."),
    ("calculating_metrics", 85, "正在计算绩效指标..."),
    ("saving_results", 100, "正在保存结果..."),
]
