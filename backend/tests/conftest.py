"""测试共享 Fixtures — 集成测试"""

import os
from urllib.parse import urlparse

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# 必须在导入 app.core.database 前设置，避免全局 engine 绑定开发库。
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://edumind:edumind_dev@localhost:5432/edumind_test",
)
parsed_test_db = urlparse(TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
test_db_name = parsed_test_db.path.rsplit("/", 1)[-1]
if not test_db_name.endswith("_test"):
    raise RuntimeError("测试数据库名称必须以 _test 结尾，已拒绝执行破坏性测试清理")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.core.database import Base, async_session_factory, engine, init_pgvector  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """为整个 session 提供事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """每个测试前建表，测试后删表"""
    await init_pgvector()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """FastAPI 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """数据库会话"""
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    """注册一个测试用户并返回登录 token 和用户信息"""
    resp = await client.post("/api/v1/auth/register", json={
        "name": "测试用户",
        "email": "test@example.com",
        "password": "123456",
    })
    assert resp.status_code == 201
    # 自动登录
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "123456",
    })
    data = login_resp.json()["data"]
    return {
        "token": data["access_token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }
