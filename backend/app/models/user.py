"""用户模型"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # admin | user
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)  # 首次登录/管理员重置后需改密码
    organization = Column(String(200), nullable=True)
    domain_id = Column(String(50), default="general")
    learner_profile = Column(JSON, default=dict)
    model_config = Column(JSON, nullable=True)  # 用户级 LLM 配置: {provider, model, api_base, api_key}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    @staticmethod
    def _public_model_config(model_config: dict | None) -> dict | None:
        """返回脱敏后的用户级模型配置。"""
        if not model_config:
            return None
        public_config = {k: v for k, v in model_config.items() if k != "api_key"}
        api_key = model_config.get("api_key")
        if api_key:
            public_config["api_key_masked"] = api_key[:6] + "****" + api_key[-4:] if len(api_key) > 12 else "****"
        return public_config

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "must_change_password": self.must_change_password,
            "organization": self.organization,
            "domain_id": self.domain_id,
            "learner_profile": self.learner_profile,
            "model_config": self._public_model_config(self.model_config),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

