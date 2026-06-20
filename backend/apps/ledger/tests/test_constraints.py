from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, JournalEntry, JournalEntryStatus, JournalLine
from apps.users.models import User

# Deferred Postgres constraint triggers only fire at a real transaction COMMIT,
# not at the end of a savepoint. pytest-django's default db fixture wraps each
# test in an outer transaction that's rolled back, so transaction.atomic()
# blocks inside it never actually commit. transaction=True uses real commits
# (and truncates tables between tests instead), which is required to exercise
# the trigger.
pytestmark = pytest.mark.django_db(transaction=True)


def make_entity_user_accounts():
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    user = User.objects.create_user(email="u@example.com", password="x")
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency="AUD"
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency="AUD"
    )
    return entity, user, bank, groceries


def test_unbalanced_lines_rejected_at_db_commit_even_via_raw_orm_calls():
    entity, user, bank, groceries = make_entity_user_accounts()

    with pytest.raises(Exception):
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                entity=entity,
                entry_date=date(2026, 1, 1),
                description="bad-unbalanced",
                status=JournalEntryStatus.POSTED,
                created_by=user,
            )
            JournalLine.objects.create(
                journal_entry=entry,
                account=groceries,
                debit_amount=Decimal("50"),
                credit_amount=Decimal("0"),
                currency="AUD",
            )
            JournalLine.objects.create(
                journal_entry=entry,
                account=bank,
                debit_amount=Decimal("0"),
                credit_amount=Decimal("40"),
                currency="AUD",
            )

    assert not JournalEntry.objects.filter(description="bad-unbalanced").exists()


def test_journal_line_check_constraint_rejects_both_sides_nonzero():
    entity, user, bank, groceries = make_entity_user_accounts()
    entry = JournalEntry.objects.create(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="single line test",
        status=JournalEntryStatus.POSTED,
        created_by=user,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            JournalLine.objects.create(
                journal_entry=entry,
                account=bank,
                debit_amount=Decimal("10"),
                credit_amount=Decimal("10"),
                currency="AUD",
            )


def test_journal_line_check_constraint_rejects_both_sides_zero():
    entity, user, bank, groceries = make_entity_user_accounts()
    entry = JournalEntry.objects.create(
        entity=entity,
        entry_date=date(2026, 1, 1),
        description="zero line test",
        status=JournalEntryStatus.POSTED,
        created_by=user,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            JournalLine.objects.create(
                journal_entry=entry,
                account=bank,
                debit_amount=Decimal("0"),
                credit_amount=Decimal("0"),
                currency="AUD",
            )
