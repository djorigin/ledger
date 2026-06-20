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
from apps.ledger.services import (
    JournalLineInput,
    mark_account_reconciled,
    post_journal_entry,
    record_simple_transaction,
    reverse_journal_entry,
)
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


def make_fx_clearing_accounts(entity):
    bank_aud = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank AUD", native_currency="AUD"
    )
    bank_cny = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank CNY", native_currency="CNY"
    )
    fx_clearing_aud = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="FX Clearing AUD", native_currency="AUD"
    )
    fx_clearing_cny = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="FX Clearing CNY", native_currency="CNY"
    )
    return bank_aud, bank_cny, fx_clearing_aud, fx_clearing_cny


def test_post_journal_entry_accepts_cross_currency_entry_balanced_per_currency():
    entity = make_entity()
    user = make_user()
    bank_aud, bank_cny, fx_clearing_aud, fx_clearing_cny = make_fx_clearing_accounts(entity)

    entry = post_journal_entry(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="AUD to CNY transfer via FX clearing",
        created_by=user,
        lines=[
            JournalLineInput(account=fx_clearing_aud, currency="AUD", debit_amount=Decimal("100")),
            JournalLineInput(account=bank_aud, currency="AUD", credit_amount=Decimal("100")),
            JournalLineInput(account=bank_cny, currency="CNY", debit_amount=Decimal("470")),
            JournalLineInput(account=fx_clearing_cny, currency="CNY", credit_amount=Decimal("470")),
        ],
    )
    assert entry.lines.count() == 4


def test_post_journal_entry_rejects_cross_currency_entry_not_balanced_per_currency():
    entity = make_entity()
    user = make_user()
    bank_aud, bank_cny, fx_clearing_aud, fx_clearing_cny = make_fx_clearing_accounts(entity)

    # Flat sums match (100 == 100) but this is accounting-nonsense: the AUD
    # leg alone is unbalanced (100 debit, 0 credit) and the CNY leg alone is
    # unbalanced (0 debit, 100 credit). Before the per-currency fix this
    # incorrectly passed.
    with pytest.raises(UnbalancedJournalEntryError):
        post_journal_entry(
            entity=entity,
            entry_date=date(2026, 1, 1),
            description="bad cross-currency entry",
            created_by=user,
            lines=[
                JournalLineInput(account=fx_clearing_aud, currency="AUD", debit_amount=Decimal("100")),
                JournalLineInput(account=fx_clearing_cny, currency="CNY", credit_amount=Decimal("100")),
            ],
        )


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


def test_mark_account_reconciled_creates_record():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 1), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )

    record = mark_account_reconciled(
        account=bank, statement_date=date(2026, 6, 5),
        statement_balance=Decimal("950.00"), reconciled_by=user,
    )
    assert record.account == bank
    assert record.statement_date == date(2026, 6, 5)
    assert record.statement_balance == Decimal("950.00")
    assert record.reconciled_by == user


def test_mark_account_reconciled_clears_matching_lines_up_to_date():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    early = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 1), description="Early",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )
    late = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 10), description="Late",
        debit_account=groceries, credit_account=bank, amount=Decimal("20.00"),
        currency="AUD", created_by=user,
    )

    mark_account_reconciled(
        account=bank, statement_date=date(2026, 6, 5),
        statement_balance=Decimal("950.00"), reconciled_by=user,
    )

    early_line = early.lines.get(account=bank)
    late_line = late.lines.get(account=bank)
    early_line.refresh_from_db()
    late_line.refresh_from_db()
    assert early_line.cleared is True
    assert late_line.cleared is False


def test_mark_account_reconciled_does_not_require_all_lines_matched_first():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 1), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )

    # No apps.imports matching/categorization ever happened for this line --
    # reconciliation must still succeed (it's a ledger-level concept that
    # works whether or not the import feature was ever used).
    record = mark_account_reconciled(
        account=bank, statement_date=date(2026, 6, 5),
        statement_balance=Decimal("950.00"), reconciled_by=user,
    )
    assert record.pk is not None


def test_mark_account_reconciled_does_not_reclear_already_cleared_lines():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 1), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50.00"),
        currency="AUD", created_by=user,
    )

    mark_account_reconciled(
        account=bank, statement_date=date(2026, 6, 5),
        statement_balance=Decimal("950.00"), reconciled_by=user,
    )
    # Re-running for an overlapping/later date must not error, and the
    # already-cleared line stays cleared (idempotent).
    mark_account_reconciled(
        account=bank, statement_date=date(2026, 6, 30),
        statement_balance=Decimal("950.00"), reconciled_by=user,
    )
    line = entry.lines.get(account=bank)
    assert line.cleared is True
    from apps.ledger.models import ReconciliationRecord

    assert ReconciliationRecord.objects.filter(account=bank).count() == 2
