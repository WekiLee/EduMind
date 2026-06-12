"""用户 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id, hash_password, validate_password_strength
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户"])

MODEL_CONFIG_FIELDS = {"provider", "model", "api_base", "api_key"}


def build_model_config_update(incoming: dict, existing: dict | None = None) -> dict:
    """清洗用户级模型配置，区分保留旧密钥与显式清空密钥。"""
    current = existing or {}
    cleaned = {
        k: v
        for k, v in incoming.items()
        if k in MODEL_CONFIG_FIELDS and k != "api_key" and v not in (None, "")
    }
    api_key = incoming.get("api_key")
    if isinstance(api_key, str):
        api_key = api_key.strip()
    if api_key:
        cleaned["api_key"] = api_key
    elif "api_key" not in incoming and current.get("api_key"):
        cleaned["api_key"] = current["api_key"]
    return cleaned


class UpdateUserRequest(BaseModel):
    name: str | None = None
    learner_profile: dict | None = None
    model_config: dict | None = None
    domain_id: str | None = None
    password: str | None = None


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
    if req.model_config is not None:
        user.model_config = build_model_config_update(req.model_config, user.model_config)
    if req.domain_id is not None:
        user.domain_id = req.domain_id
    if req.password is not None:
        validate_password_strength(req.password)
        user.password_hash = hash_password(req.password)
        user.must_change_password = False  # 改密码后清除首次登录标记

    await db.flush()
    return {"data": user.to_dict()}
