"""安全模块 —— JWT 令牌 + 密码哈希"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
MIN_PASSWORD_LENGTH = 6


# ── 密码 ──


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> None:
    """校验用户密码最低强度。"""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"密码长度不少于{MIN_PASSWORD_LENGTH}位",
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT ──


def create_access_token(user_id: str) -> str:
    """创建 JWT 访问令牌"""
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expiration_hours)
    payload = {"sub": user_id, "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """解码 JWT 令牌，返回 user_id；失败返回 None"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


async def resolve_active_user_id(token: str, db: AsyncSession) -> str | None:
    """解析令牌并确认用户仍存在且处于启用状态。"""
    user_id = decode_access_token(token)
    if user_id is None:
        return None

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user.id


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """FastAPI 依赖注入：解析当前启用用户 ID。"""
    user_id = await resolve_active_user_id(credentials.credentials, db)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效、过期或已停用的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def get_token_subject(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """仅解析令牌主体；仅用于不需要账号状态的内部测试或诊断。"""
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
