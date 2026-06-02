"""Seed 测试数据 —— Python 入门学习路径"""

import asyncio
from app.core.database import async_session_factory, get_neo4j_driver
from app.services.content_pipeline import ContentPipelineService


async def seed():
    """插入测试数据"""
    async with async_session_factory() as db:
        # 先创建测试用户（如果不存在）
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == "test@example.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name="测试用户",
                email="test@example.com",
                password_hash=hash_password("123456"),
                learner_profile={
                    "abstraction_level": 0.5,
                    "analogy_density": 0.5,
                    "teaching_speed": 0.5,
                    "feedback_tone": 0.5,
                    "quiz_style": 0.5,
                },
            )
            db.add(user)
            await db.flush()
            print(f"  ✅ 创建用户: {user.name} ({user.email})")

        # 创建学习路径
        pipeline = ContentPipelineService(db)
        path = await pipeline.process_topic(user.id, "Python 入门", "programming")
        print(f"  ✅ 创建学习路径: {path.topic} (id={path.id})")
        print(f"     📋 大纲: {len(path.syllabus)} 个模块")

        # 列出节点
        from app.services.knowledge_graph import KnowledgeGraphService
        kg = KnowledgeGraphService()
        nodes = await kg.get_path_nodes(path.id)
        print(f"     📝 节点数: {len(nodes)}")

    print("🎉 测试数据导入完成")
    print()
    print("  登录邮箱: test@example.com")
    print("  登录密码: 123456")


if __name__ == "__main__":
    asyncio.run(seed())
