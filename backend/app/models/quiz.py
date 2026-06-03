"""测验相关模型"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(String(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    answers = Column(JSON, default=list)  # [{"question_id": "...", "selected": "A", "correct": true}]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(String(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
