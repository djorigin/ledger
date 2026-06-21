from datetime import date
from decimal import Decimal

import pytest

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _seed_transaction(entity, bank, groceries, user):
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )


@pytest.mark.parametrize(
    "path_factory",
    [
        lambda entity, bank: f"/api/v1/reports/trial-balance/?entity={entity.id}",
        lambda entity, bank: f"/api/v1/reports/balance-sheet/?entity={entity.id}&reporting_currency=AUD",
        lambda entity, bank: (
            f"/api/v1/reports/income-statement/?entity={entity.id}"
            "&period_start=2026-01-01&period_end=2026-01-31&reporting_currency=AUD"
        ),
        lambda entity, bank: f"/api/v1/reports/account-ledger/?account={bank.id}",
        lambda entity, bank: f"/api/v1/reports/budget-vs-actual/?entity={entity.id}&reporting_currency=AUD",
    ],
)
def test_viewer_can_read_each_report(path_factory):
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    _seed_transaction(entity, bank, groceries, user)

    client = authenticated_client(user)
    response = client.get(path_factory(entity, bank))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path_factory",
    [
        lambda entity, bank: f"/api/v1/reports/trial-balance/?entity={entity.id}",
        lambda entity, bank: f"/api/v1/reports/balance-sheet/?entity={entity.id}&reporting_currency=AUD",
        lambda entity, bank: f"/api/v1/reports/account-ledger/?account={bank.id}",
        lambda entity, bank: f"/api/v1/reports/budget-vs-actual/?entity={entity.id}&reporting_currency=AUD",
    ],
)
def test_no_membership_user_gets_404(path_factory):
    user = make_user()
    entity = make_entity()
    bank, groceries = make_accounts(entity)
    # deliberately no membership for `user`

    client = authenticated_client(user)
    response = client.get(path_factory(entity, bank))
    assert response.status_code == 404


def test_editor_can_also_read_reports():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.get(f"/api/v1/reports/trial-balance/?entity={entity.id}")
    assert response.status_code == 200


def test_trial_balance_missing_entity_param_returns_400():
    user = make_user()
    client = authenticated_client(user)
    response = client.get("/api/v1/reports/trial-balance/")
    assert response.status_code == 400


def test_balance_sheet_missing_reporting_currency_returns_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    client = authenticated_client(user)
    response = client.get(f"/api/v1/reports/balance-sheet/?entity={entity.id}")
    assert response.status_code == 400


def test_balance_sheet_invalid_currency_returns_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    client = authenticated_client(user)
    response = client.get(
        f"/api/v1/reports/balance-sheet/?entity={entity.id}&reporting_currency=XYZ"
    )
    assert response.status_code == 400


def test_trial_balance_response_shape_includes_currency_groups():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    _seed_transaction(entity, bank, groceries, user)

    client = authenticated_client(user)
    response = client.get(f"/api/v1/reports/trial-balance/?entity={entity.id}")
    assert response.status_code == 200
    currencies = {g["currency"] for g in response.data["currency_groups"]}
    assert "AUD" in currencies


def test_account_ledger_no_account_access_returns_404():
    user = make_user()
    entity = make_entity()
    bank, groceries = make_accounts(entity)
    # no membership

    client = authenticated_client(user)
    response = client.get(f"/api/v1/reports/account-ledger/?account={bank.id}")
    assert response.status_code == 404


def test_viewer_can_read_cash_flow():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    bank.is_cash_equivalent = True
    bank.save()
    _seed_transaction(entity, bank, groceries, user)

    client = authenticated_client(user)
    response = client.get(
        f"/api/v1/reports/cash-flow/?entity={entity.id}"
        "&period_start=2026-01-01&period_end=2026-01-31&reporting_currency=AUD"
    )
    assert response.status_code == 200
    assert response.data["reconciles"] is True


def test_no_membership_user_gets_404_for_cash_flow():
    user = make_user()
    entity = make_entity()
    make_accounts(entity)
    # no membership

    client = authenticated_client(user)
    response = client.get(
        f"/api/v1/reports/cash-flow/?entity={entity.id}"
        "&period_start=2026-01-01&period_end=2026-01-31&reporting_currency=AUD"
    )
    assert response.status_code == 404


def test_net_worth_includes_only_accessible_entities():
    user_a = make_user("a@example.com")
    user_b = make_user("b@example.com")
    entity_a = make_entity("Household A")
    entity_b = make_entity("Household B")
    make_membership(user_a, entity_a, EntityRole.VIEWER)
    make_membership(user_b, entity_b, EntityRole.VIEWER)
    make_accounts(entity_a)
    make_accounts(entity_b)

    client = authenticated_client(user_a)
    response = client.get("/api/v1/reports/net-worth/?reporting_currency=AUD")
    assert response.status_code == 200
    entity_ids = {row["entity_id"] for row in response.data["rows"]}
    assert str(entity_a.id) in entity_ids
    assert str(entity_b.id) not in entity_ids


def test_net_worth_missing_reporting_currency_returns_400():
    user = make_user()
    client = authenticated_client(user)
    response = client.get("/api/v1/reports/net-worth/")
    assert response.status_code == 400
