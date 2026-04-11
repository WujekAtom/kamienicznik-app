from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum as SAEnum, Numeric, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class ContractType(str, enum.Enum):
    fixed = "fixed"
    indefinite = "indefinite"

class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    id_number = Column(String(100), nullable=True)
    contract_start = Column(Date, nullable=False)
    contract_end = Column(Date, nullable=True)
    contract_type = Column(SAEnum(ContractType), default=ContractType.indefinite, nullable=False)
    payment_due_day = Column(Integer, default=10, nullable=False)
    rent_amount = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    occupants = Column(Integer, default=1, nullable=False)
    # water_advance = Column(Numeric(10, 2), nullable=False, default=0)  # zaliczka na wodę zł/mies.
    notes = Column(String(1000), nullable=True)
    apartment = relationship("Apartment", back_populates="tenants", lazy="selectin")
    user = relationship("User", back_populates="tenant", foreign_keys="User.tenant_id", uselist=False, lazy="selectin")
