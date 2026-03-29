from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .utility_rate import UtilityType
from sqlalchemy import Enum as SAEnum

class MeterReading(Base, TimestampMixin):
    __tablename__ = "meter_readings"
    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=False)
    utility_type = Column(SAEnum(UtilityType), nullable=False)
    reading_date = Column(Date, nullable=False)
    reading_value = Column(Numeric(12, 3), nullable=False)
    consumption = Column(Numeric(12, 3), nullable=True)
    previous_reading_id = Column(Integer, ForeignKey("meter_readings.id"), nullable=True)
    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    photo_path = Column(String(500), nullable=True)
    photo_verified = Column(Boolean, default=False)
    photo_verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    photo_verified_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    apartment = relationship("Apartment", back_populates="meter_readings", lazy="selectin")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id], lazy="selectin")
    photo_verified_by = relationship("User", foreign_keys=[photo_verified_by_id], lazy="selectin")
    previous_reading = relationship("MeterReading", remote_side="MeterReading.id", lazy="selectin")
