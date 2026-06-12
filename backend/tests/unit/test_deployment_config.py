"""部署配置安全回归测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_prod_compose_enables_production_secret_guards():
    """生产服务必须启用生产环境校验并要求显式传入密钥。"""
    compose = ROOT / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "ENVIRONMENT: production" in content
    assert "AUTO_MIGRATE_ON_STARTUP: ${AUTO_MIGRATE_ON_STARTUP:-false}" in content
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


def test_compose_uses_shared_neo4j_password_variable():
    """Neo4j 服务与开发后端必须使用同一个密码变量。"""
    content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}" in content
    assert "NEO4J_PASSWORD: ${NEO4J_PASSWORD:-edumind_dev}" in content
    assert "NEO4J_PASSWORD: edumind_dev" not in content


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


def test_backend_env_example_is_trackable():
    """文档引用的 backend/.env.example 必须真实存在且可被 Git 跟踪。"""
    assert (ROOT / "backend" / ".env.example").exists()
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "backend/.env.*" in gitignore
    assert "!backend/.env.example" in gitignore


def test_alembic_migration_chain_exists():
    """生产默认关闭启动期 DDL 后，必须提供可执行的 Alembic 迁移链路。"""
    assert (ROOT / "backend" / "alembic.ini").exists()
    assert (ROOT / "backend" / "alembic" / "env.py").exists()
    versions = list((ROOT / "backend" / "alembic" / "versions").glob("*.py"))
    assert versions
    database_doc = (ROOT / "docs" / "mvp" / "DATABASE.md").read_text(encoding="utf-8")
    assert "当前代码尚未引入 Alembic" not in database_doc


def test_mvp_environment_doc_uses_current_neo4j_contract():
    """MVP 环境文档不能继续展示旧的 Neo4j 硬编码密码。"""
    content = (ROOT / "docs" / "mvp" / "ENVIRONMENT.md").read_text(encoding="utf-8")

    assert "NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}" in content
    assert "NEO4J_AUTH: neo4j/edumind_dev" not in content
    assert "AUTO_MIGRATE_ON_STARTUP: ${AUTO_MIGRATE_ON_STARTUP:-true}" in content


def test_websocket_contract_does_not_put_jwt_in_url():
    """WebSocket 认证令牌不能继续通过 URL query 传递。"""
    frontend_api = (ROOT / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
    api_doc = (ROOT / "docs" / "mvp" / "API.md").read_text(encoding="utf-8")

    assert "/ws/chat?token=" not in frontend_api
    assert "ws://host/api/v1/ws/chat?token=JWT_TOKEN" not in api_doc
    assert "type: 'auth'" in frontend_api
    assert '"type": "auth"' in api_doc


def test_testing_doc_uses_current_neo4j_contract():
    """测试文档中的 Neo4j 示例也必须跟随当前密码变量契约。"""
    content = (ROOT / "docs" / "mvp" / "TESTING.md").read_text(encoding="utf-8")

    assert "NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}" in content
    assert "NEO4J_AUTH: neo4j/edumind_dev" not in content


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
