from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _budget_payload(entity, account):
    return {
        "entity": str(entity.id),
        "account": str(account.id),
        "period_type": "MONTHLY",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "budgeted_amount": "200.00",
    }


def test_viewer_cannot_create_budget():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    _, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/budgets/", _budget_payload(entity, groceries), format="json")
    assert response.status_code == 403


def test_editor_can_create_budget():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    _, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/budgets/", _budget_payload(entity, groceries), format="json")
    assert response.status_code == 201


def test_budget_progress_endpoint_returns_actual_and_remaining():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    create = client.post("/api/v1/budgets/", _budget_payload(entity, groceries), format="json")
    response = client.get(f"/api/v1/budgets/{create.data['id']}/progress/")

    assert response.status_code == 200
    assert response.data["actual_amount"] == "60.0000"
    assert response.data["remaining_amount"] == "140.0000"


def test_list_budgets_filtered_to_accessible_entities():
    user = make_user()
    accessible_entity = make_entity("Mine")
    inaccessible_entity = make_entity("Other")
    make_membership(user, accessible_entity, EntityRole.EDITOR)
    _, mine_groceries = make_accounts(accessible_entity)
    other_user = make_user(email="other@example.com")
    make_membership(other_user, inaccessible_entity, EntityRole.EDITOR)
    _, other_groceries = make_accounts(inaccessible_entity)

    other_client = authenticated_client(other_user)
    other_client.post(
        "/api/v1/budgets/", _budget_payload(inaccessible_entity, other_groceries), format="json"
    )

    client = authenticated_client(user)
    client.post("/api/v1/budgets/", _budget_payload(accessible_entity, mine_groceries), format="json")
    response = client.get("/api/v1/budgets/")
    assert response.data["count"] == 1


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/budgets/")
    assert response.status_code == 401
