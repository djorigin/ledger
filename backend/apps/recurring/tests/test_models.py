from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType
from apps.recurring.models import RecurrenceFrequency, RecurringTransactionTemplate
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


def test_template_clean_rejects_account_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    bank, _ = make_accounts(entity)
    _, other_expense = make_accounts(other_entity)

    template = RecurringTransactionTemplate(
        entity=entity, description="Mortgage", debit_account=other_expense, credit_account=bank,
        amount=Decimal("2000"), currency="AUD", frequency=RecurrenceFrequency.MONTHLY,
        start_date=date(2026, 1, 1), next_due_date=date(2026, 1, 1), created_by=user,
    )
    with pytest.raises(ValidationError):
        template.full_clean()


def test_template_clean_rejects_currency_mismatch():
    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity, currency="AUD")
    cny_expense = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="CNY Expense", native_currency="CNY"
    )

    template = RecurringTransactionTemplate(
        entity=entity, description="Mortgage", debit_account=cny_expense, credit_account=bank,
        amount=Decimal("2000"), currency="AUD", frequency=RecurrenceFrequency.MONTHLY,
        start_date=date(2026, 1, 1), next_due_date=date(2026, 1, 1), created_by=user,
    )
    with pytest.raises(ValidationError):
        template.full_clean()


def test_template_clean_rejects_same_debit_and_credit_account():
    entity = make_entity()
    user = make_user()
    bank, _ = make_accounts(entity)

    template = RecurringTransactionTemplate(
        entity=entity, description="Mortgage", debit_account=bank, credit_account=bank,
        amount=Decimal("2000"), currency="AUD", frequency=RecurrenceFrequency.MONTHLY,
        start_date=date(2026, 1, 1), next_due_date=date(2026, 1, 1), created_by=user,
    )
    with pytest.raises(ValidationError):
        template.full_clean()


def test_pending_entry_unique_per_template_and_due_date():
    from django.db import IntegrityError, transaction

    from apps.recurring.models import PendingRecurringEntry

    entity = make_entity()
    user = make_user()
    bank, expense = make_accounts(entity)
    template = RecurringTransactionTemplate.objects.create(
        entity=entity, description="Mortgage", debit_account=expense, credit_account=bank,
        amount=Decimal("2000"), currency="AUD", frequency=RecurrenceFrequency.MONTHLY,
        start_date=date(2026, 1, 1), next_due_date=date(2026, 1, 1), created_by=user,
    )
    PendingRecurringEntry.objects.create(template=template, due_date=date(2026, 1, 1), amount=Decimal("2000"))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PendingRecurringEntry.objects.create(
                template=template, due_date=date(2026, 1, 1), amount=Decimal("2000")
            )
