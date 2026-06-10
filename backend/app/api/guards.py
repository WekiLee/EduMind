"""API 资源归属校验工具。"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.path import LearningPath
from app.services.knowledge_graph import KnowledgeGraphService


async def require_owned_path(path_id: str, user_id: str, db: AsyncSession) -> LearningPath:
    """确认学习路径属于当前用户。"""
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")
    return path


def path_contains_node(path: LearningPath, node_id: str) -> bool:
    """从路径大纲判断节点是否属于该路径。"""
    return any(node_id in (module.get("node_ids", []) or []) for module in (path.syllabus or []))


async def require_owned_node(
    node_id: str,
    user_id: str,
    db: AsyncSession,
    path_id: str | None = None,
) -> dict:
    """确认知识节点存在且属于当前用户可访问的学习路径。"""
    kg = KnowledgeGraphService()
    node = await kg.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")

    if path_id:
        path = await require_owned_path(path_id, user_id, db)
        if not path_contains_node(path, node_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")
        return node

    result = await db.execute(select(LearningPath).where(LearningPath.user_id == user_id))
    paths = result.scalars().all()
    if not any(path_contains_node(path, node_id) for path in paths):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")
    return node


async def list_owned_path_ids(user_id: str, db: AsyncSession) -> list[str]:
    """列出当前用户拥有的路径 ID，用于限定跨路径查询范围。"""
    result = await db.execute(select(LearningPath.id).where(LearningPath.user_id == user_id))
    return list(result.scalars().all())
