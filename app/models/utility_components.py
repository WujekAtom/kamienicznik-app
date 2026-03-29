from sqlalchemy import Column, Integer, String, Date, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ElectricityComponents(Base, TimestampMixin):
    """Składowe ceny prądu — aktualizowane co miesiąc z faktury"""
    __tablename__ = "electricity_components"
    id = Column(Integer, primary_key=True, index=True)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=True)

    # === SPRZEDAŻ ENERGII ===
    # Stawka zmienna (zł/kWh * zużycie)
    var_rate = Column(Numeric(10, 6), nullable=False, default=0)          # stawka zmienna całodobowa
    # Stałe miesięczne (zł/mies.)
    extra_trade_cycle = Column(Numeric(10, 4), nullable=False, default=0)  # opłata za dodatkowy cykl handlowy
    fixed_price = Column(Numeric(10, 4), nullable=False, default=0)        # stawka stała ceny

    # === DYSTRYBUCJA ===
    # Stałe miesięczne (zł/mies.)
    dist_fixed = Column(Numeric(10, 4), nullable=False, default=0)         # składnik stały stawki sieciowej
    transition_fee = Column(Numeric(10, 6), nullable=False, default=0)     # stawka opłaty przejściowej (zł/mies.)
    abonament = Column(Numeric(10, 4), nullable=False, default=0)          # opłata abonamentowa
    power_fee = Column(Numeric(10, 4), nullable=False, default=0)          # opłata mocowa

    # Zmienne (zł/kWh * zużycie)
    quality_rate = Column(Numeric(10, 6), nullable=False, default=0)       # stawka jakościowa
    dist_variable = Column(Numeric(10, 6), nullable=False, default=0)      # składnik zmienny stawki sieciowej
    oze_rate = Column(Numeric(10, 6), nullable=False, default=0)           # opłata OZE
    cogen_rate = Column(Numeric(10, 6), nullable=False, default=0)         # opłata kogeneracyjna

    apartment = relationship(
        "Apartment",
        back_populates="electricity_components",
        foreign_keys=[apartment_id],
        lazy="selectin",
    )

class GasComponents(Base, TimestampMixin):
    """Składowe ceny gazu — aktualizowane z faktury"""
    __tablename__ = "gas_components"
    id = Column(Integer, primary_key=True, index=True)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), nullable=True)

    # Stałe miesięczne (zł/mies.)
    abonament = Column(Numeric(10, 4), nullable=False, default=0)          # opłata abonamentowa

    # Przelicznik m³ → kWh (różny dla różnych lokalizacji)
    conv_factor = Column(Numeric(10, 6), nullable=False, default=11.0)     # współczynnik konwersji

    # Paliwo gazowe
    gas_price_per_kwh = Column(Numeric(10, 6), nullable=False, default=0)  # cena za kWh paliwa
    vat_pct = Column(Numeric(5, 2), nullable=False, default=23)            # VAT %

    # Dystrybucja
    dist_fixed = Column(Numeric(10, 4), nullable=False, default=0)         # dystrybucyjna stała (zł/mies.)
    dist_variable = Column(Numeric(10, 6), nullable=False, default=0)      # dystrybucyjna zmienna (zł/kWh)

    apartment = relationship(
        "Apartment",
        back_populates="gas_components",
        foreign_keys=[apartment_id],
        lazy="selectin",
    )