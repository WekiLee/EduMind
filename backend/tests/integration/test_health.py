"""集成测试 —— 健康检查"""

import pytest
from httpx import AsyncClient


class TestHealth:
    """健康检查端点"""

    async def test_health_ok(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
