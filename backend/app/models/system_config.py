"""系统配置模型 —— LLM 平台等全局设置"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String, Text

from app.core.database import Base


class SystemConfig(Base):
    """系统级配置，全局只有一条记录"""

    __tablename__ = "system_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    llm_provider = Column(String(50), nullable=False, default="openai-compatible")
    llm_model = Column(String(100), nullable=False, default="deepseek-v4-flash")
    llm_api_key = Column(Text, nullable=True)  # 管理员配置的 API Key
    llm_api_base = Column(String(500), nullable=True, default="https://api.deepseek.com/v1")
    allow_self_register = Column(JSON, default=True)  # 是否允许用户自助注册
    updated_by = Column(String(36), nullable=True)  # 最后修改的管理员 ID
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict:
        # 返回配置时不暴露 API Key
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_base": self.llm_api_base,
            "allow_self_register": self.allow_self_register,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
