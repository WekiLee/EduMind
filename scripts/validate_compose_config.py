"""校验 Docker Compose 中的最低安全配置。

该脚本不依赖 Docker，适合作为 CI 的快速预检；有 Docker 的环境仍应继续执行
`docker compose --profile prod config` 验证最终展开结果。
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"


def require(condition: bool, message: str) -> None:
    """断言配置满足要求，失败时给出明确错误。"""
    if not condition:
        raise SystemExit(f"Compose 配置校验失败：{message}")


def main() -> None:
    content = COMPOSE_FILE.read_text(encoding="utf-8")

    require(
        "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" in content,
        "PostgreSQL 密码必须通过 POSTGRES_PASSWORD 显式传入",
    )
    require(
        "POSTGRES_PASSWORD:-edumind_dev" not in content,
        "PostgreSQL 不能继续保留 edumind_dev 默认密码",
    )
    require(
        "postgresql+asyncpg://edumind:edumind_dev@postgres" not in content,
        "后端连接串不能继续硬编码开发数据库密码",
    )
    require(
        "NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-edumind_dev}" in content,
        "Neo4j 服务必须通过 NEO4J_PASSWORD 变量配置开发密码",
    )
    require(
        "NEO4J_PASSWORD: ${NEO4J_PASSWORD:-edumind_dev}" in content,
        "开发后端必须与 Neo4j 服务使用同一个 NEO4J_PASSWORD 变量",
    )
    require(
        "NEO4J_PASSWORD: edumind_dev" not in content,
        "开发后端不能继续硬编码 Neo4j 默认密码",
    )
    require(
        "ENVIRONMENT: production" in content,
        "生产后端必须显式设置 ENVIRONMENT=production",
    )
    require(
        "AUTO_MIGRATE_ON_STARTUP: ${AUTO_MIGRATE_ON_STARTUP:-false}" in content,
        "生产后端默认必须关闭启动期自动 DDL",
    )
    require(
        "JWT_SECRET: ${JWT_SECRET:?production JWT_SECRET is required}" in content,
        "生产后端必须强制要求 JWT_SECRET",
    )
    require(
        "NEO4J_PASSWORD: ${NEO4J_PASSWORD:?production NEO4J_PASSWORD is required}" in content,
        "生产后端必须强制要求 NEO4J_PASSWORD",
    )

    print("Compose 配置校验通过")


if __name__ == "__main__":
    main()
