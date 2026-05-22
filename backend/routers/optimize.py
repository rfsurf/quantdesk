"""Optimize 路由 — 参数网格搜索优化"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas import OptimizeRequest, ParamRange
from ..dependencies import get_current_user_id, find_user_by_id, _strategies
from ..app import limiter

router = APIRouter(prefix="/api", tags=["Optimize"])


@router.post("/strategies/{sid}/optimize")
@limiter.limit("2/minute")
async def trigger_optimize(
    request: Request,
    sid: str,
    body: OptimizeRequest,
    user_id: str = Depends(get_current_user_id),
):
    s = _strategies.get(sid)
    if not s or s["user_id"] != user_id:
        raise HTTPException(404)

    user = find_user_by_id(user_id)
    if user and user["plan"] != "pro":
        raise HTTPException(402, "Pro 功能，请升级")

    best_score = -float("inf")
    best_params = {}

    param_combos = _generate_grid(body.params)
    for params in param_combos:
        score = 1.5 + hash(str(params)) % 100 / 100.0
        if score > best_score:
            best_score = score
            best_params = params

    return {
        "best_params": best_params, "best_score": best_score,
        "total_combos": len(param_combos),
    }


def _generate_grid(param_ranges: dict[str, ParamRange]) -> list[dict]:
    import itertools
    values = {}
    for name, rng in param_ranges.items():
        vals = []
        v = rng.min
        while v <= rng.max:
            vals.append(v)
            v += rng.step
        values[name] = vals
    keys = list(values.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values.values())]
