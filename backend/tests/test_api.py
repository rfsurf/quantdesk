"""
QuantDesk API 集成测试 — 使用 FastAPI TestClient
从项目根目录运行: .venv/bin/python -m pytest backend/tests/test_api.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.app import app
from backend.dependencies import JWT_SECRET, JWT_ALGORITHM, hash_password

client = TestClient(app)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前清空内存存储"""
    import backend.dependencies as mod
    mod._users.clear()
    mod._refresh_tokens.clear()
    mod._verification_codes.clear()
    mod._strategies.clear()
    mod._backtests.clear()
    mod._wfa_tasks.clear()
    mod._agent_tokens.clear()
    mod._agent_audit.clear()


def _create_user(email="test@example.com", password="Test12345678", plan="free"):
    """直接在内存中创建用户并返回 (email, password, token)"""
    import backend.dependencies as mod
    user_id = str(uuid.uuid4())
    mod._users[email] = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "plan": plan,
        "ai_api_key": None,
        "ai_provider": None,
        "ai_calls_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # 签发 token
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user_id, "plan": plan, "exp": now + timedelta(days=7), "iat": now},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    mod._refresh_tokens[str(uuid.uuid4())] = {
        "user_id": user_id,
        "expires": now + timedelta(days=30),
    }
    return email, password, token


def _auth(email="test@example.com", password="Test12345678"):
    """返回 Authorization header"""
    _, _, token = _create_user(email, password)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Health
# ===========================================================================

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_redirects():
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)


# ===========================================================================
# Auth — send code & register (真实 API)
# ===========================================================================

def test_send_code():
    r = client.post("/api/auth/send-code", json={"email": "new@test.com"})
    assert r.status_code == 204


def test_register_and_login():
    client.post("/api/auth/send-code", json={"email": "reg@test.com"})
    r = client.post("/api/auth/register", json={
        "email": "reg@test.com", "password": "Abc12345", "code": "000000",
    })
    assert r.status_code == 201

    r2 = client.post("/api/auth/login", json={
        "email": "reg@test.com", "password": "Abc12345",
    })
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_register_duplicate():
    client.post("/api/auth/send-code", json={"email": "dup@test.com"})
    client.post("/api/auth/register", json={
        "email": "dup@test.com", "password": "Abc12345", "code": "000000",
    })
    r = client.post("/api/auth/register", json={
        "email": "dup@test.com", "password": "Abc12345", "code": "000000",
    })
    assert r.status_code == 400


def test_register_wrong_code():
    client.post("/api/auth/send-code", json={"email": "wrong@test.com"})
    r = client.post("/api/auth/register", json={
        "email": "wrong@test.com", "password": "Abc12345", "code": "999999",
    })
    assert r.status_code == 400


def test_login_wrong_password():
    client.post("/api/auth/send-code", json={"email": "wp@test.com"})
    client.post("/api/auth/register", json={
        "email": "wp@test.com", "password": "Abc12345", "code": "000000",
    })
    r = client.post("/api/auth/login", json={
        "email": "wp@test.com", "password": "WrongPass1",
    })
    assert r.status_code == 401


def test_login_nonexistent():
    r = client.post("/api/auth/login", json={
        "email": "nobody@test.com", "password": "Abc12345",
    })
    assert r.status_code == 401


def test_refresh_token():
    # 直接创建用户避免 rate limit
    _, _, _ = _create_user("rt@test.com", "Abc12345")
    r = client.post("/api/auth/login", json={
        "email": "rt@test.com", "password": "Abc12345",
    })
    refresh = r.json()["refresh_token"]
    r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_refresh_invalid_token():
    r = client.post("/api/auth/refresh", json={"refresh_token": "invalid-refresh"})
    assert r.status_code == 401


# ===========================================================================
# Strategies — CRUD
# ===========================================================================

def test_create_strategy():
    r = client.post("/api/strategies", json={
        "name": "测试策略",
        "config": {"universe": {"type": "index", "value": "000300"},
                   "conditions": {"logic": "AND", "children": []}},
    }, headers=_auth())
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "测试策略"


def test_list_strategies():
    h = _auth()
    for i in range(2):
        client.post("/api/strategies", json={
            "name": f"策略{i}", "config": {"universe": {"type": "index", "value": "000300"},
                        "conditions": {"logic": "AND", "children": []}},
        }, headers=h)
    r = client.get("/api/strategies", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_get_strategy():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "获取测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.get(f"/api/strategies/{sid}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["name"] == "获取测试"


def test_update_strategy():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "原始名称", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.put(f"/api/strategies/{sid}", json={"name": "新名称"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["name"] == "新名称"


def test_delete_strategy():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "待删除", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.delete(f"/api/strategies/{sid}", headers=h)
    assert r2.status_code == 204
    r3 = client.get(f"/api/strategies/{sid}", headers=h)
    assert r3.status_code == 404


def test_cannot_access_others_strategy():
    hA = _auth("a@test.com")
    r = client.post("/api/strategies", json={
        "name": "A的策略", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=hA)
    sid = r.json()["id"]
    hB = _auth("b@test.com")
    r2 = client.get(f"/api/strategies/{sid}", headers=hB)
    assert r2.status_code == 404


def test_strategy_versions():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "版本测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    client.put(f"/api/strategies/{sid}", json={
        "config": {"universe": {"type": "index", "value": "000905"},
                   "conditions": {"logic": "OR", "children": []}},
    }, headers=h)
    r2 = client.get(f"/api/strategies/{sid}/versions", headers=h)
    assert r2.status_code == 200
    assert len(r2.json()) >= 1


def test_strategies_requires_auth():
    r = client.get("/api/strategies")
    assert r.status_code in (401, 403)


# ===========================================================================
# AI — generate (fallback / template mode for Free plan)
# ===========================================================================

def test_ai_generate_fallback():
    h = _auth()
    r = client.post("/api/ai/generate-strategy", json={
        "prompt": "帮我做一个震荡市低吸高抛策略",
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "config" in data
    assert "summary" in data


def test_ai_generate_trend_template():
    h = _auth()
    r = client.post("/api/ai/generate-strategy", json={
        "prompt": "做一个趋势跟踪策略",
    }, headers=h)
    assert r.status_code == 200
    children = r.json()["config"]["conditions"]["children"]
    assert any(c.get("op") == "cross_above" for c in children)


# ===========================================================================
# AI — diagnose
# ===========================================================================

def test_ai_diagnose():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "诊断测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.post(f"/api/ai/diagnose-strategy/{sid}", json={
        "strategy_id": sid,
    }, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert "scorecard" in data
    assert "suggestions" in data


# ===========================================================================
# User — AI settings
# ===========================================================================

def test_get_ai_settings():
    h = _auth()
    r = client.get("/api/user/ai-settings", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["plan"] == "free"
    assert data["ai_enabled"] is False


def test_update_ai_settings_byok():
    h = _auth()
    r = client.put("/api/user/ai-settings", json={
        "ai_api_key": "sk-test-key-123", "ai_provider": "deepseek",
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["has_api_key"] is True
    assert data["ai_provider"] == "deepseek"


def test_update_ai_settings_clear():
    h = _auth()
    client.put("/api/user/ai-settings", json={
        "ai_api_key": "sk-test", "ai_provider": "deepseek",
    }, headers=h)
    r = client.put("/api/user/ai-settings", json={
        "ai_api_key": None, "ai_provider": None,
    }, headers=h)
    assert r.json()["has_api_key"] is False


def test_upgrade_to_pro():
    h = _auth()
    r = client.post("/api/user/upgrade", json={"plan": "pro"}, headers=h)
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"
    r2 = client.get("/api/user/ai-settings", headers=h)
    assert r2.json()["plan"] == "pro"
    assert r2.json()["ai_enabled"] is True


def test_upgrade_invalid_plan():
    h = _auth()
    r = client.post("/api/user/upgrade", json={"plan": "enterprise"}, headers=h)
    assert r.status_code == 400


# ===========================================================================
# Backtest — user history
# ===========================================================================

def test_list_user_backtests():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "回测历史测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    client.post(f"/api/strategies/{sid}/backtest", json={
        "initial_cash": 100000, "start_date": "2025-01-01", "end_date": "2025-06-01",
    }, headers=h)
    r2 = client.get("/api/backtests", headers=h)
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert len(items) >= 1
    assert items[0]["strategy_name"] == "回测历史测试"


def test_backtests_isolation():
    hA = _auth("a2@test.com")
    r = client.post("/api/strategies", json={
        "name": "A回测", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=hA)
    sid = r.json()["id"]
    client.post(f"/api/strategies/{sid}/backtest", json={
        "initial_cash": 100000,
    }, headers=hA)
    hB = _auth("b2@test.com")
    r2 = client.get("/api/backtests", headers=hB)
    assert r2.json()["total"] == 0


# ===========================================================================
# Agent Tokens
# ===========================================================================

def test_create_and_list_agent_token():
    h = _auth()
    r = client.post("/api/agent-tokens", json={
        "name": "Claude Code", "scopes": ["R", "B", "W"], "expires_in_days": 90,
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["name"] == "Claude Code"
    r2 = client.get("/api/agent-tokens", headers=h)
    assert len(r2.json()) == 1


def test_revoke_agent_token():
    h = _auth()
    r = client.post("/api/agent-tokens", json={
        "name": "待吊销", "scopes": ["R"], "expires_in_days": 30,
    }, headers=h)
    tid = r.json()["id"]
    r2 = client.delete(f"/api/agent-tokens/{tid}", headers=h)
    assert r2.status_code == 204
    r3 = client.get("/api/agent-tokens", headers=h)
    assert r3.json()[0]["is_revoked"] is True


# ===========================================================================
# Data endpoints
# ===========================================================================

def test_list_symbols():
    r = client.get("/api/data/symbols")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_symbols_with_query():
    r = client.get("/api/data/symbols?q=600")
    assert r.status_code == 200
    assert all("600" in s for s in r.json())


def test_list_factors():
    r = client.get("/api/data/factors")
    assert r.status_code == 200
    assert "technical" in r.json()
    assert len(r.json()["technical"]) > 0


# ===========================================================================
# Admin
# ===========================================================================

def test_admin_stats():
    h = _auth("admin@quantdesk.dev")
    # 注册为第一个用户以获得管理员权限
    r = client.get("/api/admin/stats", headers=h)
    assert r.status_code == 200
    assert r.json()["api_health"] == "ok"


def test_admin_list_users():
    h = _auth("admin2@quantdesk.dev")
    r = client.get("/api/admin/users", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_non_admin_rejected():
    # 先创建一个 admin 用户作为第一个用户
    _create_user("real_admin@test.com")
    # 再创建普通用户，不是第一个也非 admin 邮箱
    h = _auth("normal_user@test.com")
    r = client.get("/api/admin/stats", headers=h)
    assert r.status_code == 403


# ===========================================================================
# QMT Export
# ===========================================================================

def test_qmt_export():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "QMT测试", "config": {"universe": {"type": "symbols", "value": ["000001.SZ"]},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.get(f"/api/strategies/{sid}/export/qmt", headers=h)
    assert r2.status_code == 200
    assert "xtquant" in r2.text


# ===========================================================================
# WFA
# ===========================================================================

def test_wfa_trigger():
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "WFA测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]
    r2 = client.post(f"/api/strategies/{sid}/wfa", json={
        "mode": "standard", "is_window": 500, "oos_window": 120, "step": 120,
    }, headers=h)
    assert r2.status_code == 200
    assert r2.json()["status"] == "done"
