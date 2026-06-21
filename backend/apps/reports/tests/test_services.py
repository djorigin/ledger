from datetime import date
from decimal import Decimal

import pytest

from apps.budgets.models import Budget, BudgetPeriodType
from apps.currencies.models import ExchangeRate
from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType
from apps.ledger.services import record_simple_transaction, reverse_journal_entry
from apps.reports.services import (
    compute_account_ledger,
    compute_balance_sheet,
    compute_budget_vs_actual,
    compute_cash_flow_statement,
    compute_income_statement,
    compute_net_worth,
    compute_trial_balance,
)
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
    salary = Account.objects.create(
        entity=entity, account_type=AccountType.INCOME, name="Salary", native_currency="AUD"
    )
    return bank, groceries, salary


def test_trial_balance_groups_by_currency_and_debits_equal_credits():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    cny_bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="CNY Bank", native_currency="CNY"
    )
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="CNY Expense", native_currency="CNY"
    )
    cny_salary = Account.objects.create(
        entity=entity, account_type=AccountType.INCOME, name="CNY Salary", native_currency="CNY"
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Pay",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="CNY funding",
        debit_account=cny_bank, credit_account=cny_salary, amount=Decimal("500"),
        currency="CNY", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="CNY spend",
        debit_account=cny_expense, credit_account=cny_bank, amount=Decimal("500"),
        currency="CNY", created_by=user,
    )

    report = compute_trial_balance(entity, as_of=date(2026, 1, 31))
    by_currency = {g.currency: g for g in report.currency_groups}

    assert by_currency["AUD"].total_debits == by_currency["AUD"].total_credits
    assert by_currency["CNY"].total_debits == by_currency["CNY"].total_credits
    assert by_currency["AUD"].total_debits == Decimal("1000")
    assert by_currency["CNY"].total_debits == Decimal("500")


def test_trial_balance_nets_to_zero_after_reversal():
    entity = make_entity()
    user = make_user()
    bank, groceries, _ = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50"),
        currency="AUD", created_by=user,
    )
    reverse_journal_entry(entry=entry, reversed_by_user=user, reversal_date=date(2026, 1, 6))

    report = compute_trial_balance(entity, as_of=date(2026, 1, 31))
    aud = next(g for g in report.currency_groups if g.currency == "AUD")
    assert aud.total_debits == aud.total_credits == Decimal("0")


def test_balance_sheet_balances_single_currency():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Pay",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )

    report = compute_balance_sheet(entity, as_of=date(2026, 1, 31), reporting_currency="AUD")
    assert report.balances is True
    assert report.total_assets == Decimal("800")
    assert report.retained_earnings == Decimal("800")  # 1000 income - 200 expense


def test_balance_sheet_balances_with_multi_currency_accounts():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    cny_bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="CNY Bank", native_currency="CNY"
    )
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="CNY Expense", native_currency="CNY"
    )
    cny_salary = Account.objects.create(
        entity=entity, account_type=AccountType.INCOME, name="CNY Salary", native_currency="CNY"
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="CNY", to_currency="AUD", rate=Decimal("0.2")
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Pay",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="CNY funding",
        debit_account=cny_bank, credit_account=cny_salary, amount=Decimal("500"),
        currency="CNY", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="CNY spend",
        debit_account=cny_expense, credit_account=cny_bank, amount=Decimal("100"),
        currency="CNY", created_by=user,
    )

    report = compute_balance_sheet(entity, as_of=date(2026, 1, 31), reporting_currency="AUD")
    assert report.balances is True


def test_balance_sheet_balances_after_reversal():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Pay",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )
    reverse_journal_entry(entry=entry, reversed_by_user=user, reversal_date=date(2026, 1, 10))

    report = compute_balance_sheet(entity, as_of=date(2026, 1, 31), reporting_currency="AUD")
    assert report.balances is True
    assert report.total_assets == Decimal("1000")
    assert report.retained_earnings == Decimal("1000")


def test_income_statement_period_boundaries_and_net_income():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Pay",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="January groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 2, 1), description="February groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("80"),
        currency="AUD", created_by=user,
    )

    report = compute_income_statement(
        entity, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), reporting_currency="AUD"
    )
    assert report.income.total == Decimal("1000")
    assert report.expenses.total == Decimal("200")
    assert report.net_income == Decimal("800")


def test_account_ledger_running_balance_with_opening_balance():
    entity = make_entity()
    user = make_user()
    bank, groceries, _ = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Opening month spend",
        debit_account=groceries, credit_account=bank, amount=Decimal("50"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 2, 5), description="Feb groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("30"),
        currency="AUD", created_by=user,
    )

    report = compute_account_ledger(
        groceries, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28)
    )
    assert report.opening_balance == Decimal("50")
    assert len(report.lines) == 1
    assert report.lines[0].running_balance == Decimal("80")
    assert report.closing_balance == Decimal("80")


def test_account_ledger_without_period_starts_from_zero():
    entity = make_entity()
    user = make_user()
    bank, groceries, _ = make_accounts(entity)
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Spend",
        debit_account=groceries, credit_account=bank, amount=Decimal("50"),
        currency="AUD", created_by=user,
    )
    report = compute_account_ledger(groceries)
    assert report.opening_balance == Decimal("0")
    assert report.closing_balance == Decimal("50")


def test_budget_vs_actual_aggregates_across_currencies():
    entity = make_entity()
    user = make_user()
    bank, groceries, _ = make_accounts(entity)
    cny_bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="CNY Bank", native_currency="CNY"
    )
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="CNY Expense", native_currency="CNY"
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="CNY", to_currency="AUD", rate=Decimal("0.2")
    )
    aud_budget = Budget.objects.create(
        entity=entity, account=groceries, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("500"), created_by=user,
    )
    cny_budget = Budget.objects.create(
        entity=entity, account=cny_expense, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("1000"), created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("100"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="CNY spend",
        debit_account=cny_expense, credit_account=cny_bank, amount=Decimal("200"),
        currency="CNY", created_by=user,
    )

    report = compute_budget_vs_actual(entity, reporting_currency="AUD")
    assert {r.budget.id for r in report.rows} == {aud_budget.id, cny_budget.id}
    # 500 AUD + (1000 CNY * 0.2) = 700 budgeted; 100 AUD + (200 CNY * 0.2) = 140 actual
    assert report.total_budgeted_converted == Decimal("700")
    assert report.total_actual_converted == Decimal("140")


def test_cash_flow_classifies_operating_investing_financing():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    bank.is_cash_equivalent = True
    bank.save()
    property_account = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Property", native_currency="AUD"
    )
    mortgage = Account.objects.create(
        entity=entity, account_type=AccountType.LIABILITY, name="Mortgage", native_currency="AUD"
    )

    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Salary",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 10), description="Buy land",
        debit_account=property_account, credit_account=bank, amount=Decimal("300"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 15), description="Mortgage draw",
        debit_account=bank, credit_account=mortgage, amount=Decimal("500"),
        currency="AUD", created_by=user,
    )

    report = compute_cash_flow_statement(
        entity, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), reporting_currency="AUD"
    )
    assert report.operating_total == Decimal("800")  # +1000 salary - 200 groceries
    assert report.investing_total == Decimal("-300")  # bought property
    assert report.financing_total == Decimal("500")  # mortgage draw
    assert report.other_total == Decimal("0")
    assert report.net_change == Decimal("1000")
    assert report.reconciles is True


def test_cash_flow_excludes_internal_transfer_between_cash_accounts():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    bank.is_cash_equivalent = True
    bank.save()
    savings = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Savings",
        native_currency="AUD", is_cash_equivalent=True,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Move to savings",
        debit_account=savings, credit_account=bank, amount=Decimal("400"),
        currency="AUD", created_by=user,
    )

    report = compute_cash_flow_statement(
        entity, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), reporting_currency="AUD"
    )
    assert report.operating_total == report.investing_total == report.financing_total == Decimal("0")
    assert report.net_change == Decimal("0")
    assert report.reconciles is True


def test_cash_flow_reconciles_after_reversal():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    bank.is_cash_equivalent = True
    bank.save()
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("200"),
        currency="AUD", created_by=user,
    )
    reverse_journal_entry(entry=entry, reversed_by_user=user, reversal_date=date(2026, 1, 10))

    report = compute_cash_flow_statement(
        entity, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), reporting_currency="AUD"
    )
    assert report.operating_total == Decimal("0")
    assert report.net_change == Decimal("0")
    assert report.reconciles is True


def test_net_worth_single_entity_matches_assets_minus_liabilities():
    entity = make_entity()
    user = make_user()
    bank, groceries, salary = make_accounts(entity)
    mortgage = Account.objects.create(
        entity=entity, account_type=AccountType.LIABILITY, name="Mortgage", native_currency="AUD"
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 1), description="Salary",
        debit_account=bank, credit_account=salary, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity, entry_date=date(2026, 1, 5), description="Draw",
        debit_account=bank, credit_account=mortgage, amount=Decimal("300"),
        currency="AUD", created_by=user,
    )

    report = compute_net_worth([entity], as_of=date(2026, 1, 31), reporting_currency="AUD")
    row = report.rows[0]
    assert row.total_assets == Decimal("1300")
    assert row.total_liabilities == Decimal("300")
    assert row.net_worth == Decimal("1000")
    assert report.consolidated_net_worth == Decimal("1000")


def test_net_worth_consolidates_across_entities_in_different_currencies():
    entity_a = make_entity("Household")
    entity_b = make_entity("Business")
    user = make_user()
    bank_a, groceries_a, salary_a = make_accounts(entity_a)
    bank_b = Account.objects.create(
        entity=entity_b, account_type=AccountType.ASSET, name="CNY Bank", native_currency="CNY"
    )
    salary_b = Account.objects.create(
        entity=entity_b, account_type=AccountType.INCOME, name="CNY Income", native_currency="CNY"
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="CNY", to_currency="AUD", rate=Decimal("0.2")
    )
    record_simple_transaction(
        entity=entity_a, entry_date=date(2026, 1, 1), description="Salary",
        debit_account=bank_a, credit_account=salary_a, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    record_simple_transaction(
        entity=entity_b, entry_date=date(2026, 1, 1), description="Income",
        debit_account=bank_b, credit_account=salary_b, amount=Decimal("500"),
        currency="CNY", created_by=user,
    )

    report = compute_net_worth(
        [entity_a, entity_b], as_of=date(2026, 1, 31), reporting_currency="AUD"
    )
    assert len(report.rows) == 2
    # 1000 AUD + (500 CNY * 0.2) = 1100 AUD
    assert report.consolidated_net_worth == Decimal("1100")


def test_net_worth_excludes_entities_not_passed_in():
    entity_a = make_entity("Household")
    entity_b = make_entity("Other family's entity")
    user = make_user()
    bank_a, groceries_a, salary_a = make_accounts(entity_a)
    record_simple_transaction(
        entity=entity_a, entry_date=date(2026, 1, 1), description="Salary",
        debit_account=bank_a, credit_account=salary_a, amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    # entity_b has no accounts/transactions and is simply not passed in --
    # simulates a user without access to it.
    report = compute_net_worth([entity_a], as_of=date(2026, 1, 31), reporting_currency="AUD")
    assert len(report.rows) == 1
    assert report.rows[0].entity == entity_a
