"""P0 Auth 测试补充 — change-password"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.dependencies import hash_password
import uuid
from datetime import datetime, timezone, timedelta
from jose import jwt
from backend.dependencies import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    import backend.dependencies as mod
    mod._users.clear()
    mod._refresh_tokens.clear()
    mod._verification_codes.clear()

def _create_user(email="test@test.com", password="Test12345678"):
    import backend.dependencies as mod
    user_id = str(uuid.uuid4())
    mod._users[email] = {
        "id": user_id, "email": email,
        "password_hash": hash_password(password),
        "plan": "free", "ai_api_key": None, "ai_provider": None,
        "ai_calls_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user_id, "plan": "free", "exp": now + timedelta(days=7), "iat": now},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    return email, password, token

def test_change_password_success():
    email, pw, token = _create_user("cp@test.com", "OldPass123")
    r = client.post("/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "OldPass123", "new_password": "NewPass456"})
    assert r.status_code == 200
    assert r.json()["message"] == "密码已更新"
    # 验证新密码能登录
    r2 = client.post("/api/auth/login",
        json={"email": "cp@test.com", "password": "NewPass456"})
    assert r2.status_code == 200

def test_change_password_wrong_old():
    email, pw, token = _create_user("wp2@test.com", "Correct123")
    r = client.post("/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "WrongOld12", "new_password": "NewPass456"})
    assert r.status_code == 400

def test_change_password_short_new():
    email, pw, token = _create_user("short@test.com", "OldPass123")
    r = client.post("/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "OldPass123", "new_password": "short"})
    assert r.status_code == 422

def test_change_password_requires_auth():
    r = client.post("/api/auth/change-password",
        json={"old_password": "old", "new_password": "newpass123"})
    assert r.status_code in (401, 403)