from datetime import date
from decimal import Decimal

import pytest

from apps.entities.models import Entity, EntityType
from apps.ledger.exceptions import (
    CrossEntityAccountError,
    CurrencyMismatchError,
    InvalidJournalLineError,
    JournalEntryAlreadyReversedError,
    LedgerError,
    UnbalancedJournalEntryError,
)
from apps.ledger.models import Account, AccountType, JournalEntryStatus
from apps.ledger.services import JournalLineInput, post_journal_entry, record_simple_transaction, reverse_journal_entry
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity():
    return Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def make_accounts(entity):
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency="AUD"
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency="AUD"
    )
    return bank, groceries


def test_post_journal_entry_creates_balanced_entry():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)

    entry = post_journal_entry(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="Groceries",
        created_by=user,
        lines=[
            JournalLineInput(account=groceries, currency="AUD", debit_amount=Decimal("50.00")),
            JournalLineInput(account=bank, currency="AUD", credit_amount=Decimal("50.00")),
        ],
    )

    assert entry.status == JournalEntryStatus.POSTED
    assert entry.posted_at is not None
    assert entry.lines.count() == 2


def test_post_journal_entry_rejects_unbalanced_lines():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)

    with pytest.raises(UnbalancedJournalEntryError):
        post_journal_entry(
            entity=entity,
            entry_date=date(2026, 1, 1),
            description="Groceries",
            created_by=user,
            lines=[
                JournalLineInput(
                    account=groceries, currency="AUD", debit_amount=Decimal("50.00")
                ),
                JournalLineInput(account=bank, currency="AUD", credit_amount=Decimal("40.00")),
            ],
        )
    assert groceries.journal_lines.count() == 0


def test_post_journal_entry_requires_at_least_two_lines():
    entity = make_entity()
    user = make_user()
    bank, _ = make_accounts(entity)

    with pytest.raises(InvalidJournalLineError):
        post_journal_entry(
            entity=entity,
            entry_date=date(2026, 1, 1),
            description="Solo line",
            created_by=user,
            lines=[JournalLineInput(account=bank, currency="AUD", debit_amount=Decimal("10"))],
        )


def test_post_journal_entry_rejects_currency_mismatch_with_account():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)

    with pytest.raises(CurrencyMismatchError):
        post_journal_entry(
            entity=entity,
            entry_date=date(2026, 1, 1),
            description="Groceries",
            created_by=user,
            lines=[
                JournalLineInput(account=groceries, currency="CNY", debit_amount=Decimal("50")),
                JournalLineInput(account=bank, currency="AUD", credit_amount=Decimal("50")),
            ],
        )


def test_post_journal_entry_rejects_cross_entity_account():
    entity = make_entity()
    other_entity = Entity.objects.create(name="Business", type=EntityType.BUSINESS)
    user = make_user()
    bank, groceries = make_accounts(entity)
    other_account = Account.objects.create(
        entity=other_entity, account_type=AccountType.ASSET, name="Other Bank", native_currency="AUD"
    )

    with pytest.raises(CrossEntityAccountError):
        post_journal_entry(
            entity=entity,
            entry_date=date(2026, 1, 1),
            description="Groceries",
            created_by=user,
            lines=[
                JournalLineInput(account=groceries, currency="AUD", debit_amount=Decimal("50")),
                JournalLineInput(account=other_account, currency="AUD", credit_amount=Decimal("50")),
            ],
        )


def test_record_simple_transaction_produces_correct_two_line_entry():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)

    entry = record_simple_transaction(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="Groceries",
        debit_account=groceries,
        credit_account=bank,
        amount=Decimal("50.00"),
        currency="AUD",
        created_by=user,
    )

    lines = list(entry.lines.all())
    assert len(lines) == 2
    debit_line = next(line for line in lines if line.debit_amount)
    credit_line = next(line for line in lines if line.credit_amount)
    assert debit_line.account == groceries
    assert credit_line.account == bank
    assert debit_line.debit_amount == credit_line.credit_amount == Decimal("50.0000")


def test_reverse_journal_entry_produces_balanced_offsetting_entry():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="Groceries",
        debit_account=groceries,
        credit_account=bank,
        amount=Decimal("50.00"),
        currency="AUD",
        created_by=user,
    )

    reversal = reverse_journal_entry(entry=entry, reversed_by_user=user)

    entry.refresh_from_db()
    assert entry.status == JournalEntryStatus.REVERSED
    assert reversal.reverses_id == entry.id
    assert entry.reversed_by.id == reversal.id

    reversal_lines = {line.account_id: line for line in reversal.lines.all()}
    assert reversal_lines[groceries.id].credit_amount == Decimal("50.0000")
    assert reversal_lines[bank.id].debit_amount == Decimal("50.0000")


def test_reverse_journal_entry_twice_raises_error():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="Groceries",
        debit_account=groceries,
        credit_account=bank,
        amount=Decimal("50.00"),
        currency="AUD",
        created_by=user,
    )

    reverse_journal_entry(entry=entry, reversed_by_user=user)
    entry.refresh_from_db()

    with pytest.raises(JournalEntryAlreadyReversedError):
        reverse_journal_entry(entry=entry, reversed_by_user=user)


def test_posted_journal_entry_cannot_be_hard_deleted():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="Groceries",
        debit_account=groceries,
        credit_account=bank,
        amount=Decimal("50.00"),
        currency="AUD",
        created_by=user,
    )

    with pytest.raises(LedgerError):
        entry.delete()

    entry.refresh_from_db()
    assert entry.pk is not None
