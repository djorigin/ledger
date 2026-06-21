from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.api.tests.helpers import make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _post_graphql(query, user=None, variables=None):
    client = APIClient()
    headers = {}
    if user is not None:
        token = str(RefreshToken.for_user(user).access_token)
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    body = {"query": query}
    if variables is not None:
        body["variables"] = variables
    return client.post("/graphql/", body, format="json", **headers)


def test_me_query_returns_authenticated_user():
    user = make_user("alice@example.com")
    response = _post_graphql("{ me { email } }", user=user)
    assert response.status_code == 200
    assert response.json()["data"]["me"]["email"] == "alice@example.com"


def test_unauthenticated_request_returns_error_not_data():
    response = _post_graphql("{ me { email } }")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] is None
    assert "Authentication required" in body["errors"][0]["message"]


def test_entities_only_returns_accessible_entities():
    user_a = make_user("a@example.com")
    user_b = make_user("b@example.com")
    entity_a = make_entity("Household A")
    entity_b = make_entity("Household B")
    make_membership(user_a, entity_a, EntityRole.VIEWER)
    make_membership(user_b, entity_b, EntityRole.VIEWER)

    response = _post_graphql("{ entities { name } }", user=user_a)
    names = {e["name"] for e in response.json()["data"]["entities"]}
    assert names == {"Household A"}


def test_accounts_filtered_by_entity_and_access():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    make_accounts(other_entity)

    response = _post_graphql(
        '{ accounts(entity: "%s") { name nativeCurrency } }' % entity.id, user=user
    )
    names = {a["name"] for a in response.json()["data"]["accounts"]}
    assert names == {"Bank", "Groceries"}


def test_no_membership_user_sees_no_accounts_for_that_entity():
    user = make_user()
    entity = make_entity()
    make_accounts(entity)
    # deliberately no membership

    response = _post_graphql('{ accounts(entity: "%s") { name } }' % entity.id, user=user)
    assert response.json()["data"]["accounts"] == []


def test_journal_entries_money_fields_serialize_as_strings():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )

    response = _post_graphql(
        '{ journalEntries(entity: "%s") { description lines { debitAmount creditAmount } } }'
        % entity.id,
        user=user,
    )
    data = response.json()["data"]["journalEntries"]
    assert len(data) == 1
    amounts = {line["debitAmount"] for line in data[0]["lines"]} | {
        line["creditAmount"] for line in data[0]["lines"]
    }
    assert all(isinstance(a, str) for a in amounts)
    assert "50.0000" in amounts


def test_budgets_query_scoped_by_entity():
    from apps.budgets.models import Budget, BudgetPeriodType

    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("500"), created_by=user,
    )

    response = _post_graphql('{ budgets(entity: "%s") { budgetedAmount } }' % entity.id, user=user)
    data = response.json()["data"]["budgets"]
    assert len(data) == 1
    assert data[0]["budgetedAmount"] == "500.0000"
