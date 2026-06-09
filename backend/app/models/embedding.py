"""嵌入向量模型 —— pgvector 存储"""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.core.config import settings
from app.core.database import Base


class NodeEmbedding(Base):
    """知识点文本嵌入向量 — 用于语义搜索"""

    __tablename__ = "node_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(255), nullable=False, index=True)
    path_id = Column(String(36), nullable=False, index=True)
    content_text = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    dimensions = Column(Integer, nullable=False)
    embedding = Column(Vector(settings.embedding_dim))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (UniqueConstraint("node_id", "model_name", name="uq_node_model"),)
