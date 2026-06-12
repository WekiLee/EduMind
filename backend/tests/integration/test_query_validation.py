"""查询参数边界集成测试。"""

from httpx import AsyncClient


async def test_learning_paths_rejects_invalid_page(client: AsyncClient, registered_user: dict):
    """学习路径分页页码必须从 1 开始。"""
    resp = await client.get("/api/v1/learning-paths?page=0", headers=registered_user["headers"])

    assert resp.status_code == 422


async def test_admin_users_rejects_oversized_page_size(client: AsyncClient, registered_user: dict):
    """管理员用户列表必须限制单页大小。"""
    resp = await client.get("/api/v1/admin/users?size=1000", headers=registered_user["headers"])

    assert resp.status_code == 422


async def test_mastery_trend_rejects_invalid_limit(client: AsyncClient, registered_user: dict):
    """趋势接口 limit 必须为正数。"""
    resp = await client.get(
        "/api/v1/learning-paths/path-1/report/trend?limit=0",
        headers=registered_user["headers"],
    )

    assert resp.status_code == 422
