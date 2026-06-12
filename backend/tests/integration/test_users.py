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

    async def test_change_password_rejects_short_password(self, client: AsyncClient, registered_user: dict):
        """用户修改密码必须复用注册时的最低长度策略。"""
        resp = await client.patch("/api/v1/users/me", headers=registered_user["headers"], json={
            "password": "123",
        })

        assert resp.status_code == 422

    async def test_update_unauthorized(self, client: AsyncClient):
        resp = await client.patch("/api/v1/users/me", json={"name": "hacker"})
        assert resp.status_code == 403


class TestAdminUserUpdates:
    """管理员用户维护。"""

    async def test_admin_reset_password_rejects_short_password(self, client: AsyncClient, registered_user: dict):
        """管理员重置密码也必须执行同一密码策略。"""
        create_resp = await client.post(
            "/api/v1/admin/users",
            headers=registered_user["headers"],
            json={
                "name": "被重置用户",
                "email": "reset@example.com",
                "password": "valid123",
                "role": "user",
            },
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["data"]["id"]

        resp = await client.patch(
            f"/api/v1/admin/users/{user_id}",
            headers=registered_user["headers"],
            json={"password": "123"},
        )

        assert resp.status_code == 422
