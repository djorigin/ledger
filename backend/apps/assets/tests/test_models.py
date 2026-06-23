from datetime import date
from decimal import Decimal

import pytest

from apps.assets.models import AssetCategory, AssetClass, AssetValuation
from apps.entities.models import Entity, EntityType
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def test_latest_valuation_returns_none_when_no_valuations_exist():
    entity = make_entity()
    user = make_user()
    asset = AssetClass.objects.create(
        entity=entity, name="Mount Gambier House", category=AssetCategory.PROPERTY,
        currency="AUD", created_by=user,
    )
    assert asset.latest_valuation is None


def test_latest_valuation_returns_most_recent_by_date():
    entity = make_entity()
    user = make_user()
    asset = AssetClass.objects.create(
        entity=entity, name="Mount Gambier House", category=AssetCategory.PROPERTY,
        currency="AUD", created_by=user,
    )
    older = AssetValuation.objects.create(
        asset=asset, valuation_date=date(2025, 1, 1), current_value=Decimal("450000"),
        currency="AUD", created_by=user,
    )
    newer = AssetValuation.objects.create(
        asset=asset, valuation_date=date(2026, 1, 1), current_value=Decimal("480000"),
        currency="AUD", created_by=user,
    )
    assert asset.latest_valuation == newer
    assert asset.latest_valuation != older
