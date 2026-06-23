import pytest

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.ledger.models import Account, AccountType

pytestmark = pytest.mark.django_db


def _make_payroll_accounts(entity, bank):
    def acc(name, account_type):
        return Account.objects.create(
            entity=entity, name=name, account_type=account_type, native_currency="AUD"
        )

    return {
        "income_account": str(acc("KCC Gross", AccountType.INCOME).id),
        "pretax_lease_expense_account": str(acc("Lease", AccountType.EXPENSE).id),
        "tax_expense_account": str(acc("PAYG Withheld", AccountType.EXPENSE).id),
        "fuel_card_expense_account": str(acc("Fuel Card Recovery", AccountType.EXPENSE).id),
        "social_club_expense_account": str(acc("Social Club", AccountType.EXPENSE).id),
        "cfmeu_expense_account": str(acc("CFMEU", AccountType.EXPENSE).id),
        "bank_account": str(bank.id),
    }


def _payslip_payload(entity, accounts, **overrides):
    payload = {
        "entity": str(entity.id),
        "pay_period_start": "2026-01-01",
        "pay_period_end": "2026-01-14",
        "payment_date": "2026-01-16",
        "currency": "AUD",
        "gross_amount": "3000.00",
        "deduction_tax": "600.00",
        "deduction_fuel_card": "50.00",
        "deduction_social_club": "10.00",
        "deduction_cfmeu": "20.00",
        "deduction_pretax_lease": "200.00",
        "net_pay": "2120.00",
        **accounts,
    }
    payload.update(overrides)
    return payload


def test_viewer_cannot_create_payslip():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, _ = make_accounts(entity)
    accounts = _make_payroll_accounts(entity, bank)

    client = authenticated_client(user)
    response = client.post("/api/v1/payslips/", _payslip_payload(entity, accounts), format="json")
    assert response.status_code == 403


def test_editor_can_create_payslip_with_balanced_entry():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    accounts = _make_payroll_accounts(entity, bank)

    client = authenticated_client(user)
    response = client.post("/api/v1/payslips/", _payslip_payload(entity, accounts), format="json")
    assert response.status_code == 201
    assert response.data["journal_entry"] is not None


def test_create_rejects_incorrect_net_pay_with_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    accounts = _make_payroll_accounts(entity, bank)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/payslips/", _payslip_payload(entity, accounts, net_pay="9999.00"), format="json"
    )
    assert response.status_code == 400


def test_patch_reverses_and_reposts():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    accounts = _make_payroll_accounts(entity, bank)

    client = authenticated_client(user)
    create = client.post("/api/v1/payslips/", _payslip_payload(entity, accounts), format="json")
    payslip_id = create.data["id"]
    original_entry_id = create.data["journal_entry"]

    response = client.patch(
        f"/api/v1/payslips/{payslip_id}/",
        {"gross_amount": "3200.00", "deduction_tax": "650.00", "net_pay": "2270.00"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["journal_entry"] != original_entry_id

    journal_resp = client.get(f"/api/v1/journal-entries/{original_entry_id}/")
    assert journal_resp.data["status"] == "REVERSED"


def test_payslip_summary_aggregates_and_filters_by_entity():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    accounts = _make_payroll_accounts(entity, bank)

    client = authenticated_client(user)
    client.post("/api/v1/payslips/", _payslip_payload(entity, accounts), format="json")
    client.post(
        "/api/v1/payslips/",
        _payslip_payload(
            entity, accounts,
            pay_period_start="2026-01-15", pay_period_end="2026-01-28", payment_date="2026-01-30",
        ),
        format="json",
    )

    response = client.get(f"/api/v1/payslips/summary/?entity={entity.id}")
    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["gross"] == "6000.0000"
    assert response.data["tax"] == "1200.0000"


def test_cross_entity_payslip_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(other_entity)
    accounts = _make_payroll_accounts(other_entity, bank)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/payslips/", _payslip_payload(other_entity, accounts), format="json"
    )
    assert response.status_code == 403
