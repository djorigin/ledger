from datetime import date
from decimal import Decimal

import pytest

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, JournalEntryStatus
from apps.ledger.services import get_account_balance
from apps.recurring.exceptions import AlreadyReviewedError
from apps.recurring.models import (
    PendingEntryStatus,
    PendingRecurringEntry,
    RecurrenceFrequency,
    RecurringTransactionTemplate,
)
from apps.recurring.services import (
    approve_pending_entry,
    dismiss_pending_entry,
    generate_due_recurring_entries,
)
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
        entity=entity, account_type=AccountType.EXPENSE, name="Mortgage Interest", native_currency=currency
    )
    return bank, expense


def make_template(entity, user, bank, expense, *, frequency=RecurrenceFrequency.MONTHLY, next_due_date, end_date=None):
    return RecurringTransactionTemplate.objects.create(
        entity=entity, description="Mortgage", debit_account=expense, credit_account=bank,
        amount=Decimal("2000"), currency="AUD", frequency=frequency,
        start_date=next_due_date, next_due_date=next_due_date, end_date=end_date, created_by=user,
    )


def test_generate_due_recurring_entries_creates_one_entry_when_due():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    template = make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))

    created = generate_due_recurring_entries(as_of=date(2026, 1, 1))
    assert len(created) == 1
    assert created[0].due_date == date(2026, 1, 1)
    assert created[0].amount == Decimal("2000")
    template.refresh_from_db()
    assert template.next_due_date == date(2026, 2, 1)


def test_generate_due_recurring_entries_not_yet_due_creates_nothing():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 3, 1))

    created = generate_due_recurring_entries(as_of=date(2026, 1, 1))
    assert created == []


def test_generate_due_recurring_entries_catches_up_multiple_missed_periods():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    template = make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))

    # scheduler "didn't run" for 3 months
    created = generate_due_recurring_entries(as_of=date(2026, 4, 1))
    assert len(created) == 4  # Jan, Feb, Mar, Apr
    assert sorted(e.due_date for e in created) == [
        date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1),
    ]
    template.refresh_from_db()
    assert template.next_due_date == date(2026, 5, 1)


def test_generate_due_recurring_entries_is_idempotent():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))

    first = generate_due_recurring_entries(as_of=date(2026, 1, 1))
    second = generate_due_recurring_entries(as_of=date(2026, 1, 1))
    assert len(first) == 1
    assert second == []
    assert PendingRecurringEntry.objects.count() == 1


def test_generate_due_recurring_entries_stops_at_end_date():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(
        entity, user, bank, expense, next_due_date=date(2026, 1, 1), end_date=date(2026, 2, 15)
    )

    created = generate_due_recurring_entries(as_of=date(2026, 6, 1))
    assert sorted(e.due_date for e in created) == [date(2026, 1, 1), date(2026, 2, 1)]


def test_generate_due_recurring_entries_quarterly_and_annually():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    quarterly = make_template(
        entity, user, bank, expense, frequency=RecurrenceFrequency.QUARTERLY, next_due_date=date(2026, 1, 1)
    )
    annual = make_template(
        entity, user, bank, expense, frequency=RecurrenceFrequency.ANNUALLY, next_due_date=date(2026, 1, 1)
    )

    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    quarterly.refresh_from_db()
    annual.refresh_from_db()
    assert quarterly.next_due_date == date(2026, 4, 1)
    assert annual.next_due_date == date(2027, 1, 1)


def test_approve_pending_entry_posts_journal_entry():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    pending = PendingRecurringEntry.objects.get()

    approve_pending_entry(pending_entry=pending, approved_by=user)
    pending.refresh_from_db()
    assert pending.status == PendingEntryStatus.APPROVED
    assert pending.journal_entry is not None
    assert pending.journal_entry.status == JournalEntryStatus.POSTED
    assert get_account_balance(expense) == Decimal("2000")
    assert get_account_balance(bank) == Decimal("-2000")


def test_approve_pending_entry_with_amount_override():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    pending = PendingRecurringEntry.objects.get()

    approve_pending_entry(pending_entry=pending, approved_by=user, amount=Decimal("2150.50"))
    assert get_account_balance(expense) == Decimal("2150.50")


def test_approve_pending_entry_rejects_already_reviewed():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    pending = PendingRecurringEntry.objects.get()

    approve_pending_entry(pending_entry=pending, approved_by=user)
    with pytest.raises(AlreadyReviewedError):
        approve_pending_entry(pending_entry=pending, approved_by=user)


def test_dismiss_pending_entry_never_posts_anything():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    pending = PendingRecurringEntry.objects.get()

    dismiss_pending_entry(pending_entry=pending, dismissed_by=user)
    pending.refresh_from_db()
    assert pending.status == PendingEntryStatus.DISMISSED
    assert pending.journal_entry is None
    assert get_account_balance(expense) == Decimal("0")


def test_dismiss_pending_entry_rejects_already_reviewed():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    generate_due_recurring_entries(as_of=date(2026, 1, 1))
    pending = PendingRecurringEntry.objects.get()

    dismiss_pending_entry(pending_entry=pending, dismissed_by=user)
    with pytest.raises(AlreadyReviewedError):
        dismiss_pending_entry(pending_entry=pending, dismissed_by=user)


def test_inactive_template_is_never_generated():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    template = make_template(entity, user, bank, expense, next_due_date=date(2026, 1, 1))
    template.is_active = False
    template.save(update_fields=["is_active"])

    created = generate_due_recurring_entries(as_of=date(2026, 1, 1))
    assert created == []
