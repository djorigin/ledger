from decimal import Decimal

import pytest

from apps.entities.models import Entity, EntityType
from apps.inventory.models import InventoryCategory, InventoryItem
from apps.inventory.services import compute_inventory_summary
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def test_summary_groups_by_category():
    entity = make_entity()
    user = make_user()
    InventoryItem.objects.create(
        entity=entity, name="Sony A7IV", category=InventoryCategory.ELECTRONICS,
        estimated_replacement_value=Decimal("4500"), currency="AUD", created_by=user,
    )
    InventoryItem.objects.create(
        entity=entity, name="Drone", category=InventoryCategory.ELECTRONICS,
        estimated_replacement_value=Decimal("2500"), currency="AUD", created_by=user,
    )
    InventoryItem.objects.create(
        entity=entity, name="Sofa", category=InventoryCategory.FURNITURE,
        estimated_replacement_value=Decimal("1200"), currency="AUD", created_by=user,
    )

    summary = compute_inventory_summary(entity)
    by_category = {row.category: row for row in summary}
    assert by_category["ELECTRONICS"].total_replacement_value == Decimal("7000")
    assert by_category["ELECTRONICS"].item_count == 2
    assert by_category["FURNITURE"].total_replacement_value == Decimal("1200")
    assert by_category["FURNITURE"].item_count == 1


def test_summary_excludes_inactive_items():
    entity = make_entity()
    user = make_user()
    InventoryItem.objects.create(
        entity=entity, name="Old laptop", category=InventoryCategory.ELECTRONICS,
        estimated_replacement_value=Decimal("500"), currency="AUD", is_active=False, created_by=user,
    )

    summary = compute_inventory_summary(entity)
    assert summary == []


def test_summary_handles_null_replacement_value():
    entity = make_entity()
    user = make_user()
    InventoryItem.objects.create(
        entity=entity, name="Unvalued item", category=InventoryCategory.OTHER,
        currency="AUD", created_by=user,
    )

    summary = compute_inventory_summary(entity)
    assert summary[0].total_replacement_value == Decimal("0")
    assert summary[0].item_count == 1
