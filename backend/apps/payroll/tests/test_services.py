from datetime import date
from decimal import Decimal

import pytest

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, JournalEntryStatus
from apps.ledger.services import get_account_balance
from apps.payroll.models import Payslip
from apps.payroll.services import compute_payslip_summary, record_payslip, update_payslip
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def make_payroll_accounts(entity, currency="AUD"):
    def acc(name, account_type):
        return Account.objects.create(entity=entity, name=name, account_type=account_type, native_currency=currency)

    return {
        "bank_account": acc("Bank", AccountType.ASSET),
        "income_account": acc("KCC Gross", AccountType.INCOME),
        "pretax_lease_expense_account": acc("Lease", AccountType.EXPENSE),
        "tax_expense_account": acc("PAYG Withheld", AccountType.EXPENSE),
        "fuel_card_expense_account": acc("Fuel Card Recovery", AccountType.EXPENSE),
        "social_club_expense_account": acc("Social Club", AccountType.EXPENSE),
        "cfmeu_expense_account": acc("CFMEU", AccountType.EXPENSE),
    }


def _base_fields(entity, accounts, **overrides):
    fields = dict(
        entity=entity,
        pay_period_start=date(2026, 1, 1),
        pay_period_end=date(2026, 1, 14),
        payment_date=date(2026, 1, 16),
        currency="AUD",
        gross_amount=Decimal("3000"),
        deduction_tax=Decimal("600"),
        deduction_fuel_card=Decimal("50"),
        deduction_social_club=Decimal("10"),
        deduction_cfmeu=Decimal("20"),
        deduction_pretax_lease=Decimal("200"),
        net_pay=Decimal("2120"),
        **accounts,
    )
    fields.update(overrides)
    return fields


def test_record_payslip_posts_balanced_entry():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)

    payslip = record_payslip(created_by=user, **_base_fields(entity, accounts))

    assert payslip.journal_entry is not None
    assert payslip.journal_entry.status == JournalEntryStatus.POSTED
    assert get_account_balance(accounts["income_account"]) == Decimal("3000")
    assert get_account_balance(accounts["pretax_lease_expense_account"]) == Decimal("200")
    assert get_account_balance(accounts["tax_expense_account"]) == Decimal("600")
    assert get_account_balance(accounts["fuel_card_expense_account"]) == Decimal("50")
    assert get_account_balance(accounts["social_club_expense_account"]) == Decimal("10")
    assert get_account_balance(accounts["cfmeu_expense_account"]) == Decimal("20")
    assert get_account_balance(accounts["bank_account"]) == Decimal("2120")


def test_record_payslip_skips_zero_deduction_lines():
    """A fortnight with no social club / CFMEU deduction must not try to
    post a zero-amount JournalLine (post_journal_entry requires exactly
    one of debit/credit > 0 per line)."""
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)

    fields = _base_fields(
        entity, accounts,
        deduction_social_club=Decimal("0"), deduction_cfmeu=Decimal("0"),
        net_pay=Decimal("2150"),  # 3000 - 200 - 600 - 50 - 0 - 0
    )
    payslip = record_payslip(created_by=user, **fields)

    assert get_account_balance(accounts["social_club_expense_account"]) == Decimal("0")
    assert get_account_balance(accounts["cfmeu_expense_account"]) == Decimal("0")
    assert get_account_balance(accounts["bank_account"]) == Decimal("2150")


def test_record_payslip_rejects_incorrect_net_pay():
    from django.core.exceptions import ValidationError

    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)

    with pytest.raises(ValidationError):
        record_payslip(created_by=user, **_base_fields(entity, accounts, net_pay=Decimal("9999")))


def test_update_payslip_reverses_original_entry_and_posts_new_one():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)

    payslip = record_payslip(created_by=user, **_base_fields(entity, accounts))
    original_entry_id = payslip.journal_entry_id

    # gross 3200, tax 650, other deductions unchanged (200+50+10+20=280)
    # -> net_pay = 3200 - 280 - 650 = 2270
    updated = update_payslip(
        payslip=payslip, updated_by=user,
        gross_amount=Decimal("3200"), deduction_tax=Decimal("650"), net_pay=Decimal("2270"),
    )

    assert updated.journal_entry_id != original_entry_id
    original_entry = payslip.journal_entry.__class__.objects.get(pk=original_entry_id)
    assert original_entry.status == JournalEntryStatus.REVERSED
    # Net effect: only the corrected amounts remain on the books, the
    # original entry's effect is fully cancelled by its reversal.
    assert get_account_balance(accounts["income_account"]) == Decimal("3200")
    assert get_account_balance(accounts["tax_expense_account"]) == Decimal("650")
    assert get_account_balance(accounts["bank_account"]) == Decimal("2270")


def test_compute_payslip_summary_aggregates_ytd_totals():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)

    record_payslip(created_by=user, **_base_fields(entity, accounts))
    record_payslip(
        created_by=user,
        **_base_fields(
            entity, accounts,
            pay_period_start=date(2026, 1, 15), pay_period_end=date(2026, 1, 28),
            payment_date=date(2026, 1, 30),
        ),
    )

    summary = compute_payslip_summary(Payslip.objects.filter(entity=entity))
    assert summary.count == 2
    assert summary.gross == Decimal("6000")
    assert summary.tax == Decimal("1200")
    assert summary.net == Decimal("4240")
