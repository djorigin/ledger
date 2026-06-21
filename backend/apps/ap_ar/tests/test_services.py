from datetime import date
from decimal import Decimal

import pytest

from apps.ap_ar.exceptions import AlreadyCancelledError, HasPaymentsError, OverpaymentError
from apps.ap_ar.services import (
    cancel_bill,
    cancel_invoice,
    compute_bill_progress,
    compute_invoice_progress,
    record_bill,
    record_bill_payment,
    record_invoice,
    record_invoice_payment,
)
from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, JournalEntryStatus
from apps.ledger.services import get_account_balance
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def make_accounts(entity, currency="AUD"):
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency=currency
    )
    expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Utilities", native_currency=currency
    )
    payable = Account.objects.create(
        entity=entity, account_type=AccountType.LIABILITY, name="Accounts Payable", native_currency=currency
    )
    income = Account.objects.create(
        entity=entity, account_type=AccountType.INCOME, name="Consulting Income", native_currency=currency
    )
    receivable = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Accounts Receivable", native_currency=currency
    )
    return bank, expense, payable, income, receivable


def test_record_bill_posts_balanced_entry():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)

    bill = record_bill(
        entity=entity, vendor_name="Acme", description="January invoice",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    assert bill.journal_entry.status == JournalEntryStatus.POSTED
    assert get_account_balance(expense) == Decimal("200")
    assert get_account_balance(payable) == Decimal("200")


def test_compute_bill_progress_open_to_paid():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    assert compute_bill_progress(bill).status == "OPEN"

    record_bill_payment(
        bill=bill, payment_date=date(2026, 1, 10), amount=Decimal("80"),
        payment_account=bank, created_by=user,
    )
    progress = compute_bill_progress(bill)
    assert progress.status == "PARTIALLY_PAID"
    assert progress.amount_paid == Decimal("80")
    assert progress.amount_due == Decimal("120")

    record_bill_payment(
        bill=bill, payment_date=date(2026, 1, 20), amount=Decimal("120"),
        payment_account=bank, created_by=user,
    )
    progress = compute_bill_progress(bill)
    assert progress.status == "PAID"
    assert progress.amount_due == Decimal("0")
    assert get_account_balance(payable) == Decimal("0")
    assert get_account_balance(bank) == Decimal("-200")


def test_bill_is_overdue_when_past_due_date_and_unpaid():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 10),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    assert compute_bill_progress(bill, as_of=date(2026, 1, 5)).is_overdue is False
    assert compute_bill_progress(bill, as_of=date(2026, 1, 15)).is_overdue is True

    record_bill_payment(
        bill=bill, payment_date=date(2026, 1, 20), amount=Decimal("200"),
        payment_account=bank, created_by=user,
    )
    # fully paid -- no longer overdue even though due_date has passed
    assert compute_bill_progress(bill, as_of=date(2026, 2, 1)).is_overdue is False


def test_record_bill_payment_rejects_overpayment():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    with pytest.raises(OverpaymentError):
        record_bill_payment(
            bill=bill, payment_date=date(2026, 1, 10), amount=Decimal("201"),
            payment_account=bank, created_by=user,
        )


def test_cancel_bill_reverses_entry_and_nets_to_zero():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    cancel_bill(bill=bill, cancelled_by=user)
    bill.refresh_from_db()
    assert bill.is_cancelled is True
    assert get_account_balance(expense) == Decimal("0")
    assert get_account_balance(payable) == Decimal("0")
    assert compute_bill_progress(bill).status == "CANCELLED"


def test_cancel_bill_rejects_when_payments_exist():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    record_bill_payment(
        bill=bill, payment_date=date(2026, 1, 10), amount=Decimal("50"),
        payment_account=bank, created_by=user,
    )
    with pytest.raises(HasPaymentsError):
        cancel_bill(bill=bill, cancelled_by=user)


def test_cancel_bill_rejects_already_cancelled():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    bill = record_bill(
        entity=entity, vendor_name="Acme", description="",
        bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("200"), currency="AUD",
        expense_account=expense, payable_account=payable, created_by=user,
    )
    cancel_bill(bill=bill, cancelled_by=user)
    with pytest.raises(AlreadyCancelledError):
        cancel_bill(bill=bill, cancelled_by=user)


def test_record_invoice_posts_balanced_entry_and_progress():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)

    invoice = record_invoice(
        entity=entity, customer_name="Bob", description="Consulting",
        invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("500"), currency="AUD",
        income_account=income, receivable_account=receivable, created_by=user,
    )
    assert get_account_balance(receivable) == Decimal("500")
    assert get_account_balance(income) == Decimal("500")
    assert compute_invoice_progress(invoice).status == "OPEN"

    record_invoice_payment(
        invoice=invoice, payment_date=date(2026, 1, 15), amount=Decimal("500"),
        payment_account=bank, created_by=user,
    )
    progress = compute_invoice_progress(invoice)
    assert progress.status == "PAID"
    assert get_account_balance(receivable) == Decimal("0")
    assert get_account_balance(bank) == Decimal("500")


def test_record_invoice_payment_rejects_overpayment():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)
    invoice = record_invoice(
        entity=entity, customer_name="Bob", description="",
        invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("500"), currency="AUD",
        income_account=income, receivable_account=receivable, created_by=user,
    )
    with pytest.raises(OverpaymentError):
        record_invoice_payment(
            invoice=invoice, payment_date=date(2026, 1, 15), amount=Decimal("501"),
            payment_account=bank, created_by=user,
        )


def test_cancel_invoice_reverses_entry():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)
    invoice = record_invoice(
        entity=entity, customer_name="Bob", description="",
        invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("500"), currency="AUD",
        income_account=income, receivable_account=receivable, created_by=user,
    )
    cancel_invoice(invoice=invoice, cancelled_by=user)
    invoice.refresh_from_db()
    assert invoice.is_cancelled is True
    assert get_account_balance(receivable) == Decimal("0")
    assert get_account_balance(income) == Decimal("0")


def test_cancel_invoice_rejects_when_payments_exist():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)
    invoice = record_invoice(
        entity=entity, customer_name="Bob", description="",
        invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("500"), currency="AUD",
        income_account=income, receivable_account=receivable, created_by=user,
    )
    record_invoice_payment(
        invoice=invoice, payment_date=date(2026, 1, 15), amount=Decimal("100"),
        payment_account=bank, created_by=user,
    )
    with pytest.raises(HasPaymentsError):
        cancel_invoice(invoice=invoice, cancelled_by=user)
