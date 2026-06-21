from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.budgets.models import Budget
from apps.budgets.services import compute_budget_progress
from apps.currencies.services import convert
from apps.ledger.models import (
    Account,
    AccountType,
    DebitCredit,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
)
from apps.ledger.services import get_account_balance, get_account_period_activity


@dataclass(frozen=True)
class TrialBalanceRow:
    account: Account
    debit_balance: Decimal | None
    credit_balance: Decimal | None


@dataclass(frozen=True)
class CurrencyTrialBalance:
    currency: str
    rows: list[TrialBalanceRow]
    total_debits: Decimal
    total_credits: Decimal


@dataclass(frozen=True)
class TrialBalanceReport:
    as_of: date
    currency_groups: list[CurrencyTrialBalance]


def compute_trial_balance(entity, *, as_of=None) -> TrialBalanceReport:
    """
    Every active account, grouped by native_currency, each row's signed
    get_account_balance() placed in the debit or credit column matching its
    normal_balance (no sign-flipping for "abnormal" balances -- kept
    simple). Within a single currency, total_debits == total_credits is
    mathematically guaranteed by the same per-currency balance invariant
    the deferred Postgres trigger enforces at write time -- this report
    doubles as a live sanity check of that invariant.
    """
    as_of = as_of or timezone.now().date()
    accounts = Account.objects.filter(entity=entity, is_active=True).order_by(
        "native_currency", "account_type", "name"
    )

    groups: dict[str, list[TrialBalanceRow]] = {}
    for account in accounts:
        balance = get_account_balance(account, as_of=as_of)
        if account.normal_balance == DebitCredit.DEBIT:
            row = TrialBalanceRow(account=account, debit_balance=balance, credit_balance=None)
        else:
            row = TrialBalanceRow(account=account, debit_balance=None, credit_balance=balance)
        groups.setdefault(account.native_currency, []).append(row)

    currency_groups = []
    for currency, rows in sorted(groups.items()):
        total_debits = sum((r.debit_balance for r in rows if r.debit_balance is not None), Decimal("0"))
        total_credits = sum((r.credit_balance for r in rows if r.credit_balance is not None), Decimal("0"))
        currency_groups.append(
            CurrencyTrialBalance(
                currency=currency, rows=rows, total_debits=total_debits, total_credits=total_credits
            )
        )
    return TrialBalanceReport(as_of=as_of, currency_groups=currency_groups)


@dataclass(frozen=True)
class BalanceSheetRow:
    account: Account
    amount: Decimal


@dataclass(frozen=True)
class BalanceSheetSection:
    rows: list[BalanceSheetRow]
    total: Decimal


@dataclass(frozen=True)
class BalanceSheetReport:
    as_of: date
    reporting_currency: str
    assets: BalanceSheetSection
    liabilities: BalanceSheetSection
    equity: BalanceSheetSection
    retained_earnings: Decimal
    total_assets: Decimal
    total_liabilities_and_equity: Decimal
    balances: bool


def _converted_balance(account, *, as_of, reporting_currency) -> Decimal:
    return convert(
        amount=get_account_balance(account, as_of=as_of),
        from_currency=account.native_currency,
        to_currency=reporting_currency,
        on_date=as_of,
    )


def _section(accounts, *, as_of, reporting_currency) -> BalanceSheetSection:
    rows = [
        BalanceSheetRow(
            account=account,
            amount=_converted_balance(account, as_of=as_of, reporting_currency=reporting_currency),
        )
        for account in accounts.order_by("name")
    ]
    total = sum((r.amount for r in rows), Decimal("0"))
    return BalanceSheetSection(rows=rows, total=total)


def compute_balance_sheet(entity, *, as_of=None, reporting_currency) -> BalanceSheetReport:
    """
    Assets / Liabilities / Equity as of a point in time, every account's
    balance translated to reporting_currency at the as_of spot rate (the
    standard "current rate" method for a snapshot). Equity gets one
    synthetic Retained Earnings row -- cumulative Income minus cumulative
    Expense since inception, converted the same way -- without it the
    sheet wouldn't balance. `balances` should always be True; it's exposed
    so a future bug becomes visible instead of silently wrong.
    """
    as_of = as_of or timezone.now().date()
    active = Account.objects.filter(entity=entity, is_active=True)

    assets = _section(active.filter(account_type=AccountType.ASSET), as_of=as_of, reporting_currency=reporting_currency)
    liabilities = _section(active.filter(account_type=AccountType.LIABILITY), as_of=as_of, reporting_currency=reporting_currency)
    equity_only = _section(active.filter(account_type=AccountType.EQUITY), as_of=as_of, reporting_currency=reporting_currency)

    income_total = sum(
        (
            _converted_balance(a, as_of=as_of, reporting_currency=reporting_currency)
            for a in active.filter(account_type=AccountType.INCOME)
        ),
        Decimal("0"),
    )
    expense_total = sum(
        (
            _converted_balance(a, as_of=as_of, reporting_currency=reporting_currency)
            for a in active.filter(account_type=AccountType.EXPENSE)
        ),
        Decimal("0"),
    )
    retained_earnings = income_total - expense_total

    total_assets = assets.total
    total_liabilities_and_equity = liabilities.total + equity_only.total + retained_earnings

    return BalanceSheetReport(
        as_of=as_of,
        reporting_currency=reporting_currency,
        assets=assets,
        liabilities=liabilities,
        equity=equity_only,
        retained_earnings=retained_earnings,
        total_assets=total_assets,
        total_liabilities_and_equity=total_liabilities_and_equity,
        balances=(total_assets == total_liabilities_and_equity),
    )


@dataclass(frozen=True)
class IncomeStatementRow:
    account: Account
    amount: Decimal


@dataclass(frozen=True)
class IncomeStatementSection:
    rows: list[IncomeStatementRow]
    total: Decimal


@dataclass(frozen=True)
class IncomeStatementReport:
    period_start: date
    period_end: date
    reporting_currency: str
    income: IncomeStatementSection
    expenses: IncomeStatementSection
    net_income: Decimal


def compute_income_statement(entity, *, period_start, period_end, reporting_currency) -> IncomeStatementReport:
    """
    Income minus Expenses over [period_start, period_end], each account's
    period activity (get_account_period_activity) translated to
    reporting_currency at the period-end spot rate -- a documented
    simplification vs. a true period-average rate (ExchangeRate only
    stores daily spot rates; no averaging service exists), consistent with
    other deliberate simplifications already made in this project (e.g.
    the superannuation projection).
    """
    active = Account.objects.filter(entity=entity, is_active=True)

    def section(account_type) -> IncomeStatementSection:
        rows = []
        for account in active.filter(account_type=account_type).order_by("name"):
            activity = get_account_period_activity(
                account, period_start=period_start, period_end=period_end
            )
            converted = convert(
                amount=activity,
                from_currency=account.native_currency,
                to_currency=reporting_currency,
                on_date=period_end,
            )
            rows.append(IncomeStatementRow(account=account, amount=converted))
        total = sum((r.amount for r in rows), Decimal("0"))
        return IncomeStatementSection(rows=rows, total=total)

    income = section(AccountType.INCOME)
    expenses = section(AccountType.EXPENSE)

    return IncomeStatementReport(
        period_start=period_start,
        period_end=period_end,
        reporting_currency=reporting_currency,
        income=income,
        expenses=expenses,
        net_income=income.total - expenses.total,
    )


@dataclass(frozen=True)
class AccountLedgerLine:
    entry_date: date
    description: str
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Decimal


@dataclass(frozen=True)
class AccountLedgerReport:
    account: Account
    period_start: date | None
    period_end: date | None
    opening_balance: Decimal
    lines: list[AccountLedgerLine]
    closing_balance: Decimal


def compute_account_ledger(account, *, period_start=None, period_end=None) -> AccountLedgerReport:
    """
    A single account's transaction history with a running balance --
    always shown in the account's own native currency (one account, one
    currency, no consolidation needed). opening_balance is the balance
    strictly before period_start (as_of the day before); with no
    period_start, the ledger starts from zero and shows full history.
    """
    if period_start is not None:
        opening_balance = get_account_balance(account, as_of=period_start - timedelta(days=1))
    else:
        opening_balance = Decimal("0")

    lines_qs = JournalLine.objects.filter(account=account).exclude(
        journal_entry__status=JournalEntryStatus.DRAFT
    )
    if period_start is not None:
        lines_qs = lines_qs.filter(journal_entry__entry_date__gte=period_start)
    if period_end is not None:
        lines_qs = lines_qs.filter(journal_entry__entry_date__lte=period_end)
    lines_qs = lines_qs.select_related("journal_entry").order_by(
        "journal_entry__entry_date", "journal_entry__created_at"
    )

    running = opening_balance
    ledger_lines = []
    sign = 1 if account.normal_balance == DebitCredit.DEBIT else -1
    for line in lines_qs:
        running += sign * (line.debit_amount - line.credit_amount)
        ledger_lines.append(
            AccountLedgerLine(
                entry_date=line.journal_entry.entry_date,
                description=line.journal_entry.description,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                running_balance=running,
            )
        )

    return AccountLedgerReport(
        account=account,
        period_start=period_start,
        period_end=period_end,
        opening_balance=opening_balance,
        lines=ledger_lines,
        closing_balance=running,
    )


@dataclass(frozen=True)
class BudgetVsActualRow:
    budget: Budget
    budgeted_amount: Decimal
    actual_amount: Decimal
    percent_used: Decimal | None
    budgeted_amount_converted: Decimal
    actual_amount_converted: Decimal


@dataclass(frozen=True)
class BudgetVsActualReport:
    reporting_currency: str
    rows: list[BudgetVsActualRow]
    total_budgeted_converted: Decimal
    total_actual_converted: Decimal
    overall_percent_used: Decimal | None


def compute_budget_vs_actual(entity, *, reporting_currency) -> BudgetVsActualReport:
    """
    Every Budget for the entity, reusing compute_budget_progress (step 7)
    directly rather than recomputing actuals here -- step 8's reporting
    layer calls step 7's building blocks, as planned. Each row keeps its
    own native currency for audit; a converted budgeted/actual pair (at
    the budget's own period-end spot rate) is added only to make the
    grand-total row meaningful across budgets in different currencies.
    """
    rows = []
    for budget in Budget.objects.filter(entity=entity).order_by("period_start", "account__name"):
        progress = compute_budget_progress(budget)
        currency = budget.account.native_currency
        budgeted_converted = convert(
            amount=progress.budgeted_amount,
            from_currency=currency,
            to_currency=reporting_currency,
            on_date=budget.period_end,
        )
        actual_converted = convert(
            amount=progress.actual_amount,
            from_currency=currency,
            to_currency=reporting_currency,
            on_date=budget.period_end,
        )
        rows.append(
            BudgetVsActualRow(
                budget=budget,
                budgeted_amount=progress.budgeted_amount,
                actual_amount=progress.actual_amount,
                percent_used=progress.percent_used,
                budgeted_amount_converted=budgeted_converted,
                actual_amount_converted=actual_converted,
            )
        )

    total_budgeted = sum((r.budgeted_amount_converted for r in rows), Decimal("0"))
    total_actual = sum((r.actual_amount_converted for r in rows), Decimal("0"))
    overall_percent_used = (total_actual / total_budgeted * 100) if total_budgeted != 0 else None

    return BudgetVsActualReport(
        reporting_currency=reporting_currency,
        rows=rows,
        total_budgeted_converted=total_budgeted,
        total_actual_converted=total_actual,
        overall_percent_used=overall_percent_used,
    )


class CashFlowCategory:
    OPERATING = "OPERATING"
    INVESTING = "INVESTING"
    FINANCING = "FINANCING"
    OTHER = "OTHER"


_OPERATING_TYPES = {AccountType.INCOME, AccountType.EXPENSE}
_FINANCING_TYPES = {AccountType.LIABILITY, AccountType.EQUITY}


def _classify_cash_flow(non_cash_lines) -> str:
    """
    A real indirect-method statement needs accrual concepts (current vs.
    non-current classification, AP/AR) this system deliberately doesn't
    model -- so this is a direct-method classification based on what each
    cash-touching entry's *other* lines are. If an entry's non-cash lines
    are a mix of categories, classifying it as any single one would be a
    guess, so it's surfaced honestly as OTHER instead.
    """
    types = {line.account.account_type for line in non_cash_lines}
    if types <= _OPERATING_TYPES:
        return CashFlowCategory.OPERATING
    if types == {AccountType.ASSET}:
        return CashFlowCategory.INVESTING
    if types <= _FINANCING_TYPES:
        return CashFlowCategory.FINANCING
    return CashFlowCategory.OTHER


@dataclass(frozen=True)
class CashFlowReport:
    period_start: date
    period_end: date
    reporting_currency: str
    opening_cash: Decimal
    operating_total: Decimal
    investing_total: Decimal
    financing_total: Decimal
    other_total: Decimal
    net_change: Decimal
    closing_cash: Decimal
    reconciles: bool


def compute_cash_flow_statement(entity, *, period_start, period_end, reporting_currency) -> CashFlowReport:
    """
    Direct-method cash flow statement over [period_start, period_end].
    `is_cash_equivalent=True` accounts define what counts as "cash" --
    account_type=ASSET alone can't distinguish a bank account from a
    property or superannuation balance. Entries with no non-cash line (a
    transfer between two cash accounts) are excluded entirely -- they
    don't change the entity's total cash position, so they aren't a "cash
    flow" in this statement's sense even though both legs touch cash.
    `reconciles` should always be True; exposed so a future bug becomes
    visible instead of silently wrong, same as `balances` on the balance
    sheet.
    """
    cash_accounts = Account.objects.filter(entity=entity, is_active=True, is_cash_equivalent=True)
    cash_account_ids = set(cash_accounts.values_list("id", flat=True))

    opening_cash = sum(
        (
            convert(
                amount=get_account_balance(a, as_of=period_start - timedelta(days=1)),
                from_currency=a.native_currency,
                to_currency=reporting_currency,
                on_date=period_start - timedelta(days=1),
            )
            for a in cash_accounts
        ),
        Decimal("0"),
    )
    closing_cash = sum(
        (
            convert(
                amount=get_account_balance(a, as_of=period_end),
                from_currency=a.native_currency,
                to_currency=reporting_currency,
                on_date=period_end,
            )
            for a in cash_accounts
        ),
        Decimal("0"),
    )

    totals = {
        CashFlowCategory.OPERATING: Decimal("0"),
        CashFlowCategory.INVESTING: Decimal("0"),
        CashFlowCategory.FINANCING: Decimal("0"),
        CashFlowCategory.OTHER: Decimal("0"),
    }

    entries = (
        JournalEntry.objects.filter(
            entity=entity,
            entry_date__gte=period_start,
            entry_date__lte=period_end,
            lines__account__in=cash_accounts,
        )
        .exclude(status=JournalEntryStatus.DRAFT)
        .distinct()
        .prefetch_related("lines__account")
    )

    for entry in entries:
        lines = list(entry.lines.all())
        cash_lines = [line for line in lines if line.account_id in cash_account_ids]
        non_cash_lines = [line for line in lines if line.account_id not in cash_account_ids]
        if not non_cash_lines:
            continue

        category = _classify_cash_flow(non_cash_lines)
        for line in cash_lines:
            signed = line.debit_amount - line.credit_amount
            converted = convert(
                amount=signed,
                from_currency=line.currency,
                to_currency=reporting_currency,
                on_date=entry.entry_date,
            )
            totals[category] += converted

    net_change = sum(totals.values(), Decimal("0"))

    return CashFlowReport(
        period_start=period_start,
        period_end=period_end,
        reporting_currency=reporting_currency,
        opening_cash=opening_cash,
        operating_total=totals[CashFlowCategory.OPERATING],
        investing_total=totals[CashFlowCategory.INVESTING],
        financing_total=totals[CashFlowCategory.FINANCING],
        other_total=totals[CashFlowCategory.OTHER],
        net_change=net_change,
        closing_cash=closing_cash,
        reconciles=(opening_cash + net_change == closing_cash),
    )


@dataclass(frozen=True)
class EntityNetWorthRow:
    entity: object
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


@dataclass(frozen=True)
class NetWorthReport:
    as_of: date
    reporting_currency: str
    rows: list[EntityNetWorthRow]
    consolidated_net_worth: Decimal


def compute_net_worth(entities, *, as_of=None, reporting_currency) -> NetWorthReport:
    """
    Per the brief's "family net worth rollup... across all entities the
    logged-in user has access to" -- the one report not scoped to a
    single entity. `entities` must already be access-filtered by the
    caller (the view resolves via Entity.objects.accessible_by(user)).
    Each entity's net worth is assets minus liabilities, both converted
    via the same _converted_balance helper the balance sheet uses.
    """
    as_of = as_of or timezone.now().date()
    rows = []
    for entity in entities:
        active = Account.objects.filter(entity=entity, is_active=True)
        total_assets = sum(
            (
                _converted_balance(a, as_of=as_of, reporting_currency=reporting_currency)
                for a in active.filter(account_type=AccountType.ASSET)
            ),
            Decimal("0"),
        )
        total_liabilities = sum(
            (
                _converted_balance(a, as_of=as_of, reporting_currency=reporting_currency)
                for a in active.filter(account_type=AccountType.LIABILITY)
            ),
            Decimal("0"),
        )
        rows.append(
            EntityNetWorthRow(
                entity=entity,
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                net_worth=total_assets - total_liabilities,
            )
        )

    consolidated_net_worth = sum((r.net_worth for r in rows), Decimal("0"))
    return NetWorthReport(
        as_of=as_of,
        reporting_currency=reporting_currency,
        rows=rows,
        consolidated_net_worth=consolidated_net_worth,
    )
