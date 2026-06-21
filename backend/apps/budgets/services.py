from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.budgets.exceptions import InvalidProjectionParametersError
from apps.budgets.models import Budget, Project, SavingsGoal
from apps.currencies.services import convert
from apps.ledger.models import Account, AccountType, DebitCredit, JournalEntryStatus, JournalLine
from apps.ledger.services import get_account_balance


@dataclass(frozen=True)
class BudgetProgress:
    budget: Budget
    budgeted_amount: Decimal
    actual_amount: Decimal
    remaining_amount: Decimal
    percent_used: Decimal | None


def compute_budget_actual(budget: Budget) -> Decimal:
    """
    Sums JournalLines on budget.account (plus its direct children if
    budget.include_descendants) dated within [period_start, period_end]
    inclusive, signed per the account's normal_balance -- an EXPENSE
    budget's "actual" is debits minus credits, so a refund/credit-note
    correctly reduces actual spend rather than netting against unrelated
    debits blindly. Only DRAFT entries are excluded -- a REVERSED entry
    must still count alongside its offsetting POSTED reversal, or only
    half of a cancel-out pair would be counted (same reasoning as
    get_account_balance). This is a bounded-period sum, distinct from
    get_account_balance's all-time as-of balance -- the two answer
    different questions and are kept as separate functions deliberately.
    """
    accounts = (
        Account.objects.filter(Q(pk=budget.account_id) | Q(parent=budget.account_id))
        if budget.include_descendants
        else Account.objects.filter(pk=budget.account_id)
    )
    lines = (
        JournalLine.objects.filter(
            account__in=accounts,
            journal_entry__entry_date__gte=budget.period_start,
            journal_entry__entry_date__lte=budget.period_end,
        )
        .exclude(journal_entry__status=JournalEntryStatus.DRAFT)
    )
    totals = lines.aggregate(
        debit=Coalesce(Sum("debit_amount"), Decimal("0")),
        credit=Coalesce(Sum("credit_amount"), Decimal("0")),
    )
    if budget.account.normal_balance == DebitCredit.DEBIT:
        return totals["debit"] - totals["credit"]
    return totals["credit"] - totals["debit"]


def compute_budget_progress(budget: Budget) -> BudgetProgress:
    actual = compute_budget_actual(budget)
    remaining = budget.budgeted_amount - actual
    percent_used = (
        (actual / budget.budgeted_amount * 100) if budget.budgeted_amount != 0 else None
    )
    return BudgetProgress(
        budget=budget,
        budgeted_amount=budget.budgeted_amount,
        actual_amount=actual,
        remaining_amount=remaining,
        percent_used=percent_used,
    )


@dataclass(frozen=True)
class SavingsGoalProgress:
    goal: SavingsGoal
    current_balance: Decimal
    target_amount: Decimal
    remaining_amount: Decimal
    percent_complete: Decimal | None
    days_remaining: int


def compute_savings_goal_progress(goal: SavingsGoal, *, as_of: date | None = None) -> SavingsGoalProgress:
    """
    current_balance is get_account_balance(goal.linked_account) -- no
    currency conversion; the goal and its linked account are assumed to
    share a currency (see model docstring). days_remaining may be
    negative if target_date has already passed.
    """
    today = as_of or timezone.now().date()
    current_balance = get_account_balance(goal.linked_account)
    remaining = goal.target_amount - current_balance
    percent_complete = (
        (current_balance / goal.target_amount * 100) if goal.target_amount != 0 else None
    )
    return SavingsGoalProgress(
        goal=goal,
        current_balance=current_balance,
        target_amount=goal.target_amount,
        remaining_amount=remaining,
        percent_complete=percent_complete,
        days_remaining=(goal.target_date - today).days,
    )


@dataclass(frozen=True)
class ProjectProgress:
    project: Project
    actual_to_date: Decimal
    budget_amount: Decimal
    remaining_amount: Decimal
    percent_used: Decimal | None


def compute_project_actuals(project: Project) -> ProjectProgress:
    """
    actual_to_date sums only the EXPENSE-side lines of every non-DRAFT
    JournalEntry tagged project=project (POSTED and REVERSED both count,
    same reasoning as get_account_balance -- a REVERSED entry's cost must
    still count alongside its offsetting POSTED reversal, or the
    cancellation wouldn't net to zero), converted to project.currency
    using each line's own entry date (not today) via
    apps.currencies.services.convert -- a historical cost converts at the
    rate that applied when it was incurred.

    Deliberately excludes ASSET/LIABILITY/EQUITY/INCOME-side lines of a
    tagged entry: a project-tagged entry like "pay $5000 for visa fees"
    has two lines (debit Visa Fees [EXPENSE], credit Bank [ASSET]) --
    counting both would double the apparent cost. An asset purchase
    tagged to a project (e.g. furniture for a new house) is not counted
    as project cost under this default -- capex isn't opex. This is a
    documented trade-off, not an oversight; revisit per-project if a real
    need (e.g. capitalized equipment) comes up.

    remaining_amount ("forecast-remaining" in the brief's wording) is
    plain budget_amount - actual_to_date -- arithmetic, not a predictive
    model.
    """
    entries = project.journal_entries.exclude(status=JournalEntryStatus.DRAFT)
    expense_lines = JournalLine.objects.filter(
        journal_entry__in=entries, account__account_type=AccountType.EXPENSE
    ).select_related("journal_entry", "account")

    total = Decimal("0")
    for line in expense_lines:
        signed = line.debit_amount - line.credit_amount
        converted = convert(
            amount=signed,
            from_currency=line.currency,
            to_currency=project.currency,
            on_date=line.journal_entry.entry_date,
        )
        total += converted

    remaining = project.budget_amount - total
    percent_used = (total / project.budget_amount * 100) if project.budget_amount != 0 else None
    return ProjectProgress(
        project=project,
        actual_to_date=total,
        budget_amount=project.budget_amount,
        remaining_amount=remaining,
        percent_used=percent_used,
    )


def project_superannuation_balance(
    *,
    current_balance: Decimal,
    target_date: date,
    annual_contribution: Decimal,
    annual_growth_rate: Decimal,
    as_of: date | None = None,
) -> Decimal:
    """
    Simple annual-compounding projection -- NOT a financial-advice engine,
    NOT inflation- or tax-adjusted. Stateless: no assumptions are
    persisted anywhere, this is a pure calculator.

        years = (target_date - as_of).days / 365.25
        FV = current_balance * (1 + r) ** years
           + annual_contribution * (((1 + r) ** years - 1) / r)   [r != 0]
           + annual_contribution * years                            [r == 0]

    where r = annual_growth_rate (e.g. Decimal("0.07") for 7%), assuming a
    steady annual contribution stream (an ordinary-annuity approximation,
    not modeling actual contribution timing/frequency). Raises
    InvalidProjectionParametersError if target_date is on or before as_of.
    """
    today = as_of or timezone.now().date()
    if target_date <= today:
        raise InvalidProjectionParametersError("target_date must be after as_of.")

    years = Decimal((target_date - today).days) / Decimal("365.25")
    r = annual_growth_rate

    # Decimal ** Decimal with a fractional exponent is unreliable for this
    # purpose; this is an illustrative projection (not a posted ledger
    # amount), so a float round-trip for just the exponentiation step is
    # an acceptable, deliberate exception to "Decimal never float for
    # money" -- that rule is about ledger amounts, not back-of-envelope
    # projections.
    growth_factor = Decimal(str((1 + float(r)) ** float(years)))

    fv_lump_sum = current_balance * growth_factor
    if r != 0:
        fv_contributions = annual_contribution * ((growth_factor - 1) / r)
    else:
        fv_contributions = annual_contribution * years

    return (fv_lump_sum + fv_contributions).quantize(Decimal("0.0001"))
