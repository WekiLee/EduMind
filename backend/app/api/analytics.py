"""学习分析 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.path import LearningPath
from app.models.progress import NodeProgress
from app.models.quiz import QuizAttempt

router = APIRouter(prefix="/analytics", tags=["分析"])


@router.get("")
async def get_analytics(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的学习分析摘要。"""
    path_count = await db.execute(select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id))
    completed_paths = await db.execute(
        select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id, LearningPath.status == "completed")
    )
    node_count = await db.execute(select(func.count(NodeProgress.id)).where(NodeProgress.user_id == user_id))
    completed_nodes = await db.execute(
        select(func.count(NodeProgress.id)).where(NodeProgress.user_id == user_id, NodeProgress.status == "completed")
    )
    avg_mastery = await db.execute(select(func.avg(NodeProgress.mastery)).where(NodeProgress.user_id == user_id))
    quiz_count = await db.execute(select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id))
    avg_score = await db.execute(select(func.avg(QuizAttempt.score)).where(QuizAttempt.user_id == user_id))

    total_nodes = node_count.scalar() or 0
    done_nodes = completed_nodes.scalar() or 0
    progress_pct = round(done_nodes / total_nodes * 100, 1) if total_nodes else 0.0

    return {
        "data": {
            "total_paths": path_count.scalar() or 0,
            "completed_paths": completed_paths.scalar() or 0,
            "total_nodes": total_nodes,
            "completed_nodes": done_nodes,
            "progress_pct": progress_pct,
            "overall_mastery": round(float(avg_mastery.scalar() or 0.0), 2),
            "total_quizzes": quiz_count.scalar() or 0,
            "average_quiz_score": round(float(avg_score.scalar() or 0.0), 2),
        }
    }
