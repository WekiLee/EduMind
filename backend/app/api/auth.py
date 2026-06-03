"""认证 API —— 首位用户自动为管理员"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.models.system_config import SystemConfig
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户（首位用户自动成为管理员）"""
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="密码长度不少于6位")

    # 检查系统是否允许自助注册
    config_result = await db.execute(select(SystemConfig).limit(1))
    config = config_result.scalar_one_or_none()
    if config and config.allow_self_register is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前系统已关闭自助注册，请联系管理员")

    # 查是否已有用户——首位用户自动为管理员
    count_result = await db.execute(select(func.count(User.id)))
    user_count = count_result.scalar()
    role = "admin" if user_count == 0 else "user"

    user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role=role,
        organization=req.organization,
        learner_profile={
            "abstraction_level": 0.5,
            "analogy_density": 0.5,
            "teaching_speed": 0.5,
            "feedback_tone": 0.5,
            "quiz_style": 0.5,
        },
    )
    db.add(user)
    await db.flush()

    # 首次注册时自动创建系统配置
    if role == "admin" and not config:
        sys_config = SystemConfig(
            llm_provider="openai-compatible",
            llm_model="deepseek-v4-flash",
            llm_api_base="https://api.deepseek.com/v1",
            updated_by=user.id,
        )
        db.add(sys_config)
        await db.flush()

    return {"data": user.to_dict()}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    token = create_access_token(user.id)
    return {"data": {"access_token": token, "token_type": "bearer", "user": user.to_dict()}}


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {"data": user.to_dict()}
