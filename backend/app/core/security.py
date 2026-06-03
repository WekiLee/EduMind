"""安全模块 —— JWT 令牌 + 密码哈希"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ── 密码 ──


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


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


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI 依赖注入：从请求中解析当前用户 ID"""
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
