import pytest

from apps.entities.models import Entity, EntityType
from apps.inventory.models import InventoryCategory, InventoryItem
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def test_str_includes_category_display():
    entity = make_entity()
    user = make_user()
    item = InventoryItem.objects.create(
        entity=entity, name="Sony A7IV", category=InventoryCategory.ELECTRONICS,
        currency="AUD", created_by=user,
    )
    assert "Sony A7IV" in str(item)
    assert "Electronics" in str(item)
