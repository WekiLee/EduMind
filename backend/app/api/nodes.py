"""知识点节点 API"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guards import require_owned_node, require_owned_path
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.progress import NodeProgress
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/nodes", tags=["知识点"])


@router.get("/{node_id}")
async def get_node(
    node_id: str,
    path_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取节点完整内容"""
    node = await require_owned_node(node_id, user_id, db, path_id)
    kg = KnowledgeGraphService()

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
    path_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取以该节点为中心的图谱子图（含掌握度）"""
    await require_owned_node(node_id, user_id, db, path_id)
    kg = KnowledgeGraphService()
    graph = await kg.get_subgraph(node_id)

    # 如果传了 path_id，补充节点掌握度
    if path_id and graph.get("nodes"):
        await require_owned_path(path_id, user_id, db)
        result = await db.execute(
            select(NodeProgress).where(
                NodeProgress.user_id == user_id,
                NodeProgress.path_id == path_id,
            )
        )
        progress_map = {np.node_id: np for np in result.scalars().all()}

        for node in graph["nodes"]:
            nid = node.get("id", "")
            np = progress_map.get(nid)
            if np:
                node["mastery"] = np.mastery
                node["status"] = np.status
            else:
                node["mastery"] = 0.0
                node["status"] = "not_started"

    return {"data": graph}
