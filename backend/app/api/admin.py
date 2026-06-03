"""管理员 API —— 用户管理 / 系统配置 / 内容统计"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id, hash_password
from app.llm.adapter import LLMAdapter
from app.models.path import LearningPath
from app.models.progress import NodeProgress
from app.models.system_config import SystemConfig
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["管理员"])


# ── 权限校验 ──


async def require_admin(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """当前用户必须是管理员"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    return user


# ── 用户管理 ──


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"
    organization: str | None = None


class UpdateUserRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    organization: str | None = None
    password: str | None = None


@router.post("/users", status_code=201)
async def create_user(
    req: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员创建用户"""
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="密码长度不少于6位")
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="角色必须是 admin 或 user")

    user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        organization=req.organization,
        must_change_password=True,  # 管理员创建的账号首次登录也需改密码
        learner_profile={},
    )
    db.add(user)
    await db.flush()
    return {"data": user.to_dict()}


@router.get("/users")
async def list_users(
    page: int = 1,
    size: int = 50,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员）"""
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    result = await db.execute(select(User).order_by(User.created_at.desc()).offset((page - 1) * size).limit(size))
    users = result.scalars().all()

    # 统计每个用户的路径数和完成数
    users_data = []
    for u in users:
        ud = u.to_dict()
        np_result = await db.execute(
            select(func.count(LearningPath.id), func.count().filter(LearningPath.status == "completed")).where(
                LearningPath.user_id == u.id
            )
        )
        path_count, completed_count = np_result.one()
        ud["path_count"] = path_count
        ud["completed_count"] = completed_count
        users_data.append(ud)

    return {"data": users_data, "total": total, "page": page, "size": size}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户信息（管理员）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if req.name is not None:
        user.name = req.name
    if req.role is not None or req.is_active is not None:
        # 如果是针对自己的操作，且这是最后一个管理员
        if user_id == admin.id or user.role == "admin":
            count_result = await db.execute(select(func.count(User.id)).where(User.role == "admin", User.is_active))
            last_admin_count = count_result.scalar()
            # 如果是最后一个活跃管理员
            if user.id == admin.id and last_admin_count <= 1:
                if req.role == "user" or req.is_active is False:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="系统中至少需要一名活跃的管理员，无法降级或禁用自己",
                    )

    if req.role is not None:
        if req.role not in ("admin", "user"):
            raise HTTPException(status_code=422, detail="角色必须是 admin 或 user")
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.organization is not None:
        user.organization = req.organization
    if req.password:
        user.password_hash = hash_password(req.password)

    await db.flush()
    return {"data": user.to_dict()}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（管理员）"""
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 检查是否是最后一个管理员
    if user.role == "admin":
        count_result = await db.execute(select(func.count(User.id)).where(User.role == "admin", User.is_active))
        if count_result.scalar() <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除最后一个管理员")

    # 级联删除相关数据
    from app.models.path import LearningPath
    from app.models.quiz import ChatMessage, ChatSession, QuizAttempt

    await db.execute(
        ChatMessage.__table__.delete().where(
            ChatMessage.session_id.in_(select(ChatSession.id).where(ChatSession.user_id == user_id))
        )
    )
    await db.execute(ChatSession.__table__.delete().where(ChatSession.user_id == user_id))
    await db.execute(QuizAttempt.__table__.delete().where(QuizAttempt.user_id == user_id))
    await db.execute(NodeProgress.__table__.delete().where(NodeProgress.user_id == user_id))
    await db.execute(LearningPath.__table__.delete().where(LearningPath.user_id == user_id))
    await db.delete(user)
    await db.flush()


# ── 系统配置 ──


class SystemConfigRequest(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    allow_self_register: bool | None = None


@router.get("/config")
async def get_config(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统配置（管理员）"""
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        return {
            "data": {
                "llm_provider": "openai-compatible",
                "llm_model": "deepseek-v4-flash",
                "llm_api_base": "https://api.deepseek.com/v1",
                "allow_self_register": True,
            }
        }
    cd = config.to_dict()
    # API Key 部分遮盖后返回
    if config.llm_api_key:
        key = config.llm_api_key
        cd["llm_api_key_masked"] = key[:6] + "****" + key[-4:] if len(key) > 12 else "****"
    return {"data": cd}


@router.put("/config")
async def update_config(
    req: SystemConfigRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新系统配置（管理员）"""
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config:
        config = SystemConfig(updated_by=admin.id)
        db.add(config)

    if req.llm_provider is not None:
        config.llm_provider = req.llm_provider
    if req.llm_model is not None:
        config.llm_model = req.llm_model
    if req.llm_api_key is not None:
        config.llm_api_key = req.llm_api_key
    if req.llm_api_base is not None:
        config.llm_api_base = req.llm_api_base
    if req.allow_self_register is not None:
        config.allow_self_register = req.allow_self_register
    config.updated_by = admin.id

    await db.flush()

    # 同步更新 LLM 运行时配置
    LLMAdapter.update_runtime_config(
        provider=config.llm_provider,
        model=config.llm_model,
        api_key=config.llm_api_key,
        api_base=config.llm_api_base,
    )

    return {"data": config.to_dict()}


# ── 内容统计 ──


@router.get("/stats")
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统统计概览（管理员）"""

    user_count = await db.execute(select(func.count(User.id)))
    path_count = await db.execute(select(func.count(LearningPath.id)))
    completed_paths = await db.execute(select(func.count(LearningPath.id)).where(LearningPath.status == "completed"))

    # 按领域统计路径数
    domain_result = await db.execute(
        select(LearningPath.domain_id, func.count(LearningPath.id)).group_by(LearningPath.domain_id)
    )
    domain_stats = [{"domain": d, "count": c} for d, c in domain_result.all()]

    return {
        "data": {
            "total_users": user_count.scalar(),
            "total_paths": path_count.scalar(),
            "completed_paths": completed_paths.scalar(),
            "domain_stats": domain_stats,
        }
    }
