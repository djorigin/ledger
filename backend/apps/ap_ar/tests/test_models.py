from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.ap_ar.models import Bill, BillPayment, Invoice, InvoicePayment
from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType
from apps.ledger.services import record_simple_transaction
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


def make_throwaway_entry(entity, user, bank, expense):
    return record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="placeholder",
        debit_account=expense, credit_account=bank, amount=Decimal("1"),
        currency=bank.native_currency, created_by=user,
    )


def test_bill_clean_rejects_account_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    other_bank, other_expense, _, _, _ = make_accounts(other_entity)
    entry = make_throwaway_entry(entity, user, bank, expense)

    bill = Bill(
        entity=entity, vendor_name="Acme", description="", bill_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31), amount=Decimal("100"), currency="AUD",
        expense_account=other_expense, payable_account=payable,
        journal_entry=entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        bill.full_clean()


def test_bill_clean_rejects_wrong_account_type():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    entry = make_throwaway_entry(entity, user, bank, expense)

    bill = Bill(
        entity=entity, vendor_name="Acme", description="", bill_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31), amount=Decimal("100"), currency="AUD",
        expense_account=payable,  # wrong type: LIABILITY, not EXPENSE
        payable_account=payable,
        journal_entry=entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        bill.full_clean()


def test_bill_clean_rejects_currency_mismatch():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity, currency="AUD")
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="CNY Expense", native_currency="CNY"
    )
    entry = make_throwaway_entry(entity, user, bank, expense)

    bill = Bill(
        entity=entity, vendor_name="Acme", description="", bill_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31), amount=Decimal("100"), currency="AUD",
        expense_account=cny_expense, payable_account=payable,
        journal_entry=entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        bill.full_clean()


def test_bill_due_date_before_bill_date_violates_constraint():
    from django.db import IntegrityError, transaction

    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    entry = make_throwaway_entry(entity, user, bank, expense)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Bill.objects.create(
                entity=entity, vendor_name="Acme", bill_date=date(2026, 1, 31),
                due_date=date(2026, 1, 1), amount=Decimal("100"), currency="AUD",
                expense_account=expense, payable_account=payable,
                journal_entry=entry, created_by=user,
            )


def test_bill_payment_clean_rejects_wrong_account_type():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, _, _ = make_accounts(entity)
    entry = make_throwaway_entry(entity, user, bank, expense)
    bill = Bill.objects.create(
        entity=entity, vendor_name="Acme", bill_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("100"), currency="AUD", expense_account=expense, payable_account=payable,
        journal_entry=entry, created_by=user,
    )
    payment_entry = make_throwaway_entry(entity, user, bank, expense)

    payment = BillPayment(
        bill=bill, payment_date=date(2026, 1, 5), amount=Decimal("50"),
        payment_account=expense,  # wrong type: EXPENSE, not ASSET
        journal_entry=payment_entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        payment.full_clean()


def test_invoice_clean_rejects_wrong_account_type():
    entity = make_entity()
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)
    entry = make_throwaway_entry(entity, user, bank, expense)

    invoice = Invoice(
        entity=entity, customer_name="Bob", description="", invoice_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31), amount=Decimal("100"), currency="AUD",
        income_account=payable,  # wrong type
        receivable_account=receivable,
        journal_entry=entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        invoice.full_clean()


def test_invoice_payment_clean_rejects_cross_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    bank, expense, payable, income, receivable = make_accounts(entity)
    other_bank, _, _, _, _ = make_accounts(other_entity)
    entry = make_throwaway_entry(entity, user, bank, expense)
    invoice = Invoice.objects.create(
        entity=entity, customer_name="Bob", invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 31),
        amount=Decimal("100"), currency="AUD", income_account=income, receivable_account=receivable,
        journal_entry=entry, created_by=user,
    )
    payment_entry = make_throwaway_entry(entity, user, bank, expense)

    payment = InvoicePayment(
        invoice=invoice, payment_date=date(2026, 1, 5), amount=Decimal("50"),
        payment_account=other_bank,
        journal_entry=payment_entry, created_by=user,
    )
    with pytest.raises(ValidationError):
        payment.full_clean()
