from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
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
    DebitCredit,
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


def post_journal_entry(
    *, entity, entry_date, description, lines, created_by, memo="", project=None
):
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
            project=project,
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
    project=None,
):
    """Convenience wrapper for the common 2-line case (e.g. an expense paid from a bank account)."""
    return post_journal_entry(
        entity=entity,
        entry_date=entry_date,
        description=description,
        memo=memo,
        created_by=created_by,
        project=project,
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
            # Propagate the project tag so a reversed entry's correction
            # nets out within the same project's accounting too, not just
            # the general ledger -- otherwise compute_project_actuals would
            # see the original's REVERSED cost but never the reversal's
            # offsetting effect (it'd belong to no project at all).
            project=entry.project,
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


def get_account_balance(account, *, as_of=None, include_descendants=False) -> Decimal:
    """
    Sum of this account's real JournalLine activity, signed so that a
    positive result always means "more of the account's normal_balance
    side" -- e.g. positive for an ASSET account means more debits than
    credits (money in), positive for a LIABILITY/EQUITY/INCOME account
    means more credits than debits. Only DRAFT entries are excluded --
    REVERSED entries must still count, because a reversal only nets out
    correctly if both the original (now REVERSED) and its offsetting
    POSTED reversal are included; excluding REVERSED would count only
    half of a cancel-out pair and silently corrupt the balance. `cleared`
    is not considered here -- that's a reconciliation concept (step 6),
    not a balance concept. as_of=None means all-time; pass a date to get
    the balance as of (inclusive of) that date.

    include_descendants=False by default: callers wanting `account` plus
    its direct children (e.g. a parent "Groceries" category) must opt in
    explicitly. One level of children only, matching how deep the existing
    hierarchy is actually used.
    """
    if include_descendants:
        accounts = Account.objects.filter(Q(pk=account.pk) | Q(parent=account.pk))
        mismatched = accounts.exclude(native_currency=account.native_currency)
        if mismatched.exists():
            raise CurrencyMismatchError(
                f"Cannot aggregate '{account}' with descendants of a different native_currency."
            )
    else:
        accounts = Account.objects.filter(pk=account.pk)

    lines = JournalLine.objects.filter(account__in=accounts).exclude(
        journal_entry__status=JournalEntryStatus.DRAFT
    )
    if as_of is not None:
        lines = lines.filter(journal_entry__entry_date__lte=as_of)

    totals = lines.aggregate(
        debit=Coalesce(Sum("debit_amount"), Decimal("0")),
        credit=Coalesce(Sum("credit_amount"), Decimal("0")),
    )
    if account.normal_balance == DebitCredit.DEBIT:
        return totals["debit"] - totals["credit"]
    return totals["credit"] - totals["debit"]
