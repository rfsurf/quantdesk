"""AI 路由 — 策略生成/诊断/用户设置/套餐升级"""

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import (
    AIGenerateRequest, AIGenerateResponse,
    AIDiagnoseRequest, AIDiagnoseResponse,
    UserAISettingsRequest, UserAISettingsResponse,
    UpgradePlanRequest,
)
from ..dependencies import (
    get_current_user_id, find_user_by_id, get_ai_config,
    _strategies, find_latest_backtest, summarize_config_plain,
)
from ..scorecard import StrategyScorecard

router = APIRouter(prefix="/api", tags=["AI"])


@router.post("/ai/generate-strategy", response_model=AIGenerateResponse)
async def ai_generate_strategy(
    body: AIGenerateRequest,
    user_id: str = Depends(get_current_user_id),
):
    import uuid
    user = find_user_by_id(user_id)
    key, base, used, limit = get_ai_config(user)

    if user and user["plan"] == "pro" and not key and limit > 0 and used >= limit:
        raise HTTPException(402, "本月 AI 调用次数已用完，请等下月或升级套餐")

    try:
        from ..ai_client import generate_strategy_config
        config = await generate_strategy_config(body.prompt, user_api_key=key, user_api_base=base)

        if user and not key:
            user["ai_calls_count"] = used + 1

        return AIGenerateResponse(
            session_id=uuid.uuid4(),
            config=config,
            summary=summarize_config_plain(config, body.prompt),
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"AI 服务调用失败: {str(e)}")


@router.post("/ai/diagnose-strategy/{sid}", response_model=AIDiagnoseResponse)
async def ai_diagnose(
    sid: str,
    body: AIDiagnoseRequest,
    user_id: str = Depends(get_current_user_id),
):
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise HTTPException(404)

    user = find_user_by_id(user_id)
    key, base, used, limit = get_ai_config(user)

    if user and user["plan"] == "pro" and not key and limit > 0 and used >= limit:
        raise HTTPException(402, "本月 AI 调用次数已用完")

    bt = find_latest_backtest(sid)
    if bt and bt.get("result"):
        metrics = bt["result"]
    else:
        metrics = {
            "annual_return": 0.15, "sharpe_ratio": 1.5, "calmar_ratio": 2.0,
            "excess_alpha": 0.08, "max_drawdown": 0.15, "volatility": 0.18,
            "max_dd_days": 45, "var_99": 0.04, "win_rate": 0.55,
            "profit_factor": 1.5, "monthly_win_pct": 0.60,
            "wfa_oos_pass_rate": 0.8, "wfa_oos_is_ratio": 0.7,
        }

    try:
        from ..ai_client import diagnose_strategy
        diagnosis = await diagnose_strategy(s["config"], metrics, user_api_key=key, user_api_base=base)

        if user and not key:
            user["ai_calls_count"] = used + 1
    except Exception:
        from ..ai_client import _fallback_diagnose
        diagnosis = _fallback_diagnose(metrics)

    scorecard = StrategyScorecard(metrics).compute()

    return AIDiagnoseResponse(
        scorecard={**scorecard, "ai_summary": diagnosis.get("summary", "")},
        suggestions=diagnosis.get("suggestions", []),
    )


# ---------------------------------------------------------------------------
# User Settings
# ---------------------------------------------------------------------------

@router.get("/user/ai-settings", response_model=UserAISettingsResponse)
async def get_ai_settings(user_id: str = Depends(get_current_user_id)):
    user = find_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    key, base, used, limit = get_ai_config(user)
    return UserAISettingsResponse(
        plan=user["plan"],
        ai_enabled=limit != 0,
        ai_calls_used=used,
        ai_calls_limit=limit,
        ai_provider=user.get("ai_provider"),
        has_api_key=bool(user.get("ai_api_key")),
    )


@router.put("/user/ai-settings")
async def update_ai_settings(
    body: UserAISettingsRequest,
    user_id: str = Depends(get_current_user_id),
):
    user = find_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if "ai_api_key" in body.model_fields_set:
        user["ai_api_key"] = body.ai_api_key
    if "ai_provider" in body.model_fields_set:
        user["ai_provider"] = body.ai_provider
    key, base, used, limit = get_ai_config(user)
    return UserAISettingsResponse(
        plan=user["plan"],
        ai_enabled=limit != 0,
        ai_calls_used=used,
        ai_calls_limit=limit,
        ai_provider=user.get("ai_provider"),
        has_api_key=bool(user.get("ai_api_key")),
    )


@router.post("/user/upgrade")
async def upgrade_plan(
    body: UpgradePlanRequest,
    user_id: str = Depends(get_current_user_id),
):
    user = find_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if body.plan not in ("free", "pro"):
        raise HTTPException(400, "无效套餐，可选: free / pro")
    user["plan"] = body.plan
    user["ai_calls_count"] = 0
    return {"plan": body.plan, "message": f"已切换至 {body.plan.upper()} 套餐"}
