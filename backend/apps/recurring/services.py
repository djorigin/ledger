from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from apps.ledger.services import record_simple_transaction
from apps.recurring.exceptions import AlreadyReviewedError
from apps.recurring.models import (
    PendingEntryStatus,
    PendingRecurringEntry,
    RecurrenceFrequency,
    RecurringTransactionTemplate,
)

_FREQUENCY_DELTAS = {
    RecurrenceFrequency.WEEKLY: relativedelta(weeks=1),
    RecurrenceFrequency.MONTHLY: relativedelta(months=1),
    RecurrenceFrequency.QUARTERLY: relativedelta(months=3),
    RecurrenceFrequency.ANNUALLY: relativedelta(years=1),
}


def _advance(due_date: date, frequency: str) -> date:
    return due_date + _FREQUENCY_DELTAS[frequency]


def generate_due_recurring_entries(*, as_of: date | None = None) -> list[PendingRecurringEntry]:
    """
    Never posts a JournalEntry directly -- only creates reviewable
    PendingRecurringEntry rows. Catches up: a template whose next_due_date
    is well in the past (the scheduler didn't run for a while) generates
    one pending entry per missed occurrence, not just one. Idempotent via
    get_or_create on (template, due_date) -- safe to call repeatedly or
    from overlapping beat runs. Stops advancing once next_due_date would
    pass end_date; the template goes dormant rather than being touched.
    """
    as_of = as_of or timezone.now().date()
    created = []

    templates = RecurringTransactionTemplate.objects.filter(is_active=True, next_due_date__lte=as_of)
    for template in templates:
        with transaction.atomic():
            while template.next_due_date <= as_of:
                if template.end_date and template.next_due_date > template.end_date:
                    break
                entry, was_created = PendingRecurringEntry.objects.get_or_create(
                    template=template,
                    due_date=template.next_due_date,
                    defaults={"amount": template.amount},
                )
                if was_created:
                    created.append(entry)
                template.next_due_date = _advance(template.next_due_date, template.frequency)
                template.save(update_fields=["next_due_date"])

    return created


def approve_pending_entry(*, pending_entry, approved_by, amount=None) -> PendingRecurringEntry:
    if pending_entry.status != PendingEntryStatus.PENDING:
        raise AlreadyReviewedError(f"Pending entry '{pending_entry}' has already been reviewed.")

    template = pending_entry.template
    with transaction.atomic():
        entry = record_simple_transaction(
            entity=template.entity,
            entry_date=pending_entry.due_date,
            description=template.description,
            debit_account=template.debit_account,
            credit_account=template.credit_account,
            amount=amount if amount is not None else pending_entry.amount,
            currency=template.currency,
            created_by=approved_by,
        )
        pending_entry.status = PendingEntryStatus.APPROVED
        pending_entry.journal_entry = entry
        pending_entry.reviewed_by = approved_by
        pending_entry.reviewed_at = timezone.now()
        pending_entry.save(
            update_fields=["status", "journal_entry", "reviewed_by", "reviewed_at"]
        )
    return pending_entry


def dismiss_pending_entry(*, pending_entry, dismissed_by) -> PendingRecurringEntry:
    if pending_entry.status != PendingEntryStatus.PENDING:
        raise AlreadyReviewedError(f"Pending entry '{pending_entry}' has already been reviewed.")

    pending_entry.status = PendingEntryStatus.DISMISSED
    pending_entry.reviewed_by = dismissed_by
    pending_entry.reviewed_at = timezone.now()
    pending_entry.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    return pending_entry
