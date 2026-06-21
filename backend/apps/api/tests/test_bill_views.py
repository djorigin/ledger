import pytest

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.models import Account, AccountType

pytestmark = pytest.mark.django_db


def _make_payable_account(entity):
    return Account.objects.create(
        entity=entity, account_type=AccountType.LIABILITY, name="Accounts Payable", native_currency="AUD"
    )


def _bill_payload(entity, expense_account, payable_account):
    return {
        "entity": str(entity.id),
        "vendor_name": "Acme",
        "description": "January invoice",
        "bill_date": "2026-01-01",
        "due_date": "2026-01-31",
        "amount": "200.00",
        "currency": "AUD",
        "expense_account": str(expense_account.id),
        "payable_account": str(payable_account.id),
    }


def test_viewer_cannot_create_bill():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json")
    assert response.status_code == 403


def test_editor_can_create_bill():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    response = client.post("/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json")
    assert response.status_code == 201
    assert response.data["amount"] == "200.0000"
    assert response.data["journal_entry"] is not None


def test_cross_entity_bill_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(other_entity)
    payable = _make_payable_account(other_entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/bills/", _bill_payload(other_entity, groceries, payable), format="json"
    )
    assert response.status_code == 403


def test_viewer_can_list_and_read_payments_but_not_record_one():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    editor_client = authenticated_client(user)
    bill_id = editor_client.post(
        "/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json"
    ).data["id"]

    viewer = make_user("viewer@example.com")
    make_membership(viewer, entity, EntityRole.VIEWER)
    viewer_client = authenticated_client(viewer)

    get_resp = viewer_client.get(f"/api/v1/bills/{bill_id}/payments/")
    assert get_resp.status_code == 200

    post_resp = viewer_client.post(
        f"/api/v1/bills/{bill_id}/payments/",
        {"payment_date": "2026-01-10", "amount": "50.00", "payment_account": str(bank.id)},
        format="json",
    )
    assert post_resp.status_code == 403


def test_record_payment_and_progress_endpoint():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    bill_id = client.post(
        "/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json"
    ).data["id"]

    payment_resp = client.post(
        f"/api/v1/bills/{bill_id}/payments/",
        {"payment_date": "2026-01-10", "amount": "80.00", "payment_account": str(bank.id)},
        format="json",
    )
    assert payment_resp.status_code == 201

    progress = client.get(f"/api/v1/bills/{bill_id}/progress/")
    assert progress.status_code == 200
    assert progress.data["amount_paid"] == "80.0000"
    assert progress.data["amount_due"] == "120.0000"
    assert progress.data["status"] == "PARTIALLY_PAID"


def test_overpayment_rejected_with_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    bill_id = client.post(
        "/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json"
    ).data["id"]

    response = client.post(
        f"/api/v1/bills/{bill_id}/payments/",
        {"payment_date": "2026-01-10", "amount": "999.00", "payment_account": str(bank.id)},
        format="json",
    )
    assert response.status_code == 400


def test_cancel_unpaid_bill_succeeds_and_paid_bill_rejected():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    bill_id = client.post(
        "/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json"
    ).data["id"]

    client.post(
        f"/api/v1/bills/{bill_id}/payments/",
        {"payment_date": "2026-01-10", "amount": "50.00", "payment_account": str(bank.id)},
        format="json",
    )
    rejected = client.post(f"/api/v1/bills/{bill_id}/cancel/")
    assert rejected.status_code == 400

    other_bill_id = client.post(
        "/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json"
    ).data["id"]
    accepted = client.post(f"/api/v1/bills/{other_bill_id}/cancel/")
    assert accepted.status_code == 200
    assert accepted.data["is_cancelled"] is True


def test_bill_visible_in_trial_balance_report_without_new_reporting_code():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    payable = _make_payable_account(entity)

    client = authenticated_client(user)
    client.post("/api/v1/bills/", _bill_payload(entity, groceries, payable), format="json")

    response = client.get(f"/api/v1/reports/trial-balance/?entity={entity.id}&as_of=2026-01-31")
    assert response.status_code == 200
    aud_group = next(g for g in response.data["currency_groups"] if g["currency"] == "AUD")
    payable_row = next(r for r in aud_group["rows"] if r["account_name"] == "Accounts Payable")
    assert payable_row["credit_balance"] == "200.0000"
