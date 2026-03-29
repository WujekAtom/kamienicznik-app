from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class BillingStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    overdue = "overdue"

class BillingPeriod(Base, TimestampMixin):
    __tablename__ = "billing_periods"
    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    rent_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_utilities = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(SAEnum(BillingStatus), default=BillingStatus.draft, nullable=False)
    due_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    apartment = relationship("Apartment", back_populates="billing_periods", lazy="selectin")
    items = relationship("BillingItem", back_populates="billing_period", cascade="all, delete-orphan", lazy="selectin")
    payments = relationship("Payment", back_populates="billing_period", cascade="all, delete-orphan", lazy="selectin")

class BillingItem(Base, TimestampMixin):
    __tablename__ = "billing_items"
    id = Column(Integer, primary_key=True, index=True)
    billing_period_id = Column(Integer, ForeignKey("billing_periods.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(50), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=True)
    unit_price = Column(Numeric(10, 4), nullable=True)
    total_price = Column(Numeric(10, 2), nullable=False)
    reading_from_id = Column(Integer, ForeignKey("meter_readings.id"), nullable=True)
    reading_to_id = Column(Integer, ForeignKey("meter_readings.id"), nullable=True)
    billing_period = relationship("BillingPeriod", back_populates="items", lazy="selectin")
