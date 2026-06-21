from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.budgets.models import Budget, BudgetPeriodType, Project, SavingsGoal
from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType, JournalEntry, JournalEntryStatus
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def test_budget_clean_rejects_account_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    other_account = Account.objects.create(
        entity=other_entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency="AUD"
    )
    budget = Budget(
        entity=entity, account=other_account, period_type=BudgetPeriodType.MONTHLY,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        budgeted_amount=Decimal("500"), created_by=user,
    )
    with pytest.raises(ValidationError):
        budget.full_clean()


def test_budget_period_end_before_start_violates_constraint():
    from django.db import IntegrityError, transaction

    entity = make_entity()
    user = make_user()
    account = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency="AUD"
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Budget.objects.create(
                entity=entity, account=account, period_type=BudgetPeriodType.MONTHLY,
                period_start=date(2026, 1, 31), period_end=date(2026, 1, 1),
                budgeted_amount=Decimal("500"), created_by=user,
            )


def test_savings_goal_clean_rejects_linked_account_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    other_account = Account.objects.create(
        entity=other_entity, account_type=AccountType.ASSET, name="Bank", native_currency="AUD"
    )
    goal = SavingsGoal(
        entity=entity, name="House deposit", target_amount=Decimal("50000"),
        target_date=date(2030, 1, 1), linked_account=other_account, created_by=user,
    )
    with pytest.raises(ValidationError):
        goal.full_clean()


def test_journal_entry_clean_rejects_project_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    other_project = Project.objects.create(
        entity=other_entity, name="Other project", budget_amount=Decimal("1000"),
        currency="AUD", created_by=user,
    )
    entry = JournalEntry(
        entity=entity, entry_date=date(2026, 1, 1), description="Test",
        status=JournalEntryStatus.POSTED, created_by=user, project=other_project,
    )
    with pytest.raises(ValidationError):
        entry.full_clean()
