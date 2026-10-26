from decimal import Decimal

from modules.elm.domain.constants import (
    DEFAULT_ENTITLEMENTS,
    EL,
    LEAVE_CATEGORIES,
    VL,
)
from modules.elm.models import EmployeeLeaveBalance


def get_user_balances(
    user_id: int,
    year: int,
    employee_kind: str,
) -> list[EmployeeLeaveBalance]:
    target_year = year
    balance_by_category = {
        balance.leave_category: balance
        for balance in EmployeeLeaveBalance.objects.filter(
            user_id=user_id,
            year=target_year,
        )
    }
    missing_categories = set(LEAVE_CATEGORIES) - balance_by_category.keys()
    if not missing_categories:
        return [balance_by_category[category] for category in LEAVE_CATEGORIES]

    if employee_kind not in {"faculty", "staff"}:
        raise ValueError("ELM balances can only be initialized for faculty or staff.")

    entitlements = dict(DEFAULT_ENTITLEMENTS)
    if employee_kind == "faculty":
        entitlements[EL] = Decimal("0.0")
    else:
        entitlements[VL] = Decimal("0.0")

    for category in missing_categories:
        balance, _ = EmployeeLeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=target_year,
            leave_category=category,
            defaults={
                "allocated_days": entitlements[category],
                "availed_days": Decimal("0.0"),
                "carried_forward": Decimal("0.0"),
                "pending_days": Decimal("0.0"),
            },
        )
        balance_by_category[category] = balance
    return [balance_by_category[category] for category in LEAVE_CATEGORIES]
