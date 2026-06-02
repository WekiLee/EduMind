"""用户模型"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Boolean
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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
