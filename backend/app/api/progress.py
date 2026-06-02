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

    # 计算进度
    progress = AssessmentService.calculate_overall_progress(progress_list)

    # 模块级别进度
    syllabus = path.syllabus or []
    module_progress = []
    for module in syllabus:
        module_node_ids = module.get("node_ids", [])
        module_progress_list = [p for p in progress_list if p["node_id"] in module_node_ids]
        mp = AssessmentService.calculate_overall_progress(module_progress_list)
        module_progress.append({
            "module_name": module.get("module_name", ""),
            "total_nodes": mp["total_nodes"],
            "completed_nodes": mp["completed_nodes"],
            "mastery": mp["overall_mastery"],
        })

    # 需要复习的节点
    now = datetime.now(timezone.utc)
    review_due = [
        p for p in progress_list
        if p.get("next_review") and p["next_review"] <= now
    ]

    return {
        "data": {
            **progress,
            "module_progress": module_progress,
            "review_due": review_due[:10],
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
