from decimal import Decimal

from sqlalchemy import select
from app.crud.utility_advance import UtilityAdvance, get_utility_advances_for_apartment
from app.models.utility_advance import UtilityAdvance
from app.models.billing import BillingPeriod
from app.models.billing import BillingItem

async def build_billing_items(
    db,
    apartment_id: int,
    period_start,
    period_end,
    readings_by_type: dict,   # {UtilityType: (consumption, rate, unit_label)}
) -> tuple[list[BillingItem], Decimal, str]:
    """
    Zwraca (lista pozycji, total_utilities, billing_mode).
    billing_mode = 'full' jeśli brak zaliczek,
                 = 'diff' jeśli choć jedno medium ma tryb advance/fixed.
    """

    # Pobierz konfigurację zaliczek dla lokalu
    # result = await db.execute(
    #     select(UtilityAdvance).where(UtilityAdvance.apartment_id == apartment_id)
    # )

    result = await get_utility_advances_for_apartment(db, apartment_id)

    advances = {a.utility_type: a for a in result}

    items = []
    total_utilities = Decimal("0.00")
    has_advance_mode = False

    for utility_type, (consumption, rate, unit_label) in readings_by_type.items():
        adv = advances.get(utility_type)
        mode = adv.billing_mode if adv else "direct"
        advance_amount = Decimal(str(adv.advance_amount)) if adv else Decimal("0")
        fixed_amount = Decimal(str(adv.fixed_amount)) if adv else Decimal("0")

        usage_cost = Decimal(str(consumption)) * Decimal(str(rate))

        if mode == "direct":
            # Pełna kwota za zużycie
            item = BillingItem(
                item_type=utility_type,
                description=f"{utility_type} — {consumption} {unit_label} × {rate} zł",
                quantity=consumption,
                unit_price=rate,
                total_price=usage_cost,
                is_advance_settlement=False,
            )
            total_utilities += usage_cost

        elif mode == "advance":
            # Tylko różnica: zużycie - zaliczka
            diff = usage_cost - advance_amount
            has_advance_mode = True
            item = BillingItem(
                item_type=utility_type,
                description=(
                    f"{utility_type} — zużycie {consumption} {unit_label} × {rate} zł"
                    f" = {usage_cost:.2f} zł, zaliczka {advance_amount:.2f} zł, "
                    f"{'dopłata' if diff >= 0 else 'zwrot'}: {abs(diff):.2f} zł"
                ),
                quantity=consumption,
                unit_price=rate,
                total_price=diff,          # ujemna = nadpłata (zwrot)
                advance_amount=advance_amount,
                is_advance_settlement=True,
            )
            total_utilities += diff

        elif mode == "fixed":
            # Stała kwota, brak rozliczenia z licznikiem
            has_advance_mode = True
            item = BillingItem(
                item_type=utility_type,
                description=f"{utility_type} — ryczałt {fixed_amount:.2f} zł",
                quantity=None,
                unit_price=None,
                total_price=fixed_amount,
                is_advance_settlement=False,
            )
            total_utilities += fixed_amount

        items.append(item)

    billing_mode = "diff" if has_advance_mode else "full"
    return items, total_utilities, billing_mode