"""创建 EduMind 初始数据库结构。"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "20260612_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级到当前应用使用的初始 schema。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=True),
        sa.Column("organization", sa.String(length=200), nullable=True),
        sa.Column("domain_id", sa.String(length=50), nullable=True),
        sa.Column("learner_profile", sa.JSON(), nullable=True),
        sa.Column("model_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=500), nullable=False),
        sa.Column("domain_id", sa.String(length=50), nullable=False),
        sa.Column("syllabus", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("learner_profile_override", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_paths_user_id"), "learning_paths", ["user_id"], unique=False)

    op.create_table(
        "system_config",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("llm_provider", sa.String(length=50), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=False),
        sa.Column("llm_api_key", sa.Text(), nullable=True),
        sa.Column("llm_api_base", sa.String(length=500), nullable=True),
        sa.Column("allow_self_register", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "node_progress",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("path_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("quiz_scores", sa.JSON(), nullable=True),
        sa.Column("first_learned", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "path_id", "node_id", name="uq_user_path_node"),
    )
    op.create_index(op.f("ix_node_progress_path_id"), "node_progress", ["path_id"], unique=False)
    op.create_index(op.f("ix_node_progress_user_id"), "node_progress", ["user_id"], unique=False)

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("path_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"], unique=False)

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("path_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"], unique=False)

    op.create_table(
        "mastery_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("path_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ms_path_time", "mastery_snapshots", ["path_id", "recorded_at"], unique=False)
    op.create_index(op.f("ix_mastery_snapshots_path_id"), "mastery_snapshots", ["path_id"], unique=False)
    op.create_index(op.f("ix_mastery_snapshots_user_id"), "mastery_snapshots", ["user_id"], unique=False)

    op.create_table(
        "node_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("path_id", sa.String(length=36), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path_id", "node_id", "model_name", name="uq_path_node_model"),
    )
    op.create_index(op.f("ix_node_embeddings_node_id"), "node_embeddings", ["node_id"], unique=False)
    op.create_index(op.f("ix_node_embeddings_path_id"), "node_embeddings", ["path_id"], unique=False)


def downgrade() -> None:
    """回滚初始 schema。"""
    op.drop_index(op.f("ix_node_embeddings_path_id"), table_name="node_embeddings")
    op.drop_index(op.f("ix_node_embeddings_node_id"), table_name="node_embeddings")
    op.drop_table("node_embeddings")
    op.drop_index(op.f("ix_mastery_snapshots_user_id"), table_name="mastery_snapshots")
    op.drop_index(op.f("ix_mastery_snapshots_path_id"), table_name="mastery_snapshots")
    op.drop_index("idx_ms_path_time", table_name="mastery_snapshots")
    op.drop_table("mastery_snapshots")
    op.drop_index(op.f("ix_chat_messages_session_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index(op.f("ix_quiz_attempts_user_id"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index(op.f("ix_node_progress_user_id"), table_name="node_progress")
    op.drop_index(op.f("ix_node_progress_path_id"), table_name="node_progress")
    op.drop_table("node_progress")
    op.drop_table("system_config")
    op.drop_index(op.f("ix_learning_paths_user_id"), table_name="learning_paths")
    op.drop_table("learning_paths")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
