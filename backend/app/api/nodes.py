"""知识点节点 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/nodes", tags=["知识点"])


@router.get("/{node_id}")
async def get_node(
    node_id: str,
    _user_id: str = Depends(get_current_user_id),
):
    """获取节点完整内容"""
    kg = KnowledgeGraphService()
    node = await kg.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")

    # 补充关联信息
    prerequisites = await kg.get_prerequisites(node_id)
    related = await kg.get_related_nodes(node_id)

    return {
        "data": {
            **node,
            "prerequisites": [{"id": n.get("id"), "title": n.get("title")} for n in prerequisites],
            "related_nodes": [{"id": n.get("id"), "title": n.get("title")} for n in related],
        }
    }


@router.get("/{node_id}/graph")
async def get_node_graph(
    node_id: str,
    _user_id: str = Depends(get_current_user_id),
):
    """获取以该节点为中心的图谱子图"""
    kg = KnowledgeGraphService()
    graph = await kg.get_subgraph(node_id)
    return {"data": graph}
