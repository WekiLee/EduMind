"""测验答题卡缓存回归测试。"""

import pytest
from fastapi import HTTPException

from app.api import quiz as quiz_api


class FakeRedis:
    """用于验证答题卡共享缓存行为的最小 Redis 替身。"""

    def __init__(self):
        self.values: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str):
        self.values[key] = value

    async def get(self, key: str):
        return self.values.get(key)


@pytest.mark.asyncio
async def test_submit_quiz_rejects_expired_answer_cache(monkeypatch):
    """答题卡缺失时不能重新生成题目判当前提交。"""

    async def fake_require_owned_node(*_args, **_kwargs):
        return {"id": "node-1", "domain_id": "general"}

    async def fail_generate_quiz(*_args, **_kwargs):
        raise AssertionError("缓存缺失时不应重新生成题目")

    quiz_api._answer_cache.clear()
    monkeypatch.setattr(quiz_api, "require_owned_node", fake_require_owned_node)
    monkeypatch.setattr(quiz_api.AssessmentService, "generate_quiz", fail_generate_quiz)

    with pytest.raises(HTTPException) as exc:
        await quiz_api.submit_quiz(
            "node-1",
            quiz_api.SubmitQuizRequest(answers=[{"question_id": "q1", "selected": "A"}]),
            user_id="user-1",
            db=None,
        )

    assert exc.value.status_code == 410


@pytest.mark.asyncio
async def test_answer_cache_uses_redis_before_memory(monkeypatch):
    """答题卡应优先从 Redis 共享缓存恢复，支持多进程提交。"""
    fake_redis = FakeRedis()

    async def fake_get_redis():
        return fake_redis

    monkeypatch.setattr(quiz_api, "get_redis", fake_get_redis)
    quiz_api._answer_cache.clear()

    questions = [{"id": "q1", "answer": "A"}]
    await quiz_api._set_cached_answers("user-1:path-1:node-1", questions)
    quiz_api._answer_cache.clear()

    assert await quiz_api._get_cached_answers("user-1:path-1:node-1") == questions
