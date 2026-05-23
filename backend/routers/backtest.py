"""Backtest 路由 — 回测触发/结果查询/SSE/历史"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..schemas import BacktestRequest, BacktestTaskResponse, BacktestResultResponse
from ..dependencies import (
    get_current_user_id, _strategies, _backtests,
    find_latest_backtest,
)
from ..sse_handler import SSEMessage
from ..app import limiter
from ..tasks import run_backtest, celery_app
from ..config import settings

router = APIRouter(prefix="/api", tags=["Backtest"])


def find_strategy_by_id(strategy_id: str, user_id: str) -> dict | None:
    """查找策略 - 支持 PostgreSQL 和内存模式"""
    if settings.USE_POSTGRES:
        from ..database import sync_engine
        from sqlalchemy import text
        try:
            with sync_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, user_id, name, config, status FROM strategies WHERE id = :sid"),
                    {"sid": strategy_id}
                )
                row = result.fetchone()
                if row and str(row[1]) == user_id:
                    return {
                        "id": str(row[0]),
                        "user_id": str(row[1]),
                        "name": row[2],
                        "config": row[3] or {},
                        "status": row[4] or "draft",
                    }
        except Exception:
            pass
        return None
    else:
        s = _strategies.get(strategy_id)
        if s and s["user_id"] == user_id:
            return s
        return None


@router.post("/strategies/{sid}/backtest", response_model=BacktestTaskResponse)
@limiter.limit("3/minute")
async def trigger_backtest(
    request: Request,
    sid: str,
    body: BacktestRequest,
    user_id: str = Depends(get_current_user_id),
):
    s = find_strategy_by_id(sid, user_id)
    if not s:
        raise HTTPException(404, "策略不存在")

    task_id = str(uuid.uuid4())
    _backtests[task_id] = {
        "id": task_id, "strategy_id": sid, "user_id": user_id,
        "status": "pending", "params": body.model_dump(mode="json"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 启动 Celery 异步任务
    celery_task = run_backtest.apply_async(
        args=[sid, task_id, {**s["config"], **body.model_dump(mode="json")}],
        task_id=task_id,
    )
    _backtests[task_id]["celery_task_id"] = celery_task.id
    _backtests[task_id]["status"] = "running"

    return BacktestTaskResponse(task_id=task_id, estimated_duration_s=15)


@router.get("/backtest/{task_id}", response_model=BacktestResultResponse)
async def get_backtest_result(task_id: str, user_id: str = Depends(get_current_user_id)):
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise HTTPException(404)
    return BacktestResultResponse(
        backtest_id=task_id,
        status=bt["status"],
        result=bt.get("result"),
        error_message=bt.get("error_message"),
    )


@router.get("/backtest/{task_id}/trades")
async def get_backtest_trades(task_id: str, user_id: str = Depends(get_current_user_id)):
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise HTTPException(404)
    return bt.get("trades", [])


@router.get("/backtest/{task_id}/nav")
async def get_backtest_nav(task_id: str, user_id: str = Depends(get_current_user_id)):
    bt = _backtests.get(task_id)
    if not bt or bt["user_id"] != user_id:
        raise HTTPException(404)
    nav_series = bt.get("nav_series", [])
    return [
        {"date": str(n.date), "nav": n.nav, "daily_return": n.daily_return,
         "benchmark_nav": n.benchmark_nav}
        for n in nav_series
    ]


@router.get("/backtests")
async def list_user_backtests(user_id: str = Depends(get_current_user_id)):
    mine = [bt for bt in _backtests.values() if bt.get("user_id") == user_id]
    mine.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    result = []
    for bt in mine:
        s = _strategies.get(bt.get("strategy_id", ""), {})
        result.append({
            "id": bt["id"],
            "strategy_id": bt.get("strategy_id"),
            "strategy_name": s.get("name", "未知策略"),
            "status": bt["status"],
            "created_at": bt.get("created_at"),
            "result": bt.get("result"),
            "error_message": bt.get("error_message"),
        })
    return {"items": result, "total": len(result)}


@router.get("/backtest/stream/{task_id}")
async def stream_backtest(task_id: str):
    async def event_stream():
        import asyncio
        start_time = asyncio.get_event_loop().time()
        bt = _backtests.get(task_id, {})

        # 发送初始状态
        yield SSEMessage.snapshot(bt.get("status", "pending"), 15, 6)

        # 模拟进度（实际应从 Celery 任务状态获取）
        for step_name, pct, msg in [
            ("loading_data", 15, "正在加载行情数据..."),
            ("computing_factors", 25, "正在计算因子指标..."),
            ("generating_signals", 40, "正在生成交易信号..."),
            ("simulating_trades", 60, "正在模拟交易执行..."),
            ("calculating_metrics", 85, "正在计算绩效指标..."),
            ("saving_results", 100, "正在保存结果..."),
        ]:
            elapsed = asyncio.get_event_loop().time() - start_time
            yield SSEMessage.backtest_step(step_name, msg, pct)
            yield SSEMessage.progress(pct // 20, 5, msg, pct, elapsed)
            await asyncio.sleep(0.5)

        # 发送结果
        if bt.get("result"):
            r = bt["result"]
            metrics = {
                "max_drawdown": r.get("max_drawdown", 0),
                "win_rate": r.get("win_rate", 0),
                "total_trades": r.get("total_trades", 0),
            }
            yield SSEMessage.result(
                task_id,
                r.get("sharpe_ratio", 0),
                r.get("total_return", 0),
                metrics
            )
        elif bt.get("error_message"):
            yield SSEMessage.error("FAILED", bt["error_message"])
        else:
            yield SSEMessage.result(task_id, 0, 0)

        yield SSEMessage.done()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
