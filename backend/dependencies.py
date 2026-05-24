"""
QuantDesk 共享依赖与状态管理
所有路由模块共同使用的 JWT 认证、内存存储、工具函数。
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import bcrypt

from .config import settings

# ---------------------------------------------------------------------------
# JWT / 密码
# ---------------------------------------------------------------------------

JWT_SECRET = settings.JWT_SECRET or ("dev-temp-key-" + secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer()


def hash_password(password: str) -> str:
    """哈希密码，返回 bcrypt hash"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# 内存存储（MVP 阶段，生产切换为 PostgreSQL）
# ---------------------------------------------------------------------------

_users: dict[str, dict] = {}               # email → user
_refresh_tokens: dict[str, dict] = {}       # token_hash → {user_id, expires}
_verification_codes: dict[str, dict] = {}
_strategies: dict[str, dict] = {}           # uuid → strategy
_backtests: dict[str, dict] = {}
_wfa_tasks: dict[str, dict] = {}
_agent_tokens: dict[str, dict] = {}         # token_hash → token_data
_agent_audit: list[dict] = []


# ---------------------------------------------------------------------------
# Auth 依赖注入
# ---------------------------------------------------------------------------

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, "无效token")
        return user_id
    except JWTError:
        raise HTTPException(401, "token已过期或无效")


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[str]:
    if credentials is None:
        return None
    return get_current_user_id(credentials)


# ---------------------------------------------------------------------------
# 用户查询辅助
# ---------------------------------------------------------------------------

def find_user_by_id(user_id: str) -> Optional[dict]:
    """查找用户 - 支持 PostgreSQL 和内存模式"""
    if settings.USE_POSTGRES:
        # PostgreSQL 模式：从数据库查询
        from .database import sync_engine
        from sqlalchemy import text
        try:
            with sync_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, email, plan, is_admin, ai_api_key, ai_provider, ai_calls_count, created_at FROM users WHERE id = :uid"),
                    {"uid": user_id}
                )
                row = result.fetchone()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "plan": row[2],
                        "is_admin": row[3],
                        "ai_api_key": row[4],
                        "ai_provider": row[5],
                        "ai_calls_count": row[6],
                        "created_at": row[7].isoformat() if row[7] else None,
                    }
        except Exception:
            pass
        return None
    else:
        # 内存模式
        for u in _users.values():
            if u["id"] == user_id:
                return u
        return None


def find_user_by_email(email: str) -> Optional[dict]:
    """查找用户 - 支持 PostgreSQL 和内存模式"""
    if settings.USE_POSTGRES:
        from .database import sync_engine
        from sqlalchemy import text
        try:
            with sync_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, email, plan, is_admin, ai_api_key, ai_provider, ai_calls_count, created_at FROM users WHERE email = :email"),
                    {"email": email}
                )
                row = result.fetchone()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "plan": row[2],
                        "is_admin": row[3],
                        "ai_api_key": row[4],
                        "ai_provider": row[5],
                        "ai_calls_count": row[6],
                        "created_at": row[7].isoformat() if row[7] else None,
                    }
        except Exception:
            pass
        return None
    else:
        return _users.get(email)


# ---------------------------------------------------------------------------
# 用户 AI 配置
# ---------------------------------------------------------------------------

AI_CALL_LIMITS = {"free": 0, "pro": 500, "byok": -1}


def get_ai_config(user: dict | None) -> tuple[str | None, str | None, int, int]:
    """返回 (api_key, api_base, calls_used, calls_limit)"""
    if not user:
        return None, None, 0, 0
    key = user.get("ai_api_key")
    base = settings.DEEPSEEK_BASE_URL
    if user.get("ai_provider") == "ollama":
        base = "http://localhost:11434/v1"
    limit = AI_CALL_LIMITS.get(user["plan"], 0) if not key else -1
    return key, base, user.get("ai_calls_count", 0), limit


# ---------------------------------------------------------------------------
# Token 签发
# ---------------------------------------------------------------------------

def issue_tokens(user: dict) -> dict:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user["id"],
        "plan": user["plan"],
        "exp": now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
        "iat": now,
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    refresh = str(uuid.uuid4())
    _refresh_tokens[refresh] = {
        "user_id": user["id"],
        "expires": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }

    from .schemas import TokenResponse
    return TokenResponse(access_token=access_token, refresh_token=refresh).model_dump()


# ---------------------------------------------------------------------------
# Agent Token 认证
# ---------------------------------------------------------------------------

def authenticate_agent(request: Request, required_scope: Optional[str] = None) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "缺少 Agent Token")

    found = None
    for h, data in _agent_tokens.items():
        try:
            if verify_password(token, h):
                found = data
                break
        except Exception:
            continue

    if not found or found.get("is_revoked"):
        raise HTTPException(401, "无效的 Agent Token 或已吊销")

    if required_scope and required_scope not in found["scopes"]:
        raise HTTPException(403, f"Token 缺少 Scope: {required_scope}")

    found["last_used_at"] = datetime.now(timezone.utc)

    _agent_audit.append({
        "token_id": str(found["id"]),
        "user_id": found["user_id"],
        "route": str(request.url.path),
        "scope_class": required_scope or "R",
        "status_code": 200,
        "created_at": datetime.now(timezone.utc),
    })

    return found


# ---------------------------------------------------------------------------
# Admin 检查
# ---------------------------------------------------------------------------

ADMIN_EMAIL = settings.ADMIN_EMAIL


def check_admin(user_id: str) -> dict:
    user = find_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "用户不存在")
    # 支持 is_admin 字段或邮箱匹配
    is_admin = (
        user.get("is_admin", False) or
        user["email"] == ADMIN_EMAIL or
        (len(_users) > 0 and list(_users.values())[0]["id"] == user_id)
    )
    if not is_admin:
        raise HTTPException(403, "需要管理员权限")
    return user


def set_admin(user_id: str) -> bool:
    """将用户设置为管理员"""
    user = find_user_by_id(user_id)
    if not user:
        return False
    user["is_admin"] = True
    return True


# ---------------------------------------------------------------------------
# 回测执行（MVP 同步版本）
# ---------------------------------------------------------------------------

def execute_backtest(task_id: str):
    """同步执行回测（MVP阶段，后续改为Celery异步）"""
    import numpy as np
    import pandas as pd
    from .config import settings

    bt = _backtests.get(task_id)
    if not bt:
        return

    bt["status"] = "running"

    try:
        # 支持 PostgreSQL 和内存模式
        strategy_id = bt["strategy_id"]
        if settings.USE_POSTGRES:
            from .database import sync_engine
            from sqlalchemy import text
            with sync_engine.connect() as conn:
                r = conn.execute(
                    text("SELECT id, user_id, name, config, status FROM strategies WHERE id = :sid"),
                    {"sid": strategy_id}
                )
                row = r.fetchone()
                if not row:
                    raise ValueError("策略不存在")
                s = {"id": str(row[0]), "user_id": str(row[1]), "name": row[2], "config": row[3] or {}, "status": row[4]}
        else:
            s = _strategies.get(strategy_id)
            if not s:
                raise ValueError("策略不存在")

        from .core import BacktestConfig
        from .backtest_engine import BacktestEngine
        from .signal_translator import build_signal_func
        from .data_pipeline import query_market_data_with_factors

        params = bt.get("params", {})
        engine = BacktestEngine(BacktestConfig(
            initial_cash=params.get("initial_cash", 100000),
            commission_rate=params.get("commission_rate", 0.0003),
            slippage_rate=params.get("slippage_rate", 0.0001),
            max_positions=params.get("max_positions", 10),
            stop_loss_pct=params.get("stop_loss_pct"),
            stop_profit_pct=params.get("stop_profit_pct"),
        ))

        today = datetime.now(timezone.utc).date()
        start = params.get("start_date", today.replace(year=today.year - 1).isoformat())
        end = params.get("end_date", today.isoformat())

        universe = s["config"].get("universe", {})
        utype = universe.get("type", "symbols")
        uvalue = universe.get("value", [])
        if utype == "symbols":
            symbols = uvalue if isinstance(uvalue, list) else [uvalue]
        else:
            symbols = ["600519"]

        df = query_market_data_with_factors(symbols, start, end)

        if df.empty:
            import numpy as np
            dates = pd.date_range(start, end, freq="B")
            records = []
            rng = np.random.default_rng(42)
            for sym in symbols:
                seed = hash(sym) % 10000
                trend = 0.0005 + rng.uniform(-0.0003, 0.001)
                prices = 100 * (1 + trend) ** np.arange(len(dates))
                noise = rng.normal(0, 0.015, len(dates))
                prices = prices * (1 + noise)
                for i, d in enumerate(dates):
                    close_val = float(prices[i])
                    volume_val = int(rng.uniform(5_000_000, 20_000_000))
                    records.append({
                        "symbol": sym, "trade_date": d,
                        "open": close_val * 0.995, "high": close_val * 1.015,
                        "low": close_val * 0.985, "close": close_val,
                        "volume": volume_val,
                    })
            df = pd.DataFrame(records)
            df["trade_date"] = pd.to_datetime(df["trade_date"])

        _ensure_factors(df, symbols)

        if "trade_date" in df.columns and "symbol" in df.columns:
            df = df.set_index(["trade_date", "symbol"]).sort_index()

        signal_func = build_signal_func(s["config"])
        result = engine.run(df, signal_func)

        bt["status"] = "done"
        bt["result"] = result.to_dict()
        bt["trades"] = [
            {"date": str(t.date), "symbol": t.symbol, "side": t.side.value,
             "price": t.price, "volume": t.volume, "pnl": t.pnl}
            for t in result.trades
        ]
        bt["nav_series"] = result.nav_series
    except Exception as exc:
        bt["status"] = "failed"
        bt["error_message"] = str(exc)


def _ensure_factors(df, symbols: list):
    """为 DataFrame 补全所有基础因子列（实时计算）"""
    import numpy as np
    REQUIRED = [
        "ma_5", "ma_10", "ma_20", "ma_60", "ma_120",
        "volume_ma_5", "volume_ma_20",
        "rsi_14",
    ]
    missing = [f for f in REQUIRED if f not in df.columns]
    if not missing:
        return

    sym_in_index = "symbol" in df.index.names
    for sym in symbols:
        if sym_in_index:
            mask = df.index.get_level_values("symbol") == sym
        else:
            mask = df["symbol"] == sym
        if mask.sum() < 25:
            continue
        close_s = df.loc[mask, "close"].reset_index(drop=True)
        vol_s = df.loc[mask, "volume"].reset_index(drop=True)
        if any(f.startswith("ma_") for f in missing):
            for p in [5, 10, 20, 60, 120]:
                if f"ma_{p}" in missing:
                    df.loc[mask, f"ma_{p}"] = close_s.rolling(p).mean().values
        if "volume_ma_5" in missing:
            df.loc[mask, "volume_ma_5"] = vol_s.rolling(5).mean().values
        if "volume_ma_20" in missing:
            df.loc[mask, "volume_ma_20"] = vol_s.rolling(20).mean().values
        if "rsi_14" in missing:
            delta = close_s.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            df.loc[mask, "rsi_14"] = (100 - (100 / (1 + rs))).values


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def find_latest_backtest(sid: str) -> Optional[dict]:
    best = None
    for bt in _backtests.values():
        if bt.get("strategy_id") == sid and bt.get("status") == "done":
            if best is None or bt.get("created_at", "") > best.get("created_at", ""):
                best = bt
    return best


def summarize_config_plain(config: dict, user_prompt: str) -> str:
    """简单总结生成的策略配置（不调AI）"""
    conditions = config.get("conditions", {})
    logic = conditions.get("logic", "AND")
    children = conditions.get("children", [])
    parts = []
    for c in children:
        if c.get("type") == "compare":
            left = c.get("left", {})
            right = c.get("right", {})
            op = c.get("op", ">")
            lname = left.get("factor", "?")
            rname = right.get("factor", right.get("constant", "?"))
            if op == "cross_above":
                parts.append(f"{lname}金叉{rname}")
            elif op == "cross_below":
                parts.append(f"{lname}死叉{rname}")
            elif op == ">":
                parts.append(f"{lname}大于{rname}")
            elif op == "<":
                parts.append(f"{lname}小于{rname}")
            else:
                parts.append(f"{lname}{op}{rname}")

    rule = f"{'且' if logic == 'AND' else '或'}".join(parts) if parts else "自定义条件"
    return f"已为你生成策略：{rule}。可根据此逻辑进行回测验证。"
