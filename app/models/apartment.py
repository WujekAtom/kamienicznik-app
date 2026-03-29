from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Apartment(Base, TimestampMixin):
    __tablename__ = "apartments"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    has_water = Column(Boolean, default=True)
    has_electricity = Column(Boolean, default=True)
    has_gas = Column(Boolean, default=False)
    has_trash = Column(Boolean, default=True)
    has_heating = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    tenants = relationship("Tenant", back_populates="apartment", cascade="all, delete-orphan", lazy="selectin")
    meter_readings = relationship("MeterReading", back_populates="apartment", lazy="selectin")
    billing_periods = relationship("BillingPeriod", back_populates="apartment", lazy="selectin")

    utility_rates = relationship("UtilityRate", back_populates="apartment",
                                 foreign_keys="UtilityRate.apartment_id", lazy="selectin")
    electricity_components = relationship("ElectricityComponents", back_populates="apartment",
                                          foreign_keys="ElectricityComponents.apartment_id", lazy="selectin")
    gas_components = relationship("GasComponents", back_populates="apartment",
                                  foreign_keys="GasComponents.apartment_id", lazy="selectin")