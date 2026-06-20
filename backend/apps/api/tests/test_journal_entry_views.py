from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import (
    authenticated_client,
    make_accounts,
    make_entity,
    make_membership,
    make_user,
)
from apps.entities.models import Entity, EntityRole, EntityType
from apps.ledger.models import Account, AccountType, JournalEntry, JournalEntryStatus
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _entry_payload(bank, groceries, debit=Decimal("50.00"), credit=Decimal("50.00")):
    return {
        "entity": str(bank.entity_id),
        "entry_date": "2026-01-01",
        "description": "Groceries",
        "lines": [
            {"account": str(groceries.id), "currency": "AUD", "debit_amount": str(debit)},
            {"account": str(bank.id), "currency": "AUD", "credit_amount": str(credit)},
        ],
    }


def test_viewer_cannot_create_journal_entry():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/journal-entries/", _entry_payload(bank, groceries), format="json"
    )
    assert response.status_code == 403


def test_editor_can_create_journal_entry():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/journal-entries/", _entry_payload(bank, groceries), format="json"
    )

    assert response.status_code == 201
    assert response.data["status"] == "POSTED"
    assert response.data["posted_at"] is not None
    assert len(response.data["lines_detail"]) == 2


def test_owner_can_create_journal_entry():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.OWNER)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/journal-entries/", _entry_payload(bank, groceries), format="json"
    )
    assert response.status_code == 201


def test_create_unbalanced_journal_entry_returns_400_not_500():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/journal-entries/",
        _entry_payload(bank, groceries, debit=Decimal("50.00"), credit=Decimal("40.00")),
        format="json",
    )

    assert response.status_code == 400
    assert "not balanced" in str(response.data).lower()


def test_create_journal_entry_with_cross_entity_account_returns_400():
    user = make_user()
    entity = make_entity()
    other_entity = Entity.objects.create(name="Other", type=EntityType.BUSINESS)
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    other_account = Account.objects.create(
        entity=other_entity, account_type=AccountType.ASSET, name="Other Bank", native_currency="AUD"
    )

    client = authenticated_client(user)
    payload = {
        "entity": str(entity.id),
        "entry_date": "2026-01-01",
        "description": "bad",
        "lines": [
            {"account": str(groceries.id), "currency": "AUD", "debit_amount": "50.00"},
            {"account": str(other_account.id), "currency": "AUD", "credit_amount": "50.00"},
        ],
    }
    response = client.post("/api/v1/journal-entries/", payload, format="json")
    assert response.status_code == 400


def test_create_journal_entry_actually_calls_post_journal_entry():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/journal-entries/", _entry_payload(bank, groceries), format="json"
    )

    assert response.status_code == 201
    entry = JournalEntry.objects.get(pk=response.data["id"])
    assert entry.status == JournalEntryStatus.POSTED
    assert entry.posted_at is not None


def test_list_journal_entries_filtered_to_accessible_entities():
    user = make_user()
    accessible_entity = make_entity("Mine")
    inaccessible_entity = make_entity("Other")
    make_membership(user, accessible_entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(accessible_entity)
    other_bank, other_groceries = make_accounts(inaccessible_entity)

    other_user = make_user(email="other@example.com")
    hidden_entry = record_simple_transaction(
        entity=inaccessible_entity, entry_date=date(2026, 1, 1), description="Hidden",
        debit_account=other_groceries, credit_account=other_bank,
        amount=Decimal("10"), currency="AUD", created_by=other_user,
    )

    client = authenticated_client(user)
    response = client.get("/api/v1/journal-entries/")

    ids = {e["id"] for e in response.data["results"]}
    assert str(hidden_entry.id) not in ids


def test_reverse_action_succeeds_for_editor():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank,
        amount=Decimal("50"), currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    response = client.post(f"/api/v1/journal-entries/{entry.id}/reverse/", {}, format="json")

    assert response.status_code == 201
    assert str(response.data["reverses"]) == str(entry.id)
    entry.refresh_from_db()
    assert entry.status == JournalEntryStatus.REVERSED


def test_reverse_action_blocked_for_viewer():
    user = make_user()
    entity = make_entity()
    owner = make_user(email="owner@example.com")
    make_membership(user, entity, EntityRole.VIEWER)
    make_membership(owner, entity, EntityRole.OWNER)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank,
        amount=Decimal("50"), currency="AUD", created_by=owner,
    )

    client = authenticated_client(user)
    response = client.post(f"/api/v1/journal-entries/{entry.id}/reverse/", {}, format="json")
    assert response.status_code == 403


def test_reverse_already_reversed_entry_returns_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank,
        amount=Decimal("50"), currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    first = client.post(f"/api/v1/journal-entries/{entry.id}/reverse/", {}, format="json")
    assert first.status_code == 201

    second = client.post(f"/api/v1/journal-entries/{entry.id}/reverse/", {}, format="json")
    assert second.status_code == 400


def test_update_journal_entry_returns_405():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank,
        amount=Decimal("50"), currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    assert client.put(f"/api/v1/journal-entries/{entry.id}/", {}, format="json").status_code == 405
    assert client.patch(f"/api/v1/journal-entries/{entry.id}/", {}, format="json").status_code == 405


def test_delete_journal_entry_returns_405():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank,
        amount=Decimal("50"), currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    response = client.delete(f"/api/v1/journal-entries/{entry.id}/")
    assert response.status_code == 405


def test_unauthenticated_request_to_list_returns_401():
    client = APIClient()
    response = client.get("/api/v1/journal-entries/")
    assert response.status_code == 401


def test_unauthenticated_request_to_create_returns_401():
    client = APIClient()
    response = client.post("/api/v1/journal-entries/", {}, format="json")
    assert response.status_code == 401
