"""初始化 Neo4j 约束和索引"""

from app.core.database import get_neo4j_driver


async def init_neo4j():
    """初始化 Neo4j 约束"""
    driver = await get_neo4j_driver()
    async with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:KnowledgeNode) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE (m.name, m.path_id) IS NODE KEY",
        ]
        for cql in constraints:
            await session.run(cql)
            print(f"  ✅ {cql[:60]}...")

    print("🎉 Neo4j 初始化完成")


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_neo4j())
