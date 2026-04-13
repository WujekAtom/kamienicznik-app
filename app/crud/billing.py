from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.crud.apartments import get_apartment
from app.crud.meter_readings import get_readings_for_apartment
from app.crud.tenants import get_active_tenant_for_apartment
from app.models.billing import BillingPeriod, BillingItem, BillingStatus
from app.models.payment import Payment
from app.models.meter_reading import MeterReading
from decimal import Decimal
from datetime import date
from typing import Tuple, List, Optional
from app.crud.utility_rates import get_current_rate
from app.models.utility_rate import UtilityType
from app.crud.utility_components import get_current_gas, get_current_electricity


async def get_billing_periods_for_apartment(db: AsyncSession, apt_id: int):
    result = await db.execute(
        select(BillingPeriod)
        .where(BillingPeriod.apartment_id == apt_id)
        .options(selectinload(BillingPeriod.items), selectinload(BillingPeriod.payments))
        .order_by(BillingPeriod.period_start.desc())
    )
    return result.scalars().all()


async def get_billing_period(db: AsyncSession, bp_id: int) -> BillingPeriod | None:
    result = await db.execute(
        select(BillingPeriod)
        .where(BillingPeriod.id == bp_id)
        .options(
            selectinload(BillingPeriod.items),
            selectinload(BillingPeriod.payments).selectinload(Payment.registered_by),
            selectinload(BillingPeriod.apartment),
        )
    )
    return result.scalar_one_or_none()


async def create_billing_period(db: AsyncSession, apt_id: int, period_start: date,
                                 period_end: date, rent_amount: Decimal,
                                 due_date: date, notes: str = None) -> BillingPeriod:
    bp = BillingPeriod(
        apartment_id=apt_id,
        period_start=period_start,
        period_end=period_end,
        rent_amount=rent_amount,
        total_utilities=Decimal("0"),
        total_amount=rent_amount,
        amount_paid=Decimal("0"),
        status=BillingStatus.draft,
        due_date=due_date,
        notes=notes,
    )
    db.add(bp)
    await db.flush()
    return bp


async def add_billing_item(db: AsyncSession, bp_id: int, item_type: str, description: str,
                            total_price: Decimal, quantity=None, unit_price=None,
                            reading_from_id=None, reading_to_id=None) -> BillingItem:
    item = BillingItem(
        billing_period_id=bp_id,
        item_type=item_type,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        reading_from_id=reading_from_id,
        reading_to_id=reading_to_id,
    )
    db.add(item)
    await db.flush()
    return item


async def recalculate_billing_totals(db: AsyncSession, bp: BillingPeriod):
    # Explicitly load items and payments from DB — never rely on lazy load in async
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
    elif bp.status == BillingStatus.draft:
        pass  # keep draft
    await db.flush()


async def create_billing_for_apartment_and_period(
    db: AsyncSession,
    apartment_id: int,
    period_from: date,
    period_to: date,
    due_to: date,
    notes: str | None = None,
) -> Tuple[Optional[BillingPeriod], List[str]]:

    missing: List[str] = []

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

    if missing:
        return None, missing

    apt = await get_apartment(db, apartment_id)
    if not apt:
        missing.append("brak apartamentu")
        return None, missing
    tenant = await get_active_tenant_for_apartment(db, apartment_id)
    rent = tenant.rent_amount if tenant else Decimal("0")

    bp = await create_billing_period(db, apartment_id, period_from, period_to, rent, due_to, notes or None)

    # Czynsz
    await add_billing_item(db, bp.id, "rent", "Czynsz podstawowy", rent)

    # Media
    all_readings = await get_readings_for_apartment(db, apartment_id, limit=200)

    def get_readings(ut):
        in_p = [r for r in all_readings if r.utility_type == ut and period_from <= r.reading_date <= period_to]
        bef_p = [r for r in all_readings if r.utility_type == ut and r.reading_date < period_from]
        if not in_p or not bef_p:
            return None, None, None
        r_to = max(in_p, key=lambda r: r.reading_date)
        r_from = max(bef_p, key=lambda r: r.reading_date)
        cons = r_to.reading_value - r_from.reading_value
        if cons <= 0:
            return None, None, None
        return r_from, r_to, cons

    # --- WODA ---
    if apt.has_water:
        water_rate = await get_current_rate(db, UtilityType.water, period_to, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.water)
        if water_rate and cons is not None:
            usage_cost = (cons * water_rate.rate_per_unit).quantize(Decimal("0.01"))
            adv = (tenant.water_advance.quantize(Decimal("0.01"))
                   if tenant and tenant.water_advance and tenant.water_advance > 0
                   else Decimal("0.00"))
            net_water = (usage_cost - adv).quantize(Decimal("0.01"))
            if adv > 0:
                desc = (f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
                        f" = {float(usage_cost):.2f} zł − zaliczka {float(adv):.2f} zł"
                        f" = {float(net_water):.2f} zł")
            else:
                desc = f"Woda: {float(cons):.3f} m³ × {float(water_rate.rate_per_unit):.4f} zł/m³"
            await add_billing_item(db, bp.id, "water", desc, net_water,
                                   quantity=cons, unit_price=water_rate.rate_per_unit,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)
            if adv > 0:
                desc_adv = (f"Zaliczka na przyszły miesiąc: {float(adv):.2f} zł")
                await add_billing_item(db, bp.id, "water", desc_adv, adv)


    # --- PRĄD (składowe z faktury) ---
    if apt.has_electricity:
        elec = await get_current_electricity(db, period_to, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.electricity)
        if elec and cons is not None:
            kwh = cons
            # Sprzedaż energii
            var_total = (kwh * elec.var_rate).quantize(Decimal("0.01"))
            fixed_sale = (elec.extra_trade_cycle + elec.fixed_price).quantize(Decimal("0.01"))
            sale_total = (var_total + fixed_sale).quantize(Decimal("0.01"))
            # Dystrybucja
            dist_var = (kwh * (elec.quality_rate + elec.dist_variable + elec.oze_rate + elec.cogen_rate)).quantize(Decimal("0.01"))
            dist_fixed = (elec.dist_fixed + elec.transition_fee + elec.abonament + elec.power_fee).quantize(Decimal("0.01"))
            dist_total = (dist_var + dist_fixed).quantize(Decimal("0.01"))
            elec_total = (sale_total + dist_total).quantize(Decimal("0.01"))
            vat = (elec_total * 23 / Decimal("100")).quantize(Decimal("0.01"))
            elec_total_vat = (elec_total + vat).quantize(Decimal("0.01"))
            desc = (f"Prąd: {float(kwh):.3f} kWh | "
                    f"sprzedaż: {float(sale_total):.2f} zł, dystr.: {float(dist_total):.2f} zł + VAT 23%: {float(vat):.2f} zł")
            await add_billing_item(db, bp.id, "electricity", desc, elec_total_vat,
                                   quantity=kwh, unit_price=None,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- GAZ (składowe z faktury) ---
    if apt.has_gas:
        gas = await get_current_gas(db, period_to, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.gas)
        if gas and cons is not None:
            m3 = cons
            kwh_gas = (m3 * gas.conv_factor).quantize(Decimal("0.000001"))
            fuel_netto = (kwh_gas * gas.gas_price_per_kwh).quantize(Decimal("0.01"))
            dist_var = (kwh_gas * gas.dist_variable).quantize(Decimal("0.01"))
            netto = (fuel_netto + gas.dist_fixed + gas.abonament + dist_var).quantize(Decimal("0.01"))
            vat = (netto * gas.vat_pct / Decimal("100")).quantize(Decimal("0.01"))
            gas_total = (netto + vat).quantize(Decimal("0.01"))
            desc = (f"Gaz: {float(m3):.3f} m³ → {float(kwh_gas):.1f} kWh | "
                    f"netto: {float(netto):.2f} zł + VAT {float(gas.vat_pct):.0f}%: {float(vat):.2f} zł")
            await add_billing_item(db, bp.id, "gas", desc, gas_total,
                                   quantity=m3, unit_price=None,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- OGRZEWANIE (prosta stawka) ---
    if apt.has_heating:
        heat_rate = await get_current_rate(db, UtilityType.heating, period_to, apartment_id=apt.id)
        r_from, r_to, cons = get_readings(UtilityType.heating)
        if heat_rate and cons is not None:
            total = (cons * heat_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc = f"Ogrzewanie: {float(cons):.3f} GJ × {float(heat_rate.rate_per_unit):.4f} zł/GJ"
            await add_billing_item(db, bp.id, "heating", desc, total,
                                   quantity=cons, unit_price=heat_rate.rate_per_unit,
                                   reading_from_id=r_from.id, reading_to_id=r_to.id)

    # --- ŚMIECI (stawka × liczba osób) ---
    if apt.has_trash and tenant:
        trash_rate = await get_current_rate(db, UtilityType.trash, period_to, apartment_id=apt.id)
        if trash_rate:
            occupants = tenant.occupants or 1
            trash_total = (Decimal(str(occupants)) * trash_rate.rate_per_unit).quantize(Decimal("0.01"))
            desc = f"Śmieci: {occupants} os. × {float(trash_rate.rate_per_unit):.2f} zł/os."
            await add_billing_item(db, bp.id, "trash", desc, trash_total,
                                   quantity=Decimal(str(occupants)),
                                   unit_price=trash_rate.rate_per_unit)

    # --- CZYNSZ DO WSPÓLNOTY ( zł / miesiąc) ---

    community_rate = await get_current_rate(db, UtilityType.community_fee, period_to, apartment_id=apt.id)
    if community_rate:
        total = community_rate.rate_per_unit.quantize(Decimal("0.01"))
        desc = f"Czynsz do wspólnoty: {float(community_rate.rate_per_unit):.2f} zł/mies."
        await add_billing_item(db, bp.id, "community_fee", desc, total, quantity=Decimal("1.00"), unit_price=community_rate.rate_per_unit)


    await recalculate_billing_totals(db, bp)

    await db.flush()

    return bp, []