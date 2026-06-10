"""部署配置安全回归测试。"""

from pathlib import Path


def test_prod_compose_enables_production_secret_guards():
    """生产服务必须启用生产环境校验并要求显式传入密钥。"""
    compose = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "ENVIRONMENT: production" in content
    assert "DATABASE_URL: ${DATABASE_URL:?production DATABASE_URL is required}" in content
    assert "NEO4J_PASSWORD: ${NEO4J_PASSWORD:?production NEO4J_PASSWORD is required}" in content
    assert "JWT_SECRET: ${JWT_SECRET:?production JWT_SECRET is required}" in content

