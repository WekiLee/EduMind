"""学习路径 API"""

import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.path import LearningPath
from app.models.progress import NodeProgress
from app.models.user import User
from app.services.content_pipeline import ContentPipelineService
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/learning-paths", tags=["学习路径"])


class CreatePathByTopic(BaseModel):
    mode: str = "topic"
    topic: str
    domain_id: str = "general"
    depth: str = "intermediate"


@router.post("", status_code=201)
async def create_learning_path(
    body: CreatePathByTopic,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建学习路径（主题模式）"""
    # 管理员不能学习
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员账号仅用于管理，无法创建学习路径")
    pipeline = ContentPipelineService(db)
    path = await pipeline.process_topic(user_id, body.topic, body.domain_id)
    return {"data": path.to_dict()}


class CreatePathWithSearch(BaseModel):
    mode: str = "topic_search"
    topic: str
    domain_id: str = "general"


@router.post("/with-search", status_code=201)
async def create_learning_path_with_search(
    body: CreatePathWithSearch,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建学习路径（主题+搜索增强模式）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员账号仅用于管理，无法创建学习路径")
    pipeline = ContentPipelineService(db)
    path = await pipeline.process_topic_with_search(user_id, body.topic, body.domain_id)
    return {"data": path.to_dict()}


class CreatePathByUpload(BaseModel):
    mode: str = "upload"
    domain_id: str = "general"
    topic: str | None = None


@router.post("/upload", status_code=201)
async def create_path_by_upload(
    file: UploadFile = File(...),
    domain_id: str = Form("general"),
    topic: str | None = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建学习路径（上传文件模式）"""
    # 检查文件格式
    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    supported = ["pdf", "docx", "pptx", "md", "txt"]
    if ext not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式: {ext}，支持: {', '.join(supported)}",
        )

    # 检查文件大小（上限从配置读取，默认 50MB）
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大（{len(content) / 1024 / 1024:.1f}MB），上限为 {settings.max_upload_size_mb}MB",
        )

    # 保存到临时文件
    temp_path = os.path.join(tempfile.gettempdir(), f"upload_{uuid.uuid4().hex}.{ext}")
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        pipeline = ContentPipelineService(db)
        path = await pipeline.process_upload(user_id, temp_path, domain_id, topic)
        return {"data": path.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("")
async def list_learning_paths(
    page: int = 1,
    size: int = 20,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取学习路径列表"""
    # 计算总数
    count_result = await db.execute(select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id))
    total = count_result.scalar()

    # 分页查询
    result = await db.execute(
        select(LearningPath)
        .where(LearningPath.user_id == user_id)
        .order_by(LearningPath.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    paths = result.scalars().all()

    # 补充进度信息（从 syllabus 计算总节点数，从 NodeProgress 计算已学节点数）
    paths_data = []
    for path in paths:
        pd = path.to_dict()
        # syllabus 中的总节点数
        syllabus_nodes = sum(len(m.get("node_ids", [])) for m in (path.syllabus or []))
        # 已完成的节点数
        comp_result = await db.execute(
            select(func.count(NodeProgress.id)).where(
                NodeProgress.path_id == path.id,
                NodeProgress.user_id == user_id,
                NodeProgress.status == "completed",
            )
        )
        completed_nodes = comp_result.scalar() or 0
        pd["node_count"] = syllabus_nodes
        pd["completed_count"] = completed_nodes
        pd["progress"] = round(completed_nodes / syllabus_nodes, 2) if syllabus_nodes > 0 else 0
        paths_data.append(pd)

    return {"data": paths_data, "total": total, "page": page, "size": size}


@router.get("/{path_id}")
async def get_learning_path(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取路径详情（含大纲）"""
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    pd = path.to_dict()

    # 补充节点进度
    np_result = await db.execute(
        select(NodeProgress).where(NodeProgress.path_id == path_id, NodeProgress.user_id == user_id)
    )
    progress_map = {np.node_id: np.to_dict() for np in np_result.scalars().all()}

    # 从 Neo4j 获取所有节点标题
    kg = KnowledgeGraphService()
    node_titles = {}
    for module in pd.get("syllabus", []):
        for nid in module.get("node_ids", []):
            if nid not in node_titles:
                node = await kg.get_node(nid)
                node_titles[nid] = node.get("title", nid[:12]) if node else nid[:12]

    # 在大纲中嵌入状态 + 标题
    enriched_syllabus = []
    for module in pd.get("syllabus", []):
        enriched_module = {**module, "nodes": []}
        for nid in module.get("node_ids", []):
            np_dict = progress_map.get(nid, {"status": "not_started", "mastery": 0.0})
            enriched_module["nodes"].append(
                {
                    "id": nid,
                    "title": node_titles.get(nid, nid[:12]),
                    "status": np_dict.get("status", "not_started"),
                    "mastery": np_dict.get("mastery", 0.0),
                }
            )
        enriched_syllabus.append(enriched_module)
    pd["syllabus"] = enriched_syllabus

    return {"data": pd}


@router.patch("/{path_id}")
async def update_syllabus(
    path_id: str,
    syllabus: list[dict],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新大纲（用户拖拽调整后）"""
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    path.syllabus = syllabus
    await db.flush()
    return {"data": path.to_dict()}


@router.patch("/{path_id}/profile-override")
async def update_path_profile_override(
    path_id: str,
    learner_profile_override: dict | None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新路径的 Learner Profile 覆盖"""
    from app.services.learner_profile import normalize

    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    if learner_profile_override is None:
        path.learner_profile_override = None
    else:
        path.learner_profile_override = normalize(learner_profile_override)
    await db.flush()
    return {"data": path.to_dict()}


@router.delete("/{path_id}", status_code=204)
async def delete_learning_path(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """删除学习路径及关联数据"""
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习路径不存在")

    # 清理图谱
    try:
        kg = KnowledgeGraphService()
        await kg.delete_path_graph(path_id)
    except Exception:
        pass  # Neo4j 清理失败不影响 PG 删除

    await db.delete(path)
    await db.flush()
