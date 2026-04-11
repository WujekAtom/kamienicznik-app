# app/models/utility_advance.py
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base

class UtilityAdvance(Base):
    __tablename__ = "utility_advances"

    id = Column(Integer, primary_key=True)
    apartment_id  = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False)
    utility_type  = Column(String(30), nullable=False)   # wartość enum UtilityType
    billing_mode  = Column(String(10), nullable=False, default="direct")
    advance_amount = Column(Numeric(10, 2), nullable=False, default=0)
    fixed_amount  = Column(Numeric(10, 2), nullable=False, default=0)

    apartment = relationship("Apartment", back_populates="utility_advances")

    __table_args__ = (
        UniqueConstraint("apartment_id", "utility_type", name="utility_advances_unique"),
    )