"""用户 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户"])


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    learner_profile: Optional[dict] = None
    domain_id: Optional[str] = None
    password: Optional[str] = None


@router.patch("/me")
async def update_user(
    req: UpdateUserRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户信息（含密码修改）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if req.name is not None:
        user.name = req.name
    if req.learner_profile is not None:
        user.learner_profile = req.learner_profile
    if req.domain_id is not None:
        user.domain_id = req.domain_id
    if req.password:
        from app.core.security import hash_password
        user.password_hash = hash_password(req.password)
        user.must_change_password = False  # 改密码后清除首次登录标记

    await db.flush()
    return {"data": user.to_dict()}
