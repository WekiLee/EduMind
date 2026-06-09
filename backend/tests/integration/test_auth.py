"""集成测试 —— 认证 API"""

import pytest
from httpx import AsyncClient


class TestRegister:
    """注册端点"""

    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "name": "新用户",
            "email": "new@example.com",
            "password": "123456",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["email"] == "new@example.com"
        assert data["name"] == "新用户"
        assert data["role"] == "admin"  # 首位用户自动成为管理员

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/register", json={
            "name": "重复用户",
            "email": "test@example.com",
            "password": "123456",
        })
        assert resp.status_code == 409

    async def test_register_short_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "name": "弱密码",
            "email": "weak@example.com",
            "password": "123",
        })
        assert resp.status_code == 422


class TestLogin:
    """登录端点"""

    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "123456",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "123456",
        })
        assert resp.status_code == 401


class TestMe:
    """获取当前用户信息"""

    async def test_get_me_authenticated(self, client: AsyncClient, registered_user: dict):
        resp = await client.get("/api/v1/auth/me", headers=registered_user["headers"])
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "test@example.com"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403  # HTTPBearer 默认 403

    async def test_get_me_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
