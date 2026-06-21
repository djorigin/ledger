from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.ledger.constants import validate_currency_code


# --- query param validation -------------------------------------------------


class TrialBalanceQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    as_of = serializers.DateField(required=False)


class BalanceSheetQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    as_of = serializers.DateField(required=False)
    reporting_currency = serializers.CharField(validators=[validate_currency_code])


class IncomeStatementQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    reporting_currency = serializers.CharField(validators=[validate_currency_code])


class AccountLedgerQuerySerializer(serializers.Serializer):
    account = serializers.UUIDField()
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)


class BudgetVsActualQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    reporting_currency = serializers.CharField(validators=[validate_currency_code])


# --- output shapes -----------------------------------------------------------


class TrialBalanceRowSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    debit_balance = MoneyField(allow_null=True)
    credit_balance = MoneyField(allow_null=True)


class CurrencyTrialBalanceSerializer(serializers.Serializer):
    currency = serializers.CharField()
    rows = TrialBalanceRowSerializer(many=True)
    total_debits = MoneyField()
    total_credits = MoneyField()


class TrialBalanceReportSerializer(serializers.Serializer):
    as_of = serializers.DateField()
    currency_groups = CurrencyTrialBalanceSerializer(many=True)


class BalanceSheetRowSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    amount = MoneyField()


class BalanceSheetSectionSerializer(serializers.Serializer):
    rows = BalanceSheetRowSerializer(many=True)
    total = MoneyField()


class BalanceSheetReportSerializer(serializers.Serializer):
    as_of = serializers.DateField()
    reporting_currency = serializers.CharField()
    assets = BalanceSheetSectionSerializer()
    liabilities = BalanceSheetSectionSerializer()
    equity = BalanceSheetSectionSerializer()
    retained_earnings = MoneyField()
    total_assets = MoneyField()
    total_liabilities_and_equity = MoneyField()
    balances = serializers.BooleanField()


class IncomeStatementRowSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    amount = MoneyField()


class IncomeStatementSectionSerializer(serializers.Serializer):
    rows = IncomeStatementRowSerializer(many=True)
    total = MoneyField()


class IncomeStatementReportSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    reporting_currency = serializers.CharField()
    income = IncomeStatementSectionSerializer()
    expenses = IncomeStatementSectionSerializer()
    net_income = MoneyField()


class AccountLedgerLineSerializer(serializers.Serializer):
    entry_date = serializers.DateField()
    description = serializers.CharField()
    debit_amount = MoneyField()
    credit_amount = MoneyField()
    running_balance = MoneyField()


class AccountLedgerReportSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    currency = serializers.CharField()
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField(allow_null=True)
    opening_balance = MoneyField()
    lines = AccountLedgerLineSerializer(many=True)
    closing_balance = MoneyField()


class BudgetVsActualRowSerializer(serializers.Serializer):
    budget_id = serializers.UUIDField()
    account_name = serializers.CharField()
    currency = serializers.CharField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    budgeted_amount = MoneyField()
    actual_amount = MoneyField()
    percent_used = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    budgeted_amount_converted = MoneyField()
    actual_amount_converted = MoneyField()


class BudgetVsActualReportSerializer(serializers.Serializer):
    reporting_currency = serializers.CharField()
    rows = BudgetVsActualRowSerializer(many=True)
    total_budgeted_converted = MoneyField()
    total_actual_converted = MoneyField()
    overall_percent_used = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
