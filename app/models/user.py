from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    tenant = "tenant"

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.tenant, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    magic_link_token = Column(String(255), nullable=True, unique=True, index=True)
    magic_link_expires = Column(DateTime(timezone=True), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    tenant = relationship("Tenant", back_populates="user", foreign_keys=[tenant_id], lazy="selectin")
    reset_token = Column(String(255), nullable=True, unique=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
