from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.entities.models import Entity, EntityType
from apps.ledger.models import Account, AccountType
from apps.payroll.models import Payslip
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_user():
    return User.objects.create_user(email="u@example.com", password="x")


def make_payroll_accounts(entity, currency="AUD"):
    def acc(name, account_type):
        return Account.objects.create(entity=entity, name=name, account_type=account_type, native_currency=currency)

    return {
        "bank_account": acc("Bank", AccountType.ASSET),
        "income_account": acc("KCC Gross", AccountType.INCOME),
        "pretax_lease_expense_account": acc("Lease", AccountType.EXPENSE),
        "tax_expense_account": acc("PAYG Withheld", AccountType.EXPENSE),
        "fuel_card_expense_account": acc("Fuel Card Recovery", AccountType.EXPENSE),
        "social_club_expense_account": acc("Social Club", AccountType.EXPENSE),
        "cfmeu_expense_account": acc("CFMEU", AccountType.EXPENSE),
    }


def _base_fields(entity, accounts, **overrides):
    fields = dict(
        entity=entity,
        pay_period_start=date(2026, 1, 1),
        pay_period_end=date(2026, 1, 14),
        payment_date=date(2026, 1, 16),
        currency="AUD",
        gross_amount=Decimal("3000"),
        deduction_tax=Decimal("600"),
        deduction_fuel_card=Decimal("50"),
        deduction_social_club=Decimal("10"),
        deduction_cfmeu=Decimal("20"),
        deduction_pretax_lease=Decimal("200"),
        **accounts,
    )
    fields.update(overrides)
    return fields


def test_net_pay_mismatch_raises_validation_error():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)
    payslip = Payslip(
        **_base_fields(entity, accounts, net_pay=Decimal("9999")), created_by=user,
    )
    with pytest.raises(ValidationError):
        payslip.full_clean()


def test_correct_net_pay_passes_validation():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity)
    # 3000 - 200 - 600 - 50 - 10 - 20 = 2120
    payslip = Payslip(
        **_base_fields(entity, accounts, net_pay=Decimal("2120")), created_by=user,
    )
    payslip.full_clean()  # should not raise


def test_clean_rejects_account_from_different_entity():
    entity = make_entity()
    other_entity = make_entity("Other")
    user = make_user()
    accounts = make_payroll_accounts(entity)
    other_accounts = make_payroll_accounts(other_entity)
    accounts["bank_account"] = other_accounts["bank_account"]
    payslip = Payslip(
        **_base_fields(entity, accounts, net_pay=Decimal("2120")), created_by=user,
    )
    with pytest.raises(ValidationError):
        payslip.full_clean()


def test_clean_rejects_currency_mismatch():
    entity = make_entity()
    user = make_user()
    accounts = make_payroll_accounts(entity, currency="AUD")
    cny_income = Account.objects.create(
        entity=entity, name="CNY Income", account_type=AccountType.INCOME, native_currency="CNY"
    )
    accounts["income_account"] = cny_income
    payslip = Payslip(
        **_base_fields(entity, accounts, net_pay=Decimal("2120")), created_by=user,
    )
    with pytest.raises(ValidationError):
        payslip.full_clean()
