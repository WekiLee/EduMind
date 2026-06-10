"""集成测试 —— 简化评估 API"""

from httpx import AsyncClient


async def test_assessment_response_contains_required_fields(client: AsyncClient, registered_user: dict):
    """评估响应需包含分数、百分比、难度级别与时间戳。"""
    user_id = registered_user["user"]["id"]
    resp = await client.post(
        "/api/v1/assessment",
        headers=registered_user["headers"],
        json={
            "user_id": user_id,
            "subject": "Mathematics",
            "answers": [1, 0, 2, 1, 3, 0, 2, 1, 0, 3],
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["score"] == 7
    assert data["percentage"] == 70.0
    assert data["difficulty_level"] == "intermediate"
    assert data["timestamp"]
    assert data["assessment_method"] == "compatibility_count_positive_answers"
    assert data["calibrated"] is False
    assert data["confidence"] == "low"
    assert data["fairness_note"]


async def test_assessment_rejects_other_user(client: AsyncClient, registered_user: dict):
    """用户不能为其他 user_id 提交评估。"""
    resp = await client.post(
        "/api/v1/assessment",
        headers=registered_user["headers"],
        json={
            "user_id": "other-user",
            "subject": "Mathematics",
            "answers": [1],
        },
    )

    assert resp.status_code == 403


async def test_assessment_rejects_out_of_range_answer(client: AsyncClient, registered_user: dict):
    """兼容评估接口应拒绝超出约定范围的答案编码。"""
    user_id = registered_user["user"]["id"]
    resp = await client.post(
        "/api/v1/assessment",
        headers=registered_user["headers"],
        json={
            "user_id": user_id,
            "subject": "Mathematics",
            "answers": [1, 4],
        },
    )

    assert resp.status_code == 422
