"""测验 API —— 生成时缓存答题卡，提交时取缓存判卷"""

import yaml
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.progress import NodeProgress
from app.services.assessment import AssessmentService
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="", tags=["测验"])

# ── 答题卡缓存：生成 quiz 时保存答案，提交时直接取用 ──
# key: node_id, value: (questions_with_answers, timestamp)
_answer_cache: dict[str, tuple[list[dict], float]] = {}
_CACHE_TTL = 3600  # 1 小时


def _get_cached_answers(node_id: str) -> list[dict] | None:
    entry = _answer_cache.get(node_id)
    if entry:
        questions, ts = entry
        if time.time() - ts < _CACHE_TTL:
            return questions
        del _answer_cache[node_id]
    return None


def _set_cached_answers(node_id: str, questions: list[dict]):
    _answer_cache[node_id] = (questions, time.time())


# ── 领域配置缓存（与 ws/chat.py 共享逻辑，后续可抽取公共模块）──
_domain_profile_cache: dict[str, tuple[dict, float]] = {}
_PROFILE_CACHE_TTL = 300


def load_domain_profile(domain_id: str) -> dict:
    """加载领域配置（带缓存）"""
    entry = _domain_profile_cache.get(domain_id)
    if entry and (time.time() - entry[1]) < _PROFILE_CACHE_TTL:
        return entry[0]

    import os
    path = os.path.join("app", "domain_profiles", f"{domain_id}.yaml")
    if not os.path.exists(path):
        path = os.path.join("app", "domain_profiles", "general.yaml")

    with open(path, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    _domain_profile_cache[domain_id] = (profile, time.time())
    return profile


@router.post("/nodes/{node_id}/quiz")
async def generate_quiz(
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """为节点生成测验（同时缓存答题卡供提交时使用）"""
    kg = KnowledgeGraphService()
    node = await kg.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")

    domain_id = node.get("domain_id", "general")
    profile = load_domain_profile(domain_id)

    assessment = AssessmentService(db)
    quiz = await assessment.generate_quiz(node, profile.get("domain", {}))
    questions = quiz.get("questions", [])

    # 缓存完整题目（含答案）用于判卷
    _set_cached_answers(node_id, questions)

    # 返回给前端时不包含答案
    client_questions = [
        {k: v for k, v in q.items() if k != "answer"}
        for q in questions
    ]

    # 更新进度（用 limit(1) 避免跨路径时 MultipleResultsFound）
    result = await db.execute(
        select(NodeProgress).where(
            NodeProgress.user_id == user_id,
            NodeProgress.node_id == node_id,
        ).limit(1)
    )
    np = result.scalar_one_or_none()
    if np:
        np.attempt_count += 1
    await db.flush()

    return {
        "data": {
            "quiz_id": node_id,
            "questions": client_questions,
        }
    }


class SubmitQuizRequest(BaseModel):
    answers: list[dict]
    path_id: Optional[str] = None


@router.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    req: SubmitQuizRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """提交测验答案（从缓存取答题卡判卷）"""
    # 从缓存取正确答案
    questions = _get_cached_answers(quiz_id)
    if not questions:
        # 缓存未命中 → 从节点重新生成（fallback，需确保一致性）
        kg = KnowledgeGraphService()
        node = await kg.get_node(quiz_id)
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测验不存在或已过期")

        domain_id = node.get("domain_id", "general")
        profile = load_domain_profile(domain_id)
        assessment = AssessmentService(db)
        quiz = await assessment.generate_quiz(node, profile.get("domain", {}))
        questions = quiz.get("questions", [])
        _set_cached_answers(quiz_id, questions)

    # 判卷
    assessment = AssessmentService(db)
    result = assessment.grade_quiz(questions, req.answers)

    # 保存测验记录
    if req.path_id:
        attempt = await assessment.save_attempt(
            user_id=user_id,
            path_id=req.path_id,
            node_id=quiz_id,
            score=result["score"],
            total=result["total"],
            correct=result["correct"],
            answers=req.answers,
        )

        # 更新掌握度
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
            if result["score"] >= 0.6:
                result["passed"] = True
                result["mastery_update"] = np.mastery

    return {"data": result}
