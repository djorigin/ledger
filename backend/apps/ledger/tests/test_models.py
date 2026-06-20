from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, DebitCredit, JournalLine, ReconciliationRecord
from apps.ledger.services import record_simple_transaction
from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_account_normal_balance_for_each_type():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    expectations = {
        AccountType.ASSET: DebitCredit.DEBIT,
        AccountType.EXPENSE: DebitCredit.DEBIT,
        AccountType.LIABILITY: DebitCredit.CREDIT,
        AccountType.EQUITY: DebitCredit.CREDIT,
        AccountType.INCOME: DebitCredit.CREDIT,
    }
    for account_type, expected in expectations.items():
        account = Account.objects.create(
            entity=entity, account_type=account_type, name=account_type, native_currency="AUD"
        )
        assert account.normal_balance == expected


def test_child_account_must_match_parent_entity():
    entity_a = Entity.objects.create(name="A", type=EntityType.HOUSEHOLD)
    entity_b = Entity.objects.create(name="B", type=EntityType.BUSINESS)
    parent = Account.objects.create(
        entity=entity_a, account_type=AccountType.ASSET, name="Assets", native_currency="AUD"
    )
    child = Account(
        entity=entity_b,
        parent=parent,
        account_type=AccountType.ASSET,
        name="Bank",
        native_currency="AUD",
    )
    with pytest.raises(ValidationError):
        child.full_clean()


def test_child_account_must_match_parent_account_type():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    parent = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Assets", native_currency="AUD"
    )
    child = Account(
        entity=entity,
        parent=parent,
        account_type=AccountType.LIABILITY,
        name="Bank",
        native_currency="AUD",
    )
    with pytest.raises(ValidationError):
        child.full_clean()


def test_valid_account_hierarchy_saves_cleanly():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    assets = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Assets", native_currency="AUD"
    )
    bank = Account(
        entity=entity,
        parent=assets,
        account_type=AccountType.ASSET,
        name="Bank",
        native_currency="AUD",
    )
    bank.full_clean()
    bank.save()
    assert bank.parent == assets


def test_journal_line_defaults_to_not_cleared():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    user = User.objects.create_user(email="u@example.com", password="x")
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency="AUD"
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency="AUD"
    )
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("10"),
        currency="AUD", created_by=user,
    )
    line = entry.lines.first()
    assert isinstance(line, JournalLine)
    assert line.cleared is False


def test_reconciliation_record_string_representation():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    user = User.objects.create_user(email="u@example.com", password="x")
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency="AUD"
    )
    record = ReconciliationRecord.objects.create(
        account=bank, statement_date=date(2026, 6, 5),
        statement_balance=Decimal("100.00"), reconciled_by=user,
    )
    assert "Bank" in str(record)
    assert "100.00" in str(record)
