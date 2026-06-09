"""集成测试 —— 用户 API"""

import pytest
from httpx import AsyncClient


class TestUpdateUser:
    """更新用户信息"""

    async def test_update_learner_profile(self, client: AsyncClient, registered_user: dict):
        resp = await client.patch("/api/v1/users/me", headers=registered_user["headers"], json={
            "learner_profile": {"content": {"abstraction_level": 0.9, "analogy_density": 0.1}},
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        # learner_profile 存储后端会归一化
        lp = data["learner_profile"]
        assert lp["content"]["abstraction_level"] == 0.9
        assert lp["content"]["analogy_density"] == 0.1

    async def test_change_password(self, client: AsyncClient, registered_user: dict):
        resp = await client.patch("/api/v1/users/me", headers=registered_user["headers"], json={
            "password": "newpass123",
        })
        assert resp.status_code == 200

        # 用新密码登录
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "newpass123",
        })
        assert login_resp.status_code == 200

        # 旧密码失效
        old_login = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "123456",
        })
        assert old_login.status_code == 401

    async def test_update_unauthorized(self, client: AsyncClient):
        resp = await client.patch("/api/v1/users/me", json={"name": "hacker"})
        assert resp.status_code == 403
