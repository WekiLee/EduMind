"""语义搜索服务 —— pgvector 向量相似度查询 + 嵌入存储"""

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.embedding import NodeEmbedding
from app.services.embedding import EmbeddingService
from app.services.knowledge_graph import KnowledgeGraphService


class SemanticSearchService:
    """语义搜索：管理内容嵌入 + 向量相似度搜索"""

    def __init__(self):
        self.embedder = EmbeddingService()

    async def index_node(self, db: AsyncSession, node_id: str, path_id: str, text: str):
        """为节点生成并存储嵌入向量"""
        vec = await self.embedder.embed(text)
        if vec is None:
            return

        # 删除旧嵌入（同一节点、同一模型）
        await db.execute(
            NodeEmbedding.__table__.delete().where(
                NodeEmbedding.node_id == node_id,
                NodeEmbedding.model_name == self.embedder.model_name,
            )
        )

        embedding = NodeEmbedding(
            node_id=node_id,
            path_id=path_id,
            content_text=text[:2000],
            model_name=self.embedder.model_name,
            dimensions=self.embedder.dimensions,
            embedding=vec,
        )
        db.add(embedding)
        await db.flush()

    async def search(self, db: AsyncSession, query: str, path_id: str | None = None, top_k: int = 5) -> list[dict]:
        """语义搜索：将查询文本转为向量后做相似度搜索"""
        query_vec = await self.embedder.embed(query)
        if query_vec is None:
            return []

        # 构建余弦距离查询 (pgvector 的 <=> 操作符)
        vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"
        where_clause = f"model_name = '{self.embedder.model_name}'"
        if path_id:
            where_clause += f" AND path_id = '{path_id}'"

        sql = f"""
            SELECT node_id, path_id, content_text, model_name,
                   1 - (embedding <=> '{vec_str}') AS similarity
            FROM node_embeddings
            WHERE {where_clause}
            ORDER BY similarity DESC
            LIMIT {top_k}
        """
        results = await db.execute(sa_text(sql))
        rows = results.all()

        # 补充节点标题
        kg = KnowledgeGraphService()
        output = []
        for row in rows:
            node_id = row[0]
            node = await kg.get_node(node_id)
            title = node.get("title", node_id[:16]) if node else node_id[:16]
            output.append({
                "node_id": node_id,
                "path_id": row[1],
                "title": title,
                "snippet": row[2][:200],
                "similarity": round(float(row[4]), 4),
            })
        return output

    async def delete_node_embeddings(self, db: AsyncSession, node_id: str):
        """删除节点的所有嵌入"""
        await db.execute(
            NodeEmbedding.__table__.delete().where(NodeEmbedding.node_id == node_id)
        )
        await db.flush()

    async def delete_path_embeddings(self, db: AsyncSession, path_id: str):
        """删除路径的所有嵌入"""
        await db.execute(
            NodeEmbedding.__table__.delete().where(NodeEmbedding.path_id == path_id)
        )
        await db.flush()
