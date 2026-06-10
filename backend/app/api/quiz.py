"""测验 API —— 生成时缓存答题卡，提交时取缓存判卷"""

import json
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guards import require_owned_node, require_owned_path
from app.core.config import settings
from app.core.database import get_db, get_redis
from app.core.security import get_current_user_id
from app.models.progress import NodeProgress
from app.services.assessment import AssessmentService
from app.services.domain_profile import load_domain_profile

router = APIRouter(prefix="", tags=["测验"])

# ── 答题卡缓存：生产优先使用 Redis，内存缓存仅作为开发降级 ──
# key: quiz_answers:user_id:path_id:node_id, value: questions_with_answers
_answer_cache: dict[str, tuple[list[dict], float]] = {}
_CACHE_TTL = 3600  # 1 小时
_CACHE_PREFIX = "quiz_answers"


def _redis_required() -> bool:
    """生产环境必须使用共享缓存，避免多实例答题卡丢失。"""
    return settings.environment.lower() in {"prod", "production"}


def _get_memory_cached_answers(cache_key: str) -> list[dict] | None:
    entry = _answer_cache.get(cache_key)
    if entry:
        questions, ts = entry
        if time.time() - ts < _CACHE_TTL:
            return questions
        del _answer_cache[cache_key]
    return None


def _set_memory_cached_answers(cache_key: str, questions: list[dict]) -> None:
    _answer_cache[cache_key] = (questions, time.time())


async def _get_cached_answers(cache_key: str) -> list[dict] | None:
    """从共享缓存读取答题卡，Redis 不可用时开发环境降级到内存。"""
    redis_key = f"{_CACHE_PREFIX}:{cache_key}"
    try:
        redis = await get_redis()
        cached = await redis.get(redis_key)
        if cached:
            questions = json.loads(cached)
            if isinstance(questions, list):
                _set_memory_cached_answers(cache_key, questions)
                return questions
    except Exception as e:
        if _redis_required():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="测验答题卡缓存不可用，请稍后重试",
            ) from e
    return _get_memory_cached_answers(cache_key)


async def _set_cached_answers(cache_key: str, questions: list[dict]) -> None:
    """写入答题卡缓存，生产环境 Redis 失败时直接阻断生成。"""
    _set_memory_cached_answers(cache_key, questions)
    redis_key = f"{_CACHE_PREFIX}:{cache_key}"
    try:
        redis = await get_redis()
        await redis.setex(redis_key, _CACHE_TTL, json.dumps(questions, ensure_ascii=False))
    except Exception as e:
        if _redis_required():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="测验答题卡缓存不可用，请稍后重试",
            ) from e


def _quiz_cache_key(user_id: str, node_id: str, path_id: str | None) -> str:
    """生成按用户和路径隔离的测验缓存键。"""
    return f"{user_id}:{path_id or '-'}:{node_id}"


@router.post("/nodes/{node_id}/quiz")
async def generate_quiz(
    node_id: str,
    path_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """为节点生成测验（同时缓存答题卡供提交时使用）"""
    node = await require_owned_node(node_id, user_id, db, path_id)

    domain_id = node.get("domain_id", "general")
    profile = load_domain_profile(domain_id)

    assessment = AssessmentService(db)
    quiz = await assessment.generate_quiz(node, profile.get("domain", {}))
    questions = quiz.get("questions", [])

    # 缓存完整题目（含答案）用于判卷
    await _set_cached_answers(_quiz_cache_key(user_id, node_id, path_id), questions)

    # 返回给前端时不包含答案
    client_questions = [{k: v for k, v in q.items() if k != "answer"} for q in questions]

    return {
        "data": {
            "quiz_id": node_id,
            "questions": client_questions,
        }
    }


class SubmitQuizRequest(BaseModel):
    answers: list[dict]
    path_id: str | None = None


@router.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    req: SubmitQuizRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """提交测验答案（从缓存取答题卡判卷）"""
    await require_owned_node(quiz_id, user_id, db, req.path_id)

    # 从缓存取正确答案
    cache_key = _quiz_cache_key(user_id, quiz_id, req.path_id)
    questions = await _get_cached_answers(cache_key)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="测验已过期，请重新生成后再提交",
        )

    # 判卷
    assessment = AssessmentService(db)
    result = assessment.grade_quiz(questions, req.answers)

    # 保存测验记录
    if req.path_id:
        await require_owned_path(req.path_id, user_id, db)
        await assessment.save_attempt(
            user_id=user_id,
            path_id=req.path_id,
            node_id=quiz_id,
            score=result["score"],
            total=result["total"],
            correct=result["correct"],
            answers=req.answers,
        )

        # 更新掌握度 + 复习计划
        np_result = await db.execute(
            select(NodeProgress).where(
                NodeProgress.user_id == user_id,
                NodeProgress.path_id == req.path_id,
                NodeProgress.node_id == quiz_id,
            )
        )
        np = np_result.scalar_one_or_none()
        if np:
            scores = list(np.quiz_scores or []) + [result["score"]]
            np.quiz_scores = scores
            np.mastery = AssessmentService.calculate_mastery(scores, np.mastery)
            np.attempt_count += 1  # 每次测验递增复习计数
            # 根据新掌握度重算下次复习时间
            interval_days = AssessmentService.compute_next_review(np.mastery, np.attempt_count)
            np.next_review = datetime.now(UTC) + timedelta(days=interval_days)
            np.last_reviewed = datetime.now(UTC)
            if result["score"] >= 0.6:
                result["passed"] = True
                result["mastery_update"] = np.mastery

    return {"data": result}
