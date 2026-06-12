"""数据库连接管理 —— PostgreSQL (SQLAlchemy async) + Neo4j + Redis"""

from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── PostgreSQL ──

engine = create_async_engine(settings.database_url, echo=False, pool_size=10)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_pgvector():
    """初始化 pgvector 扩展"""
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: sync_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector")))


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    """检查 public schema 中的数据表是否存在。"""
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def _column_type(conn: AsyncConnection, table_name: str, column_name: str) -> str | None:
    """读取指定列的数据类型，不存在时返回 None。"""
    result = await conn.execute(
        text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    value = result.scalar()
    return str(value) if value else None


async def _ensure_allow_self_register_boolean(conn: AsyncConnection) -> None:
    """兼容旧库：将 allow_self_register 从 JSON/Text 收敛为 Boolean。"""
    if not await _table_exists(conn, "system_config"):
        return

    column_type = await _column_type(conn, "system_config", "allow_self_register")
    if not column_type:
        return

    if column_type != "boolean":
        await conn.execute(text("ALTER TABLE system_config ALTER COLUMN allow_self_register DROP DEFAULT"))
        await conn.execute(
            text(
                """
                ALTER TABLE system_config
                ALTER COLUMN allow_self_register TYPE boolean
                USING CASE
                    WHEN allow_self_register IS NULL THEN TRUE
                    WHEN lower(allow_self_register::text) IN ('true', '"true"', '1', '"1"') THEN TRUE
                    WHEN lower(allow_self_register::text) IN ('false', '"false"', '0', '"0"') THEN FALSE
                    ELSE TRUE
                END
                """
            )
        )

    await conn.execute(text("UPDATE system_config SET allow_self_register = TRUE WHERE allow_self_register IS NULL"))
    await conn.execute(text("ALTER TABLE system_config ALTER COLUMN allow_self_register SET DEFAULT TRUE"))
    await conn.execute(text("ALTER TABLE system_config ALTER COLUMN allow_self_register SET NOT NULL"))


async def _ensure_node_embeddings_schema(conn: AsyncConnection) -> None:
    """兼容旧库：补齐 node_embeddings 路径维度约束与外键。"""
    if not await _table_exists(conn, "node_embeddings"):
        return

    await conn.execute(text("ALTER TABLE node_embeddings ADD COLUMN IF NOT EXISTS path_id VARCHAR(36)"))
    await conn.execute(text("DELETE FROM node_embeddings WHERE path_id IS NULL OR path_id = ''"))

    if await _table_exists(conn, "learning_paths"):
        await conn.execute(
            text(
                """
                DELETE FROM node_embeddings ne
                WHERE NOT EXISTS (
                    SELECT 1 FROM learning_paths lp WHERE lp.id = ne.path_id
                )
                """
            )
        )

    await conn.execute(
        text(
            """
            DELETE FROM node_embeddings newer
            USING node_embeddings older
            WHERE newer.id > older.id
              AND newer.path_id = older.path_id
              AND newer.node_id = older.node_id
              AND newer.model_name = older.model_name
            """
        )
    )
    await conn.execute(text("ALTER TABLE node_embeddings ALTER COLUMN path_id SET NOT NULL"))
    await conn.execute(text("ALTER TABLE node_embeddings DROP CONSTRAINT IF EXISTS uq_node_model"))
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'node_embeddings'::regclass
                      AND conname = 'uq_path_node_model'
                ) THEN
                    ALTER TABLE node_embeddings
                    ADD CONSTRAINT uq_path_node_model UNIQUE (path_id, node_id, model_name);
                END IF;
            END $$;
            """
        )
    )

    if await _table_exists(conn, "learning_paths"):
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conrelid = 'node_embeddings'::regclass
                          AND contype = 'f'
                          AND pg_get_constraintdef(oid) LIKE '%FOREIGN KEY (path_id)%REFERENCES%learning_paths%'
                    ) THEN
                        ALTER TABLE node_embeddings
                        ADD CONSTRAINT fk_node_embeddings_path_id
                        FOREIGN KEY (path_id) REFERENCES learning_paths(id) ON DELETE CASCADE;
                    END IF;
                END $$;
                """
            )
        )


async def ensure_schema_compatibility() -> None:
    """开发/演示环境启动期兼容旧数据库结构；生产环境应使用 Alembic。"""
    if engine.dialect.name != "postgresql":
        return

    async with engine.begin() as conn:
        await _ensure_allow_self_register_boolean(conn)
        await _ensure_node_embeddings_schema(conn)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Neo4j ──

neo4j_driver = None


async def get_neo4j_driver():
    """获取 Neo4j 驱动（单例）"""
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return neo4j_driver


async def close_neo4j():
    """关闭 Neo4j 连接"""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None


# ── Redis ──

redis_client: Redis | None = None


async def get_redis() -> Redis:
    """获取 Redis 客户端（单例）"""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
