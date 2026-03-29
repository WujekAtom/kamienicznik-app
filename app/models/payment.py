from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class PaymentType(str, enum.Enum):
    cash = "cash"
    transfer = "transfer"
    mixed = "mixed"

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    billing_period_id = Column(Integer, ForeignKey("billing_periods.id", ondelete="CASCADE"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_type = Column(SAEnum(PaymentType), nullable=False)
    cash_amount = Column(Numeric(10, 2), nullable=True)
    transfer_amount = Column(Numeric(10, 2), nullable=True)
    reference_number = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    registered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    billing_period = relationship("BillingPeriod", back_populates="payments", lazy="selectin")
    registered_by = relationship("User", foreign_keys=[registered_by_id], lazy="selectin")
