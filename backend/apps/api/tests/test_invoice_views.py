import pytest

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.models import Account, AccountType

pytestmark = pytest.mark.django_db


def _make_ar_accounts(entity):
    income = Account.objects.create(
        entity=entity, account_type=AccountType.INCOME, name="Consulting Income", native_currency="AUD"
    )
    receivable = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Accounts Receivable", native_currency="AUD"
    )
    return income, receivable


def _invoice_payload(entity, income_account, receivable_account):
    return {
        "entity": str(entity.id),
        "customer_name": "Bob",
        "description": "Consulting",
        "invoice_date": "2026-01-01",
        "due_date": "2026-01-31",
        "amount": "500.00",
        "currency": "AUD",
        "income_account": str(income_account.id),
        "receivable_account": str(receivable_account.id),
    }


def test_viewer_cannot_create_invoice():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    income, receivable = _make_ar_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    )
    assert response.status_code == 403


def test_editor_can_create_invoice():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    income, receivable = _make_ar_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    )
    assert response.status_code == 201
    assert response.data["amount"] == "500.0000"


def test_record_payment_and_progress_endpoint():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    income, receivable = _make_ar_accounts(entity)

    client = authenticated_client(user)
    invoice_id = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    ).data["id"]

    payment_resp = client.post(
        f"/api/v1/invoices/{invoice_id}/payments/",
        {"payment_date": "2026-01-15", "amount": "500.00", "payment_account": str(bank.id)},
        format="json",
    )
    assert payment_resp.status_code == 201

    progress = client.get(f"/api/v1/invoices/{invoice_id}/progress/")
    assert progress.status_code == 200
    assert progress.data["status"] == "PAID"
    assert progress.data["amount_due"] == "0.0000"


def test_overpayment_rejected_with_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    income, receivable = _make_ar_accounts(entity)

    client = authenticated_client(user)
    invoice_id = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    ).data["id"]

    response = client.post(
        f"/api/v1/invoices/{invoice_id}/payments/",
        {"payment_date": "2026-01-15", "amount": "501.00", "payment_account": str(bank.id)},
        format="json",
    )
    assert response.status_code == 400


def test_cancel_unpaid_invoice_succeeds_and_paid_invoice_rejected():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    income, receivable = _make_ar_accounts(entity)

    client = authenticated_client(user)
    invoice_id = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    ).data["id"]

    client.post(
        f"/api/v1/invoices/{invoice_id}/payments/",
        {"payment_date": "2026-01-15", "amount": "100.00", "payment_account": str(bank.id)},
        format="json",
    )
    rejected = client.post(f"/api/v1/invoices/{invoice_id}/cancel/")
    assert rejected.status_code == 400

    other_invoice_id = client.post(
        "/api/v1/invoices/", _invoice_payload(entity, income, receivable), format="json"
    ).data["id"]
    accepted = client.post(f"/api/v1/invoices/{other_invoice_id}/cancel/")
    assert accepted.status_code == 200
    assert accepted.data["is_cancelled"] is True


def test_cross_entity_invoice_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)
    income, receivable = _make_ar_accounts(other_entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/invoices/", _invoice_payload(other_entity, income, receivable), format="json"
    )
    assert response.status_code == 403
