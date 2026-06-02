"""节点进度模型"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, ForeignKey, UniqueConstraint
from app.core.database import Base


class NodeProgress(Base):
    __tablename__ = "node_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(String(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String(255), nullable=False)  # Neo4j 节点 ID
    status = Column(String(20), nullable=False, default="not_started")  # not_started | learning | completed | reviewing
    mastery = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    quiz_scores = Column(JSON, default=list)
    first_learned = Column(DateTime(timezone=True), nullable=True)
    last_reviewed = Column(DateTime(timezone=True), nullable=True)
    next_review = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "path_id", "node_id", name="uq_user_path_node"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "status": self.status,
            "mastery": self.mastery,
            "attempt_count": self.attempt_count,
            "first_learned": self.first_learned.isoformat() if self.first_learned else None,
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
            "next_review": self.next_review.isoformat() if self.next_review else None,
        }
