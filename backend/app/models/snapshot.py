"""掌握度快照模型 —— 趋势分析用"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String

from app.core.database import Base


class MasterySnapshot(Base):
    """掌握度快照 —— 记录每次测验/完成后的掌握度快照，用于趋势分析"""

    __tablename__ = "mastery_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(String(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot = Column(JSON, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_ms_path_time", "path_id", "recorded_at"),
    )

