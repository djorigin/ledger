from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.ledger.exceptions import (
    CrossEntityAccountError,
    CurrencyMismatchError,
    InvalidJournalLineError,
    JournalEntryAlreadyReversedError,
    UnbalancedJournalEntryError,
)
from apps.ledger.models import (
    Account,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    ReconciliationRecord,
)


@dataclass(frozen=True)
class JournalLineInput:
    account: Account
    currency: str
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    description: str = ""


def post_journal_entry(*, entity, entry_date, description, lines, created_by, memo=""):
    """
    The only sanctioned way to create a posted JournalEntry. Validates line
    count, entity/currency consistency, and debit=credit balance in Python
    before insert; a deferred Postgres trigger re-checks balance at COMMIT
    regardless of which code path wrote the rows.
    """
    if len(lines) < 2:
        raise InvalidJournalLineError("A journal entry needs at least two lines.")

    totals_by_currency = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
    for line in lines:
        if line.account.entity_id != entity.id:
            raise CrossEntityAccountError(
                f"Account '{line.account}' does not belong to entity '{entity}'."
            )
        if line.currency != line.account.native_currency:
            raise CurrencyMismatchError(
                f"Line currency '{line.currency}' does not match account "
                f"'{line.account}' native currency '{line.account.native_currency}'."
            )
        debit_positive = line.debit_amount and line.debit_amount > 0
        credit_positive = line.credit_amount and line.credit_amount > 0
        if debit_positive == credit_positive:
            raise InvalidJournalLineError(
                "Exactly one of debit_amount or credit_amount must be greater "
                "than zero per line."
            )
        totals_by_currency[line.currency]["debit"] += line.debit_amount
        totals_by_currency[line.currency]["credit"] += line.credit_amount

    # Balance must hold within each currency present in the entry, not as a
    # flat sum across all lines -- a 100 AUD debit and a 100 CNY credit are
    # not "balanced" just because the numbers match.
    for currency, totals in totals_by_currency.items():
        if totals["debit"] != totals["credit"]:
            raise UnbalancedJournalEntryError(
                f"Journal entry is not balanced in {currency}: "
                f"debits={totals['debit']}, credits={totals['credit']}."
            )

    with transaction.atomic():
        entry = JournalEntry(
            entity=entity,
            entry_date=entry_date,
            description=description,
            memo=memo,
            status=JournalEntryStatus.POSTED,
            created_by=created_by,
            posted_at=timezone.now(),
        )
        entry.full_clean()
        entry.save()

        for line in lines:
            journal_line = JournalLine(
                journal_entry=entry,
                account=line.account,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                currency=line.currency,
                description=line.description,
            )
            journal_line.full_clean()
            journal_line.save()

    return entry


def record_simple_transaction(
    *,
    entity,
    entry_date,
    description,
    debit_account,
    credit_account,
    amount,
    currency,
    created_by,
    memo="",
):
    """Convenience wrapper for the common 2-line case (e.g. an expense paid from a bank account)."""
    return post_journal_entry(
        entity=entity,
        entry_date=entry_date,
        description=description,
        memo=memo,
        created_by=created_by,
        lines=[
            JournalLineInput(account=debit_account, currency=currency, debit_amount=amount),
            JournalLineInput(account=credit_account, currency=currency, credit_amount=amount),
        ],
    )


def reverse_journal_entry(*, entry, reversed_by_user, reversal_date=None):
    """
    Creates a new, balanced JournalEntry with every line's debit/credit
    swapped relative to `entry`, and marks `entry` REVERSED. `entry` itself
    is never deleted or otherwise mutated.
    """
    if entry.status == JournalEntryStatus.REVERSED:
        raise JournalEntryAlreadyReversedError(f"Journal entry '{entry}' is already reversed.")

    swapped_lines = [
        JournalLineInput(
            account=line.account,
            currency=line.currency,
            debit_amount=line.credit_amount,
            credit_amount=line.debit_amount,
            description=line.description,
        )
        for line in entry.lines.all()
    ]

    with transaction.atomic():
        reversal = post_journal_entry(
            entity=entry.entity,
            entry_date=reversal_date or timezone.now().date(),
            description=f"Reversal of: {entry.description}",
            lines=swapped_lines,
            created_by=reversed_by_user,
        )
        reversal.reverses = entry
        reversal.save(update_fields=["reverses"])
        entry.mark_reversed(reversed_by_user)

    return reversal


def mark_account_reconciled(*, account, statement_date, statement_balance, reconciled_by, notes=""):
    """
    Records a ReconciliationRecord and marks every currently-uncleared
    POSTED JournalLine on this account, dated on or before statement_date,
    as cleared=True -- regardless of whether it came from an import or was
    entered manually. Does NOT require every line up to statement_date to
    already be matched/categorized first: an account can be partially
    reconciled, with outstanding unmatched items rolling forward to the
    next pass, mirroring real-world bank reconciliation.
    """
    with transaction.atomic():
        record = ReconciliationRecord.objects.create(
            account=account,
            statement_date=statement_date,
            statement_balance=statement_balance,
            reconciled_by=reconciled_by,
            notes=notes,
        )
        JournalLine.objects.filter(
            account=account,
            journal_entry__entry_date__lte=statement_date,
            journal_entry__status=JournalEntryStatus.POSTED,
            cleared=False,
        ).update(cleared=True)
    return record
