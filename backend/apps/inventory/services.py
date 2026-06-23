from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import InventoryItem


@dataclass(frozen=True)
class InventoryCategorySummary:
    category: str
    total_replacement_value: Decimal
    item_count: int


def compute_inventory_summary(entity) -> list[InventoryCategorySummary]:
    """
    Total estimated_replacement_value by category, for one entity --
    deliberately no cross-currency conversion (unlike the asset register):
    insurance schedules are normally read per-currency/per-policy, not
    rolled into one converted figure, so mixing currencies here would
    misrepresent what's actually insured where.
    """
    rows = (
        InventoryItem.objects.filter(entity=entity, is_active=True)
        .values("category")
        .annotate(
            total_replacement_value=Coalesce(Sum("estimated_replacement_value"), Decimal("0")),
            item_count=Count("id"),
        )
        .order_by("category")
    )
    return [
        InventoryCategorySummary(
            category=row["category"],
            total_replacement_value=row["total_replacement_value"],
            item_count=row["item_count"],
        )
        for row in rows
    ]
