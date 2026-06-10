"""生产环境配置安全测试。"""

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_DATABASE_URL, DEFAULT_JWT_SECRET, DEFAULT_NEO4J_PASSWORD, Settings


def test_production_rejects_default_secrets():
    """生产环境不能使用默认开发密钥。"""
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url=DEFAULT_DATABASE_URL,
            neo4j_password=DEFAULT_NEO4J_PASSWORD,
            jwt_secret=DEFAULT_JWT_SECRET,
            _env_file=None,
        )


def test_development_allows_default_secrets():
    """开发环境允许默认值，保证本地快速启动。"""
    settings = Settings(environment="development", _env_file=None)

    assert settings.environment == "development"


def test_production_rejects_documented_weak_jwt_secret():
    """生产环境不能使用文档或 compose 中的弱示例 JWT 密钥。"""
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://edumind:strong_password@db:5432/edumind",
            neo4j_password="strong-neo4j-password",
            jwt_secret="edumind-dev-secret-change-in-production",
            _env_file=None,
        )
