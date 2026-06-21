from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _goal_payload(entity, account):
    return {
        "entity": str(entity.id),
        "name": "House deposit",
        "target_amount": "50000.00",
        "target_date": "2030-03-01",
        "linked_account": str(account.id),
    }


def test_viewer_cannot_create_savings_goal():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/savings-goals/", _goal_payload(entity, bank), format="json")
    assert response.status_code == 403


def test_editor_can_create_savings_goal():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/savings-goals/", _goal_payload(entity, bank), format="json")
    assert response.status_code == 201


def test_savings_goal_progress_endpoint_returns_current_balance_and_days_remaining():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Deposit",
        debit_account=bank, credit_account=groceries, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    create = client.post("/api/v1/savings-goals/", _goal_payload(entity, bank), format="json")
    response = client.get(f"/api/v1/savings-goals/{create.data['id']}/progress/")

    assert response.status_code == 200
    assert response.data["current_balance"] == "1000.0000"
    assert response.data["days_remaining"] > 365 * 3


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/savings-goals/")
    assert response.status_code == 401
