from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.budgets.exceptions import InvalidProjectionParametersError
from apps.budgets.models import Budget, BudgetPeriodType, Project, SavingsGoal
from apps.budgets.services import (
    compute_budget_actual,
    compute_budget_progress,
    compute_project_actuals,
    compute_savings_goal_progress,
    project_superannuation_balance,
)
from apps.currencies.models import ExchangeRate
from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType
from apps.ledger.services import record_simple_transaction
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


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


def test_compute_budget_actual_sums_debits_for_expense_account():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("60")


def test_compute_budget_actual_nets_credit_notes_against_expense_debits():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )
    # A refund: credit the expense account, debit the bank back.
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 10), description="Refund",
        debit_account=bank, credit_account=groceries, amount=Decimal("20"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("40")


def test_compute_budget_actual_respects_period_boundaries_inclusive():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="In range start",
        debit_account=groceries, credit_account=bank, amount=Decimal("10"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 31), description="In range end",
        debit_account=groceries, credit_account=bank, amount=Decimal("20"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 2, 1), description="Out of range",
        debit_account=groceries, credit_account=bank, amount=Decimal("99"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("30")


def test_compute_budget_actual_include_descendants_rolls_up_child_accounts():
    entity = make_entity()
    user = make_user()
    bank, _ = make_accounts(entity)
    expenses = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Expenses", native_currency="AUD"
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries",
        native_currency="AUD", parent=expenses,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=expenses, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), include_descendants=True, created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("60")


def test_compute_budget_actual_excludes_descendants_when_flag_false():
    entity = make_entity()
    user = make_user()
    bank, _ = make_accounts(entity)
    expenses = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Expenses", native_currency="AUD"
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries",
        native_currency="AUD", parent=expenses,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=expenses, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), include_descendants=False, created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("0")


def test_compute_budget_progress_percent_used_none_when_budget_zero():
    entity = make_entity()
    user = make_user()
    _, groceries = make_accounts(entity)
    budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("0"), created_by=user,
    )
    progress = compute_budget_progress(budget)
    assert progress.percent_used is None


def test_compute_savings_goal_progress_matches_account_balance():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Deposit",
        debit_account=bank, credit_account=groceries, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    goal = SavingsGoal.objects.create(
        entity=entity, name="House deposit", target_amount=Decimal("50000"),
        target_date=date(2030, 3, 1), linked_account=bank, created_by=user,
    )
    progress = compute_savings_goal_progress(goal, as_of=date(2026, 1, 2))
    assert progress.current_balance == Decimal("1000")
    assert progress.remaining_amount == Decimal("49000")


def test_compute_savings_goal_progress_days_remaining_for_long_horizon_date():
    entity = make_entity()
    user = make_user()
    bank, _ = make_accounts(entity)
    goal = SavingsGoal.objects.create(
        entity=entity, name="Migration fund", target_amount=Decimal("20000"),
        target_date=date(2030, 1, 1), linked_account=bank, created_by=user,
    )
    progress = compute_savings_goal_progress(goal, as_of=date(2026, 6, 20))
    expected_days = (date(2030, 1, 1) - date(2026, 6, 20)).days
    assert progress.days_remaining == expected_days
    assert expected_days > 365 * 3  # genuinely multi-year


def test_compute_project_actuals_sums_only_expense_lines_excludes_asset_lines():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    project = Project.objects.create(
        entity=entity, name="China migration costs", budget_amount=Decimal("5000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Visa fees",
        debit_account=groceries, credit_account=bank, amount=Decimal("300"),
        currency="AUD", created_by=user, project=project,
    )
    progress = compute_project_actuals(project)
    # Only the EXPENSE-side (debit groceries 300) counts; the ASSET-side
    # (credit bank 300) must not also be summed, or it would double.
    assert progress.actual_to_date == Decimal("300")


def test_compute_project_actuals_converts_cross_currency_lines_at_entry_date_rate():
    entity = make_entity()
    user = make_user()
    cny_bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="China Bank", native_currency="CNY"
    )
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="China Expenses", native_currency="CNY"
    )
    project = Project.objects.create(
        entity=entity, name="China migration costs", budget_amount=Decimal("5000"),
        currency="AUD", created_by=user,
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="CNY", to_currency="AUD", rate=Decimal("0.21")
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Apartment deposit",
        debit_account=cny_expense, credit_account=cny_bank, amount=Decimal("1000"),
        currency="CNY", created_by=user, project=project,
    )
    progress = compute_project_actuals(project)
    assert progress.actual_to_date == Decimal("210.0000")


def test_compute_project_actuals_forecast_remaining_is_simple_subtraction():
    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    project = Project.objects.create(
        entity=entity, name="Documentary costs", budget_amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Camera rental",
        debit_account=groceries, credit_account=bank, amount=Decimal("400"),
        currency="AUD", created_by=user, project=project,
    )
    progress = compute_project_actuals(project)
    assert progress.remaining_amount == Decimal("600")


def test_project_superannuation_balance_matches_hand_computed_value():
    as_of = date(2026, 1, 1)
    target_date = as_of + timedelta(days=round(5 * 365.25))
    result = project_superannuation_balance(
        current_balance=Decimal("50000"),
        target_date=target_date,
        annual_contribution=Decimal("10000"),
        annual_growth_rate=Decimal("0.07"),
        as_of=as_of,
    )
    # Hand-computed FV for ~5 years at 7%: lump sum 50000*(1.07^5) plus
    # annuity 10000*((1.07^5 - 1)/0.07) ~= 127635. Allow tolerance for the
    # day-count-based fractional-year rounding (target_date isn't exactly
    # 5*365.25 days due to integer day rounding).
    expected = Decimal("127635")
    assert abs(result - expected) < Decimal("100")


def test_project_superannuation_balance_zero_growth_rate_uses_linear_contribution_sum():
    as_of = date(2026, 1, 1)
    target_date = as_of + timedelta(days=round(5 * 365.25))
    result = project_superannuation_balance(
        current_balance=Decimal("50000"),
        target_date=target_date,
        annual_contribution=Decimal("10000"),
        annual_growth_rate=Decimal("0"),
        as_of=as_of,
    )
    # No growth: FV = current_balance + annual_contribution * years
    expected = Decimal("50000") + Decimal("10000") * 5
    assert abs(result - expected) < Decimal("10")


def test_project_superannuation_balance_raises_for_past_target_date():
    with pytest.raises(InvalidProjectionParametersError):
        project_superannuation_balance(
            current_balance=Decimal("50000"),
            target_date=date(2020, 1, 1),
            annual_contribution=Decimal("10000"),
            annual_growth_rate=Decimal("0.07"),
            as_of=date(2026, 1, 1),
        )


def test_compute_budget_actual_nets_to_zero_after_reversal():
    from apps.ledger.services import reverse_journal_entry

    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("60"),
        currency="AUD", created_by=user,
    )
    budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("200"), created_by=user,
    )
    assert compute_budget_actual(budget) == Decimal("60")
    # Backdate the reversal into the same period being tested -- by default
    # reverse_journal_entry dates the reversal "today" (correct: a
    # correction made later is recorded when it happened, not retroactively
    # backdated), which would otherwise fall outside this budget's period.
    reverse_journal_entry(
        entry=entry, reversed_by_user=user, reversal_date=date(2026, 1, 20)
    )
    # The REVERSED original must still count alongside its POSTED reversal,
    # or only half of the cancel-out pair would be counted.
    assert compute_budget_actual(budget) == Decimal("0")


def test_compute_project_actuals_nets_to_zero_after_reversal():
    from apps.ledger.services import post_journal_entry, reverse_journal_entry
    from apps.ledger.services import JournalLineInput

    entity = make_entity()
    user = make_user()
    bank, groceries = make_accounts(entity)
    project = Project.objects.create(
        entity=entity, name="Documentary costs", budget_amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    entry = post_journal_entry(
        entity=entity, entry_date=date(2026, 1, 1), description="Camera rental",
        created_by=user, project=project,
        lines=[
            JournalLineInput(account=groceries, currency="AUD", debit_amount=Decimal("400")),
            JournalLineInput(account=bank, currency="AUD", credit_amount=Decimal("400")),
        ],
    )
    assert compute_project_actuals(project).actual_to_date == Decimal("400")
    reverse_journal_entry(entry=entry, reversed_by_user=user)
    assert compute_project_actuals(project).actual_to_date == Decimal("0")
