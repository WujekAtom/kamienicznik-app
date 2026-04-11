
from decimal import Decimal
from datetime import date
from typing import Tuple, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.billing import BillingPeriod, BillingItem, BillingStatus
from app.models.meter_reading import MeterReading
from app.models.payment import Payment
from app.models.utility_rate import UtilityType

from app.crud import billing_crud as billing_crud
from app.crud.apartments import get_apartment
from app.crud.meter_readings import get_readings_for_apartment
from app.crud.tenants import get_active_tenant_for_apartment
from app.crud.utility_rates import get_current_rate
from app.crud.utility_components import get_current_gas, get_current_electricity


# ---------------------------------------------------------------------------
# Helpers (prywatne)
# ---------------------------------------------------------------------------

def _pick_readings(all_readings, utility_type, period_from: date, period_to: date):
    """
    Zwraca (reading_from, reading_to, consumption) dla danego medium.
    Consumption to różnica odczytów; None jeśli brak danych.
    """
    in_p = [
        r for r in all_readings
        if r.utility_type == utility_type and period_from <= r.reading_date <= period_to
    ]
    bef_p = [
        r for r in all_readings
        if r.utility_type == utility_type and r.reading_date < period_from
    ]
    if not in_p or not bef_p:
        return None, None, None
    r_to = max(in_p, key=lambda r: r.reading_date)
    r_from = max(bef_p, key=lambda r: r.reading_date)
    cons = r_to.reading_value - r_from.reading_value
    if cons <= 0:
        return None, None, None
    return r_from, r_to, cons


# ---------------------------------------------------------------------------
# Publiczne funkcje service
# ---------------------------------------------------------------------------

async def recalculate_totals(db: AsyncSession, bp: BillingPeriod) -> None:
    """
    Przelicza total_utilities, total_amount, amount_paid oraz status rozliczenia.
    Wywołaj po każdej zmianie pozycji lub płatności.
    """
    items_res = await db.execute(
        select(BillingItem).where(BillingItem.billing_period_id == bp.id)
    )
    items = items_res.scalars().all()

    payments_res = await db.execute(
        select(Payment).where(Payment.billing_period_id == bp.id)
    )
    payments = payments_res.scalars().all()

    utility_total = sum(
        item.total_price for item in items if item.item_type != "rent"
    )
    rent_total = sum(
        item.total_price for item in items if item.item_type == "rent"
    )

    bp.total_utilities = utility_total
    bp.rent_amount = rent_total if rent_total > 0 else bp.rent_amount
    bp.total_amount = bp.rent_amount + utility_total
    bp.amount_paid = sum(p.amount for p in payments)

    today = date.today()
    if bp.amount_paid >= bp.total_amount:
        bp.status = BillingStatus.paid
    elif today > bp.due_date and bp.amount_paid < bp.total_amount:
        bp.status = BillingStatus.overdue
    # draft → zostawiamy draft

    await db.flush()


async def generate_billing(
    db: AsyncSession,
    apartment_id: int,
    period_from: date,
    period_to: date,
    due_to: date,
    notes: str | None = None,
) -> Tuple[Optional[BillingPeriod], List[str]]:
    """
    Główna funkcja generowania rozliczenia dla lokalu.

    Kolejność kroków:
    1. Walidacja — czy są odczyty w okresie
    2. Pobierz lokal i lokatora
    3. Utwórz BillingPeriod (draft) w bazie
    4. Dodaj pozycję: czynsz
    5. Dodaj pozycje mediów (woda, prąd, gaz, ogrzewanie, śmieci, wspólnota)
    6. Przelicz sumy i status
    7. Zwróć (billing_period, [])  lub  (None, [lista błędów])
    """

    missing: List[str] = []

    # --- 1. Walidacja: czy są jakiekolwiek odczyty w okresie ---
    readings_result = await db.execute(
        select(MeterReading).where(
            MeterReading.apartment_id == apartment_id,
            MeterReading.reading_date >= period_from,
            MeterReading.reading_date <= period_to,
        )
    )
    readings = readings_result.scalars().all()
    if not readings:
        missing.append("brak odczytów w okresie")
        return None, missing

    # --- 2. Dane lokalu i lokatora ---
    apt = await get_apartment(db, apartment_id)
    if not apt:
        missing.append("brak apartamentu")
        return None, missing

    tenant = await get_active_tenant_for_apartment(db, apartment_id)
    rent = tenant.rent_amount if tenant else Decimal("0")

    # --- 3. Utwórz BillingPeriod ---
    bp = await billing_crud.create_billing_period(
        db, apartment_id, period_from, period_to, rent, due_to, notes or None
    )

    # --- 4. Pozycja: czynsz ---
    await billing_crud.add_billing_item(db, bp.id, "rent", "Czynsz podstawowy", rent)

    # --- 5. Pozycje mediów ---
    all_readings = await get_readings_for_apartment(db, apartment_id, limit=200)

    # WODA
    if apt.has_water:
        water_rate = await get_current_rate(db, UtilityType.water, period_to, apartment_id=apt.id)
        r_from, r_to, cons = _pick_readings(all_readings, UtilityType.water, period_from, period_to)
        if water_rate and cons is not None:
            usage_cost = (cons * water_rate.rate_per_unit).quantize(Decimal("0.01"))
            adv = (
                tenant.water_advance.quantize(Decimal("0.01"))  # to trzeba zmienic
                if tenant and tenant.water_advance and tenant.water_advance > 0
                else Decimal("0.00")
            )
            net_water = (usage_cost - adv).quantize(Decimal("0.01"))
            if adv > 0:
                desc = (
                    f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
                    f" = {float(usage_cost):.2f} zł − zaliczka {float(adv):.2f} zł"
                    f" = {float(net_water):.2f} zł"
                )
            else:
                desc = f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
            await billing_crud.add_billing_item(
                db, bp.id, "water", desc, net_water,
                quantity=cons, unit_price=water_rate.rate_per_unit,
                reading_from_id=r_from.id, reading_to_id=r_to.id,
            )

    # PRĄD
    if apt.has_electricity:
        elec = await get_current_electricity(db, period_to, apartment_id=apt.id)
        r_from, r_to, cons = _pick_readings(all_readings, UtilityType.electricity, period_from, period_to)
        if elec and cons is not None:
            kwh = cons
            var_total   = (kwh * elec.var_rate).quantize(Decimal("0.01"))
            fixed_sale  = (elec.extra_trade_cycle + elec.fixed_price).quantize(Decimal("0.01"))
            sale_total  = (var_total + fixed_sale).quantize(Decimal("0.01"))
            dist_var    = (kwh * (elec.quality_rate + elec.dist_variable + elec.oze_rate + elec.cogen_rate)).quantize(Decimal("0.01"))
            dist_fixed  = (elec.dist_fixed + elec.transition_fee + elec.abonament + elec.power_fee).quantize(Decimal("0.01"))
            dist_total  = (dist_var + dist_fixed).quantize(Decimal("0.01"))
            elec_total  = (sale_total + dist_total).quantize(Decimal("0.01"))
            vat         = (elec_total * 23 / Decimal("100")).quantize(Decimal("0.01"))
            elec_total_vat = (elec_total + vat).quantize(Decimal("0.01"))
            desc = (
                f"Prąd: {float(kwh):.3f} kWh | "
                f"sprzedaż: {float(sale_total):.2f} zł, dystr.: {float(dist_total):.2f} zł"
                f" + VAT 23%: {float(vat):.2f} zł"
            )
            await billing_crud.add_billing_item(
                db, bp.id, "electricity", desc, elec_total_vat,
                quantity=kwh, unit_price=None,
                reading_from_id=r_from.id, reading_to_id=r_to.id,
            )

    # GAZ
    if apt.has_gas:
        gas = await get_current_gas(db, period_to, apartment_id=apt.id)
        r_from, r_to, cons = _pick_readings(all_readings, UtilityType.gas, period_from, period_to)
        if gas and cons is not None:
            m3      = cons
            kwh_gas = (m3 * gas.conv_factor).quantize(Decimal("0.000001"))
            fuel_netto = (kwh_gas * gas.gas_price_per_kwh).quantize(Decimal("0.01"))
            dist_var   = (kwh_gas * gas.dist_variable).quantize(Decimal("0.01"))
            netto      = (fuel_netto + gas.dist_fixed + gas.abonament + dist_var).quantize(Decimal("0.01"))
            vat        = (netto * gas.vat_pct / Decimal("100")).quantize(Decimal("0.01"))
            gas_total  = (netto + vat).quantize(Decimal("0.01"))
            desc = (
                f"Gaz: {float(m3):.3f} m³ → {float(kwh_gas):.1f} kWh | "
                f"netto: {float(netto):.2f} zł + VAT {float(gas.vat_pct):.0f}%: {float(vat):.2f} zł"
            )
            await billing_crud.add_billing_item(
                db, bp.id, "gas", desc, gas_total,
                quantity=m3, unit_price=None,
                reading_from_id=r_from.id, reading_to_id=r_to.id,
            )

    # OGRZEWANIE
    if apt.has_heating:
        heat_rate = await get_current_rate(db, UtilityType.heating, period_to, apartment_id=apt.id)
        r_from, r_to, cons = _pick_readings(all_readings, UtilityType.heating, period_from, period_to)
        if heat_rate and cons is not None:
            total = (cons * heat_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc  = f"Ogrzewanie: {float(cons):.3f} GJ × {float(heat_rate.rate_per_unit):.4f} zł/GJ"
            await billing_crud.add_billing_item(
                db, bp.id, "heating", desc, total,
                quantity=cons, unit_price=heat_rate.rate_per_unit,
                reading_from_id=r_from.id, reading_to_id=r_to.id,
            )

    # ŚMIECI
    if apt.has_trash and tenant:
        trash_rate = await get_current_rate(db, UtilityType.trash, period_to, apartment_id=apt.id)
        if trash_rate:
            occupants   = tenant.occupants or 1
            trash_total = (Decimal(str(occupants)) * trash_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc = f"Śmieci: {occupants} os. × {float(trash_rate.rate_per_unit):.2f} zł/os."
            await billing_crud.add_billing_item(
                db, bp.id, "trash", desc, trash_total,
                quantity=Decimal(str(occupants)),
                unit_price=trash_rate.rate_per_unit,
            )

    # CZYNSZ DO WSPÓLNOTY
    community_rate = await get_current_rate(db, UtilityType.community_fee, period_to, apartment_id=apt.id)
    if community_rate:
        total = community_rate.rate_per_unit.quantize(Decimal("0.01"))
        desc  = f"Czynsz do wspólnoty: {float(community_rate.rate_per_unit):.2f} zł/mies."
        await billing_crud.add_billing_item(
            db, bp.id, "community_fee", desc, total,
            quantity=Decimal("1.00"),
            unit_price=community_rate.rate_per_unit,
        )

    # --- 6. Przelicz sumy ---
    await recalculate_totals(db, bp)
    await db.flush()

    return bp, []