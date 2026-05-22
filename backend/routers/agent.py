"""Agent 路由 — Agent Token 管理 + Agent Gateway (MCP 协议)"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas import (
    AgentTokenCreate, AgentTokenReveal, AgentTokenListItem,
)
from ..dependencies import (
    get_current_user_id, authenticate_agent,
    hash_password, _agent_tokens, _strategies, _backtests, find_latest_backtest,
    find_user_by_id, get_ai_config,
)
from ..ai_validator import sanitize_ai_output
from ..core import StrategyStage
from ..scorecard import StrategyScorecard

router = APIRouter(tags=["Agent"])


# ===========================================================================
# Agent Token 管理
# ===========================================================================

@router.get("/api/agent-tokens")
async def list_agent_tokens(user_id: str = Depends(get_current_user_id)):
    mine = [t for t in _agent_tokens.values() if t["user_id"] == user_id]
    return [
        AgentTokenListItem(
            id=t["id"], name=t["name"], scopes=t["scopes"],
            is_revoked=t.get("is_revoked", False),
            last_used_at=t.get("last_used_at"),
            created_at=t["created_at"],
        )
        for t in mine
    ]


@router.post("/api/agent-tokens", response_model=AgentTokenReveal)
async def create_agent_token(body: AgentTokenCreate, user_id: str = Depends(get_current_user_id)):
    raw = secrets.token_urlsafe(32)
    token_hash = hash_password(raw)
    if len(raw) > 64:
        raw = raw[:64]

    tid = uuid.uuid4()
    _agent_tokens[token_hash] = {
        "id": tid, "user_id": user_id, "name": body.name,
        "scopes": body.scopes, "is_revoked": False,
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
    }

    return AgentTokenReveal(
        id=tid, name=body.name, token=raw,
        scopes=body.scopes,
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days),
    )


@router.delete("/api/agent-tokens/{tid}", status_code=204)
async def revoke_agent_token(tid: str, user_id: str = Depends(get_current_user_id)):
    for h, t in list(_agent_tokens.items()):
        if str(t["id"]) == tid and t["user_id"] == user_id:
            t["is_revoked"] = True
            return
    raise HTTPException(404)


# ===========================================================================
# Agent Gateway (MCP 协议)
# ===========================================================================

@router.get("/api/agent/v1/whoami")
async def agent_whoami(request: Request):
    token_data = authenticate_agent(request)
    return {"user_id": token_data["user_id"], "scopes": token_data["scopes"]}


@router.get("/api/agent/v1/factors")
async def agent_factors(request: Request):
    authenticate_agent(request, required_scope="R")
    from ..factors import FACTOR_NAMES
    return {"factors": [{"name": f, "category": "technical"} for f in FACTOR_NAMES]}


@router.get("/api/agent/v1/symbols")
async def agent_symbols(request: Request, q: str = ""):
    authenticate_agent(request, required_scope="R")
    sample = ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH", "000858.SZ"]
    if q:
        sample = [s for s in sample if q in s]
    return sample


@router.get("/api/agent/v1/klines/{symbol}")
async def agent_klines(request: Request, symbol: str):
    authenticate_agent(request, required_scope="R")
    import pandas as pd
    import numpy as np
    today = datetime.now(timezone.utc).date()
    year_ago = today.replace(year=today.year - 1)
    dates = pd.date_range(year_ago, today, freq="B")
    prices = 100 * (1.0005) ** np.arange(len(dates))
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": p * 0.99, "high": p * 1.01,
         "low": p * 0.98, "close": p, "volume": 10_000_000}
        for d, p in zip(dates, prices)
    ]


@router.get("/api/agent/v1/strategies")
async def agent_list_strategies(request: Request):
    token_data = authenticate_agent(request, required_scope="R")
    mine = [s for s in _strategies.values() if s["user_id"] == token_data["user_id"]]
    return [{"id": s["id"], "name": s["name"], "status": s["status"]} for s in mine]


@router.post("/api/agent/v1/strategies")
async def agent_create_strategy(request: Request):
    token_data = authenticate_agent(request, required_scope="W")
    body = await request.json()
    config = body.get("config", {})
    cleaned = sanitize_ai_output({"name": "Agent创建", "config": config})
    s = {
        "id": str(uuid.uuid4()), "user_id": token_data["user_id"],
        "name": cleaned["name"], "status": "draft",
        "stage": StrategyStage.DRAFT.value, "config": cleaned["config"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "versions": [],
    }
    _strategies[s["id"]] = s
    return s


@router.post("/api/agent/v1/strategies/{sid}/backtest")
async def agent_backtest(request: Request, sid: str):
    token_data = authenticate_agent(request, required_scope="B")
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        for bt in _backtests.values():
            if bt.get("idempotency_key") == idempotency_key:
                return {"backtest_id": bt["id"], "status": "duplicate"}

    s = _strategies.get(sid)
    if not s or s["user_id"] != token_data["user_id"]:
        raise HTTPException(404)

    task_id = str(uuid.uuid4())
    _backtests[task_id] = {
        "id": task_id, "strategy_id": sid,
        "user_id": token_data["user_id"],
        "status": "pending",
        "idempotency_key": idempotency_key,
        "params": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"backtest_id": task_id, "status": "accepted"}


@router.post("/api/agent/v1/strategies/{sid}/diagnose")
async def agent_diagnose(request: Request, sid: str):
    token_data = authenticate_agent(request, required_scope="B")
    s = _strategies.get(sid)
    if not s or s["user_id"] != token_data["user_id"]:
        raise HTTPException(404)

    bt = find_latest_backtest(sid)
    metrics = bt["result"] if bt and bt.get("result") else {
        "annual_return": 0.12, "sharpe_ratio": 1.2, "calmar_ratio": 1.8,
        "excess_alpha": 0.06, "max_drawdown": 0.18, "volatility": 0.19,
        "max_dd_days": 50, "var_99": 0.05, "win_rate": 0.58,
        "profit_factor": 1.6, "monthly_win_pct": 0.65,
        "wfa_oos_pass_rate": 0.8, "wfa_oos_is_ratio": 0.7,
    }

    try:
        from ..ai_client import diagnose_strategy
        user = find_user_by_id(token_data["user_id"])
        key, base, _, _ = get_ai_config(user)
        diagnosis = await diagnose_strategy(s["config"], metrics, user_api_key=key, user_api_base=base)
    except Exception:
        from ..ai_client import _fallback_diagnose
        diagnosis = _fallback_diagnose(metrics)

    scorecard = StrategyScorecard(metrics).compute()
    return {**scorecard, "diagnosis": diagnosis}
