"""学习路径模型"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String

from app.core.database import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    domain_id = Column(String(50), nullable=False, default="general")
    syllabus = Column(JSON, default=list)  # [{"module_name": "...", "order": 1, "node_ids": [...]}]
    status = Column(String(20), nullable=False, default="active")  # processing | active | completed | archived
    source = Column(String(20), default="topic")  # topic | upload | link
    learner_profile_override = Column(JSON, nullable=True)  # 本路径的学习者画像覆盖
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "domain_id": self.domain_id,
            "syllabus": self.syllabus,
            "status": self.status,
            "source": self.source,
            "learner_profile_override": self.learner_profile_override,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

