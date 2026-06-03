"""进度 API"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.path import LearningPath
from app.models.progress import NodeProgress
from app.services.assessment import AssessmentService

router = APIRouter(prefix="/nodes", tags=["进度"])
path_progress_router = APIRouter(prefix="/learning-paths", tags=["进度"])


@path_progress_router.get("/{path_id}/progress")
async def get_path_progress(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取路径全局进度"""
    # 验证路径存在且属于当前用户
    result = await db.execute(
        select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id)
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    # 获取所有节点进度
    result = await db.execute(
        select(NodeProgress).where(NodeProgress.path_id == path_id, NodeProgress.user_id == user_id)
    )
    progress_list = [np.to_dict() for np in result.scalars().all()]

    # syllabus 中的总节点数
    syllabus_total = sum(len(m.get("node_ids", [])) for m in (path.syllabus or []))
    completed_count = sum(1 for p in progress_list if p.get("status") == "completed")
    total_mastery = sum(p.get("mastery", 0.0) or 0.0 for p in progress_list)

    progress = {
        "total_nodes": syllabus_total,
        "completed_nodes": completed_count,
        "progress_pct": round(completed_count / syllabus_total * 100, 1) if syllabus_total > 0 else 0,
        "overall_mastery": round(total_mastery / syllabus_total, 2) if syllabus_total > 0 else 0,
    }

    # 模块级别进度
    syllabus = path.syllabus or []
    module_progress = []
    for module in syllabus:
        module_node_ids = module.get("node_ids", [])
        total_in_module = len(module_node_ids)
        module_progress_list = [p for p in progress_list if p["node_id"] in module_node_ids]
        completed_in_module = sum(1 for p in module_progress_list if p.get("status") == "completed")
        mastery_sum = sum(p.get("mastery", 0.0) or 0.0 for p in module_progress_list)
        module_progress.append({
            "module_name": module.get("module_name", ""),
            "total_nodes": total_in_module,
            "completed_nodes": completed_in_module,
            "mastery": round(mastery_sum / total_in_module, 2) if total_in_module > 0 else 0,
        })

    # 需要复习的节点
    now = datetime.now(timezone.utc)
    review_due = []
    for p in progress_list:
        nr = p.get("next_review")
        if nr:
            if isinstance(nr, str):
                try:
                    nr_dt = datetime.fromisoformat(nr)
                except ValueError:
                    continue
            else:
                nr_dt = nr
            if nr_dt <= now:
                review_due.append(p)

    return {
        "data": {
            **progress,
            "module_progress": module_progress,
            "review_due": review_due[:10],
        }
    }


@path_progress_router.get("/{path_id}/report")
async def get_learning_report(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """学习报告（掌握度热力图 + 薄弱节点 + 时间统计）"""
    result = await db.execute(
        select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id)
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    # 节点进度
    result = await db.execute(
        select(NodeProgress).where(NodeProgress.path_id == path_id, NodeProgress.user_id == user_id)
    )
    progress_list = [np.to_dict() for np in result.scalars().all()]

    # 模块掌握度
    syllabus = path.syllabus or []
    module_mastery = []
    for module in syllabus:
        module_node_ids = module.get("node_ids", [])
        mp_list = [p for p in progress_list if p["node_id"] in module_node_ids]
        total = len(mp_list)
        avg_mastery = sum(p.get("mastery", 0) or 0 for p in mp_list) / total if total > 0 else 0
        module_mastery.append({
            "module_name": module.get("module_name", ""),
            "total_nodes": total,
            "completed": sum(1 for p in mp_list if p.get("status") == "completed"),
            "avg_mastery": round(avg_mastery, 2),
        })

    # 薄弱节点（掌握度 < 0.5）
    weak_nodes = [p for p in progress_list if (p.get("mastery", 0) or 0) < 0.5 and p.get("mastery", 0) > 0]

    # 时间统计（从 quiz_attempts 表获取）
    from app.models.quiz import QuizAttempt
    quiz_result = await db.execute(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.path_id == path_id,
        ).order_by(QuizAttempt.created_at)
    )
    attempts = quiz_result.scalars().all()
    quiz_history = [
        {
            "node_id": a.node_id,
            "score": a.score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in attempts
    ]

    # 整体掌握度（从 syllabus 总节点数计算）
    syllabus_total = sum(len(m.get("node_ids", [])) for m in syllabus)
    total_mastery = sum(p.get("mastery", 0) or 0 for p in progress_list)
    overall_mastery = round(total_mastery / syllabus_total, 2) if syllabus_total > 0 else 0

    return {
        "data": {
            "module_mastery": module_mastery,
            "weak_nodes": weak_nodes[:10],
            "quiz_history": quiz_history,
            "total_quizzes": len(attempts),
            "overall_mastery": overall_mastery,
        }
    }


class StartNodeRequest(BaseModel):
    pass


@router.post("/{node_id}/start")
async def start_node(
    node_id: str,
    _req: StartNodeRequest,
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """开始学习节点"""
    # 查找或创建进度记录
    result = await db.execute(
        select(NodeProgress).where(
            NodeProgress.user_id == user_id,
            NodeProgress.path_id == path_id,
            NodeProgress.node_id == node_id,
        )
    )
    np = result.scalar_one_or_none()

    if np and np.status == "completed":
        return {"data": np.to_dict()}

    if np is None:
        np = NodeProgress(
            user_id=user_id,
            path_id=path_id,
            node_id=node_id,
            status="learning",
            first_learned=datetime.now(timezone.utc),
        )
        db.add(np)
    else:
        np.status = "learning"

    await db.flush()
    return {"data": np.to_dict()}


class CompleteNodeRequest(BaseModel):
    mastery: float = 0.0


@router.post("/{node_id}/complete")
async def complete_node(
    node_id: str,
    req: CompleteNodeRequest,
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """完成节点"""
    result = await db.execute(
        select(NodeProgress).where(
            NodeProgress.user_id == user_id,
            NodeProgress.path_id == path_id,
            NodeProgress.node_id == node_id,
        )
    )
    np = result.scalar_one_or_none()

    if not np:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该节点尚未开始学习")

    np.status = "completed"
    np.mastery = req.mastery
    np.last_reviewed = datetime.now(timezone.utc)

    # 计算下次复习时间
    from app.services.assessment import AssessmentService
    interval_days = AssessmentService.compute_next_review(req.mastery, np.attempt_count)
    from datetime import timedelta
    np.next_review = datetime.now(timezone.utc) + timedelta(days=interval_days)

    await db.flush()
    return {"data": np.to_dict()}
