"""FastAPI 主应用"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, analytics, assessment, auth, learning_paths, nodes, progress, quiz, search, users
from app.api.progress import path_progress_router
from app.core.config import settings
from app.core.database import (
    Base,
    async_session_factory,
    close_neo4j,
    close_redis,
    engine,
    ensure_schema_compatibility,
    init_pgvector,
)
from app.llm.adapter import LLMAdapter
from app.ws import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化 pgvector 扩展（必须在建表前）
    try:
        await init_pgvector()
    except Exception as e:
        print(f"  ⚠️  pgvector 扩展初始化跳过: {e}")

    # 启动时创建数据库表（开发环境自动迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 兼容历史数据库结构（项目当前未引入 Alembic）
    try:
        await ensure_schema_compatibility()
    except Exception as e:
        print(f"  ⚠️  数据库兼容修复跳过: {e}")

    # 启动时确保内置管理员账号存在
    try:
        from app.scripts.ensure_admin import ensure_admin

        await ensure_admin()
    except Exception as e:
        print(f"  ⚠️  内置管理员初始化跳过: {e}")

    # 确保系统配置存在（管理员已存在但配置表为空的情况）
    try:
        from sqlalchemy import select

        from app.models.system_config import SystemConfig

        async with async_session_factory() as session:
            cfg = await session.execute(select(SystemConfig).limit(1))
            if not cfg.scalar_one_or_none():
                from app.models.user import User

                admin_user = await session.execute(select(User).where(User.role == "admin").limit(1))
                admin = admin_user.scalar_one_or_none()
                if admin:
                    session.add(SystemConfig(updated_by=admin.id))
                    await session.commit()
                    print("  ✅ 已补充默认系统配置")
    except Exception as e:
        print(f"  ⚠️  补充系统配置跳过: {e}")

    # 启动时加载管理员保存的 LLM 配置
    try:
        from sqlalchemy import select

        from app.models.system_config import SystemConfig

        async with async_session_factory() as session:
            result = await session.execute(select(SystemConfig).limit(1))
            config = result.scalar_one_or_none()
            if config:
                LLMAdapter.update_runtime_config(
                    provider=config.llm_provider,
                    model=config.llm_model,
                    api_key=config.llm_api_key,
                    api_base=config.llm_api_base,
                )
                print(f"  ✅ 已加载系统 LLM 配置: {config.llm_provider}/{config.llm_model}")
    except Exception as e:
        print(f"  ⚠️  加载 LLM 配置失败（首次运行正常）: {e}")

    yield
    # 关闭连接
    await close_neo4j()
    await close_redis()


app = FastAPI(
    title="EduMind API",
    description="智能导师系统后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(learning_paths.router, prefix="/api/v1")
app.include_router(nodes.router, prefix="/api/v1")
app.include_router(progress.router, prefix="/api/v1")
app.include_router(path_progress_router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(assessment.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

# 兼容用户审查清单中的短路径，核心业务仍推荐使用 /api/v1 前缀。
app.include_router(assessment.router)
app.include_router(analytics.router)


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
