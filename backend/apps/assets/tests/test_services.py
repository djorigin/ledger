from datetime import date
from decimal import Decimal

import pytest

from apps.assets.models import AssetCategory, AssetClass, AssetValuation
from apps.assets.services import compute_asset_register_net_worth
from apps.currencies.models import ExchangeRate
from apps.entities.models import Entity, EntityType
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def test_net_worth_uses_latest_valuation_when_present():
    entity = make_entity()
    user = make_user()
    asset = AssetClass.objects.create(
        entity=entity, name="House", category=AssetCategory.PROPERTY,
        acquisition_date=date(2020, 1, 1), acquisition_cost=Decimal("400000"),
        currency="AUD", created_by=user,
    )
    AssetValuation.objects.create(
        asset=asset, valuation_date=date(2026, 1, 1), current_value=Decimal("480000"),
        currency="AUD", created_by=user,
    )

    report = compute_asset_register_net_worth([entity], reporting_currency="AUD")
    assert report.total == Decimal("480000")
    assert report.rows[0].as_of == date(2026, 1, 1)


def test_net_worth_falls_back_to_acquisition_cost_when_no_valuation():
    entity = make_entity()
    user = make_user()
    AssetClass.objects.create(
        entity=entity, name="Car", category=AssetCategory.VEHICLE,
        acquisition_date=date(2024, 6, 1), acquisition_cost=Decimal("25000"),
        currency="AUD", created_by=user,
    )

    report = compute_asset_register_net_worth([entity], reporting_currency="AUD")
    assert report.total == Decimal("25000")
    assert report.rows[0].as_of == date(2024, 6, 1)


def test_asset_with_no_valuation_and_no_acquisition_cost_contributes_nothing():
    entity = make_entity()
    user = make_user()
    AssetClass.objects.create(
        entity=entity, name="Mystery item", category=AssetCategory.OTHER,
        currency="AUD", created_by=user,
    )

    report = compute_asset_register_net_worth([entity], reporting_currency="AUD")
    assert report.total == Decimal("0")
    assert report.rows == []


def test_inactive_asset_excluded():
    entity = make_entity()
    user = make_user()
    asset = AssetClass.objects.create(
        entity=entity, name="Old boat", category=AssetCategory.OTHER,
        acquisition_date=date(2020, 1, 1), acquisition_cost=Decimal("5000"),
        currency="AUD", is_active=False, created_by=user,
    )
    AssetValuation.objects.create(
        asset=asset, valuation_date=date(2026, 1, 1), current_value=Decimal("1000"),
        currency="AUD", created_by=user,
    )

    report = compute_asset_register_net_worth([entity], reporting_currency="AUD")
    assert report.total == Decimal("0")


def test_currency_conversion_at_valuation_date_rate():
    entity = make_entity()
    user = make_user()
    asset = AssetClass.objects.create(
        entity=entity, name="China apartment", category=AssetCategory.PROPERTY,
        currency="CNY", created_by=user,
    )
    AssetValuation.objects.create(
        asset=asset, valuation_date=date(2026, 1, 1), current_value=Decimal("1000000"),
        currency="CNY", created_by=user,
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="CNY", to_currency="AUD", rate=Decimal("0.2"),
    )

    report = compute_asset_register_net_worth([entity], reporting_currency="AUD")
    assert report.total == Decimal("200000")


def test_consolidates_across_multiple_entities():
    entity_a = make_entity("Household")
    entity_b = make_entity("Business")
    user = make_user()
    asset_a = AssetClass.objects.create(
        entity=entity_a, name="House", category=AssetCategory.PROPERTY,
        currency="AUD", created_by=user,
    )
    AssetValuation.objects.create(
        asset=asset_a, valuation_date=date(2026, 1, 1), current_value=Decimal("400000"),
        currency="AUD", created_by=user,
    )
    asset_b = AssetClass.objects.create(
        entity=entity_b, name="Equipment", category=AssetCategory.OTHER,
        currency="AUD", created_by=user,
    )
    AssetValuation.objects.create(
        asset=asset_b, valuation_date=date(2026, 1, 1), current_value=Decimal("20000"),
        currency="AUD", created_by=user,
    )

    report = compute_asset_register_net_worth([entity_a, entity_b], reporting_currency="AUD")
    assert report.total == Decimal("420000")
    assert len(report.rows) == 2
