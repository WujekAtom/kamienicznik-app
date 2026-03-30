from sqlalchemy import Column, Integer, String, Date, Numeric, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class UtilityType(str, enum.Enum):
    water = "water"
    electricity = "electricity"
    gas = "gas"
    trash = "trash"
    heating = "heating"
    community_fee = "community_fee"

class UtilityRate(Base, TimestampMixin):
    __tablename__ = "utility_rates"
    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=True)
    utility_type = Column(SAEnum(UtilityType), nullable=False)
    rate_per_unit = Column(Numeric(10, 4), nullable=False)
    unit_label = Column(String(20), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    apartment = relationship(
        "Apartment",
        back_populates="utility_rates",
        foreign_keys=[apartment_id],
        lazy="selectin",
    )