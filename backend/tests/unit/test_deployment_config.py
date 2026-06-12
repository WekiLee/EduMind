"""部署配置安全回归测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_prod_compose_enables_production_secret_guards():
    """生产服务必须启用生产环境校验并要求显式传入密钥。"""
    compose = ROOT / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "ENVIRONMENT: production" in content
    assert "DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://edumind:${POSTGRES_PASSWORD:" in content
    assert "NEO4J_PASSWORD: ${NEO4J_PASSWORD:?production NEO4J_PASSWORD is required}" in content
    assert "JWT_SECRET: ${JWT_SECRET:?production JWT_SECRET is required}" in content


def test_compose_rejects_default_postgres_password():
    """Compose 不能为 PostgreSQL 继续保留开发默认密码。"""
    compose = ROOT / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" in content
    assert "POSTGRES_PASSWORD:-edumind_dev" not in content
    assert "postgresql+asyncpg://edumind:edumind_dev@postgres" not in content


def test_deploy_script_uses_root_env_and_dev_profile():
    """一键部署脚本必须为 Compose 准备根环境变量并启用 dev profile。"""
    content = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert "ensure_root_env_var \"POSTGRES_PASSWORD\"" in content
    assert "ensure_root_env_var \"NEO4J_PASSWORD\"" in content
    assert "ensure_root_env_var \"JWT_SECRET\"" in content
    assert "docker compose --profile dev up -d" in content
    assert "docker compose up -d 2>/dev/null" not in content


def test_makefile_docker_targets_use_profiles():
    """Makefile 的 Docker 入口必须显式使用 dev/prod profile。"""
    content = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker compose --profile dev up -d" in content
    assert "docker compose --profile prod up -d" in content


def test_ci_runs_compose_config_validator():
    """CI 必须执行 Compose 安全配置校验。"""
    content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python scripts/validate_compose_config.py" in content


def test_windows_setup_script_uses_existing_compose_contract():
    """Windows 初始化脚本不能依赖不存在的样例文件或旧服务列表。"""
    content = (ROOT / "scripts" / "setup.bat").read_text(encoding="utf-8")

    assert "backend\\.env.example" not in content
    assert "POSTGRES_PASSWORD=edumind_dev" in content
    assert "docker compose up -d postgres neo4j redis" in content
    assert "ollama" not in content


def test_native_deploy_script_does_not_hardcode_database_passwords():
    """原生部署脚本不能继续写死数据库和 Neo4j 默认密码。"""
    content = (ROOT / "scripts" / "deploy-native.sh").read_text(encoding="utf-8")

    assert "BACKEND_ENV=" in content
    assert ". \"$BACKEND_ENV\"" in content
    assert "WITH PASSWORD 'edumind_dev'" not in content
    assert "set-initial-password edumind_dev" not in content
    assert "NEO4J_PASSWORD=edumind_dev" not in content
    assert "postgresql+asyncpg://edumind:edumind_dev@localhost" not in content
