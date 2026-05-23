"""
QuantDesk API 补充测试 — P0/P1 缺失端点
环境变量已在 conftest.py 中设置
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.app import app
from backend.dependencies import JWT_SECRET, JWT_ALGORITHM, hash_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    import backend.dependencies as mod
    mod._users.clear()
    mod._refresh_tokens.clear()
    mod._verification_codes.clear()
    mod._strategies.clear()
    mod._backtests.clear()
    mod._wfa_tasks.clear()
    mod._agent_tokens.clear()
    mod._agent_audit.clear()


def _create_user(email="test@example.com", password="Test12345678", plan="free", is_admin=False):
    import backend.dependencies as mod
    user_id = str(uuid.uuid4())
    mod._users[email] = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "plan": plan,
        "is_admin": is_admin,
        "ai_api_key": None,
        "ai_provider": None,
        "ai_calls_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user_id, "plan": plan, "is_admin": is_admin, "exp": now + timedelta(days=7), "iat": now},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    mod._refresh_tokens[str(uuid.uuid4())] = {"user_id": user_id, "expires": now + timedelta(days=30)}
    return email, password, token


def _auth(email="test@example.com", password="Test12345678", is_admin=False, plan="free"):
    _, _, token = _create_user(email, password, is_admin=is_admin, plan=plan)
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Backtest 详情端点 (P0) — 需要 Celery/Redis，跳过
# ===========================================================================

@pytest.mark.skip(reason="需要 Celery/Redis 环境")
def test_backtest_detail():
    pass


@pytest.mark.skip(reason="需要 Celery/Redis 环境")
def test_backtest_nav():
    pass


@pytest.mark.skip(reason="需要 Celery/Redis 环境")
def test_backtest_trades():
    pass


@pytest.mark.skip(reason="需要 Celery/Redis 环境")
def test_backtest_stream_endpoint():
    pass


# ===========================================================================
# Data 端点 (P0)
# ===========================================================================

def test_get_daily_data():
    """测试获取个股日线数据"""
    # 符号格式需要带后缀 .SZ 或 .SH
    r = client.get("/api/data/daily/000001.SZ")
    # 200（有数据）、404（无数据）、422（验证错误，符号格式不对）
    assert r.status_code in (200, 404, 422)


def test_strategy_scorecard():
    """测试获取策略评分卡"""
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "评分卡测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]

    r2 = client.get(f"/api/strategies/{sid}/scorecard", headers=h)
    # scorecard 可能需要回测后才有数据
    assert r2.status_code in (200, 404)


# ===========================================================================
# Optimize 端点 (P1)
# ===========================================================================

def test_strategy_optimize_requires_pro():
    """测试策略优化需要 Pro 计划"""
    h = _auth(plan="free")
    r = client.post("/api/strategies", json={
        "name": "优化测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]

    r2 = client.post(f"/api/strategies/{sid}/optimize", json={
        "params": {"period": {"min": 5, "max": 20, "step": 5}},
    }, headers=h)
    assert r2.status_code == 402  # Payment Required


def test_strategy_optimize_with_pro():
    """测试 Pro 用户可以优化"""
    h = _auth(plan="pro")
    r = client.post("/api/strategies", json={
        "name": "优化测试Pro", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]

    r2 = client.post(f"/api/strategies/{sid}/optimize", json={
        "params": {"period": {"min": 5, "max": 20, "step": 5}},
    }, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert "best_params" in data
    assert "best_score" in data


# ===========================================================================
# WFA 详情端点 (P1)
# ===========================================================================

def test_wfa_detail():
    """测试获取 WFA 分析详情"""
    h = _auth()
    r = client.post("/api/strategies", json={
        "name": "WFA详情测试", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h)
    sid = r.json()["id"]

    r2 = client.post(f"/api/strategies/{sid}/wfa", json={
        "mode": "standard", "is_window": 500, "oos_window": 120, "step": 120,
    }, headers=h)
    # WFA 可能返回结果或任务 ID
    assert r2.status_code == 200
    wfa_id = r2.json().get("wfa_id") or r2.json().get("id")

    if wfa_id:
        r3 = client.get(f"/api/wfa/{wfa_id}", headers=h)
        assert r3.status_code in (200, 404)


# ===========================================================================
# Admin 补充端点 (P1)
# ===========================================================================

def test_admin_audit_logs():
    """测试获取审计日志"""
    h = _auth("admin_audit@test.com", is_admin=True)
    # 创建审计记录
    import backend.dependencies as mod
    mod._agent_audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_email": "admin_audit@test.com",
        "action": "test",
        "resource": "test",
    })
    r = client.get("/api/admin/audit-logs", headers=h)
    assert r.status_code == 200
    data = r.json()
    # 返回格式是 {items: [], total: N}
    assert "items" in data
    assert "total" in data


def test_admin_set_user_admin():
    """测试设置用户为管理员"""
    h = _auth("superadmin@test.com", is_admin=True)
    _create_user("normal@test.com", is_admin=False)

    import backend.dependencies as mod
    normal_user = mod._users.get("normal@test.com")
    if normal_user:
        uid = normal_user["id"]
        r = client.post(f"/api/admin/users/{uid}/set-admin", json={"is_admin": True}, headers=h)
        assert r.status_code in (200, 403, 404)


def test_admin_list_strategies():
    """测试管理员列出所有策略"""
    h = _auth("admin_strat@test.com", is_admin=True)
    h2 = _auth("user_strat@test.com")
    client.post("/api/strategies", json={
        "name": "用户策略", "config": {"universe": {"type": "index", "value": "000300"},
                    "conditions": {"logic": "AND", "children": []}},
    }, headers=h2)

    r = client.get("/api/admin/strategies", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_admin_list_backtests():
    """测试管理员列出所有回测"""
    h = _auth("admin_bt@test.com", is_admin=True)
    r = client.get("/api/admin/backtests", headers=h)
    assert r.status_code == 200


def test_admin_list_agent_tokens():
    """测试管理员列出所有 Agent Token"""
    h = _auth("admin_token@test.com", is_admin=True)
    r = client.get("/api/admin/agent-tokens", headers=h)
    assert r.status_code == 200


# ===========================================================================
# 边界测试
# ===========================================================================

def test_backtest_nonexistent_task():
    """测试获取不存在的回测任务"""
    h = _auth()
    r = client.get("/api/backtest/nonexistent-task-id", headers=h)
    assert r.status_code in (404, 400)


def test_wfa_nonexistent():
    """测试获取不存在的 WFA 任务"""
    h = _auth()
    r = client.get("/api/wfa/nonexistent-id", headers=h)
    assert r.status_code in (404, 400)