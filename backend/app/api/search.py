"""语义搜索 API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guards import list_owned_path_ids, require_owned_path
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.semantic_search import SemanticSearchService

router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("")
async def semantic_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    path_id: str | None = Query(None, description="限定学习路径"),
    top_k: int = Query(5, ge=1, le=20),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """语义搜索知识点"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    if path_id:
        await require_owned_path(path_id, user_id, db)
        path_ids = [path_id]
    else:
        path_ids = await list_owned_path_ids(user_id, db)
        if not path_ids:
            return {"data": []}

    svc = SemanticSearchService()
    results = await svc.search(db, q, path_ids, top_k)
    return {"data": results}
