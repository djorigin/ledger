from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasEntityRole
from apps.api.serializers.reports import (
    AccountLedgerQuerySerializer,
    AccountLedgerReportSerializer,
    BalanceSheetQuerySerializer,
    BalanceSheetReportSerializer,
    BudgetVsActualQuerySerializer,
    BudgetVsActualReportSerializer,
    CashFlowQuerySerializer,
    CashFlowReportSerializer,
    IncomeStatementQuerySerializer,
    IncomeStatementReportSerializer,
    ConsolidatedNetWorthReportSerializer,
    NetWorthQuerySerializer,
    NetWorthReportSerializer,
    TrialBalanceQuerySerializer,
    TrialBalanceReportSerializer,
)
from apps.entities.models import Entity, EntityRole
from apps.ledger.models import Account
from apps.reports.services import (
    compute_account_ledger,
    compute_balance_sheet,
    compute_budget_vs_actual,
    compute_cash_flow_statement,
    compute_consolidated_net_worth,
    compute_income_statement,
    compute_net_worth,
    compute_trial_balance,
)


def _get_entity(request, entity_id):
    entity = Entity.objects.accessible_by(request.user).filter(pk=entity_id).first()
    if entity is None:
        raise Http404
    return entity


def _get_account(request, account_id):
    account = Account.objects.accessible_by(request.user).filter(pk=account_id).first()
    if account is None:
        raise Http404
    return account


class _ReportView(APIView):
    """
    Read-only, query-param-filtered reports (not CRUD resources, so no
    ModelViewSet). HasEntityRole's `has_permission` only inspects
    request.data, which is empty on a GET -- so the real check here is the
    explicit `check_object_permissions` call below, same pattern as
    `AccountReconciliationRecordsView` (apps/api/views/imports.py).
    """

    def get_permissions(self):
        return [HasEntityRole(EntityRole.VIEWER)()]


def _trial_balance_row(row):
    return {
        "account_id": row.account.id,
        "account_name": row.account.name,
        "account_type": row.account.account_type,
        "debit_balance": row.debit_balance,
        "credit_balance": row.credit_balance,
    }


class TrialBalanceView(_ReportView):
    def get(self, request):
        query = TrialBalanceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entity = _get_entity(request, query.validated_data["entity"])
        self.check_object_permissions(request, entity)

        report = compute_trial_balance(entity, as_of=query.validated_data.get("as_of"))
        data = {
            "as_of": report.as_of,
            "currency_groups": [
                {
                    "currency": group.currency,
                    "rows": [_trial_balance_row(r) for r in group.rows],
                    "total_debits": group.total_debits,
                    "total_credits": group.total_credits,
                }
                for group in report.currency_groups
            ],
        }
        return Response(TrialBalanceReportSerializer(data).data)


def _balance_sheet_section(section):
    return {
        "rows": [
            {"account_id": r.account.id, "account_name": r.account.name, "amount": r.amount}
            for r in section.rows
        ],
        "total": section.total,
    }


class BalanceSheetView(_ReportView):
    def get(self, request):
        query = BalanceSheetQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entity = _get_entity(request, query.validated_data["entity"])
        self.check_object_permissions(request, entity)

        report = compute_balance_sheet(
            entity,
            as_of=query.validated_data.get("as_of"),
            reporting_currency=query.validated_data["reporting_currency"],
        )
        data = {
            "as_of": report.as_of,
            "reporting_currency": report.reporting_currency,
            "assets": _balance_sheet_section(report.assets),
            "liabilities": _balance_sheet_section(report.liabilities),
            "equity": _balance_sheet_section(report.equity),
            "retained_earnings": report.retained_earnings,
            "total_assets": report.total_assets,
            "total_liabilities_and_equity": report.total_liabilities_and_equity,
            "balances": report.balances,
        }
        return Response(BalanceSheetReportSerializer(data).data)


def _income_statement_section(section):
    return {
        "rows": [
            {"account_id": r.account.id, "account_name": r.account.name, "amount": r.amount}
            for r in section.rows
        ],
        "total": section.total,
    }


class IncomeStatementView(_ReportView):
    def get(self, request):
        query = IncomeStatementQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entity = _get_entity(request, query.validated_data["entity"])
        self.check_object_permissions(request, entity)

        report = compute_income_statement(
            entity,
            period_start=query.validated_data["period_start"],
            period_end=query.validated_data["period_end"],
            reporting_currency=query.validated_data["reporting_currency"],
        )
        data = {
            "period_start": report.period_start,
            "period_end": report.period_end,
            "reporting_currency": report.reporting_currency,
            "income": _income_statement_section(report.income),
            "expenses": _income_statement_section(report.expenses),
            "net_income": report.net_income,
        }
        return Response(IncomeStatementReportSerializer(data).data)


class AccountLedgerView(_ReportView):
    def get(self, request):
        query = AccountLedgerQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        account = _get_account(request, query.validated_data["account"])
        self.check_object_permissions(request, account)

        report = compute_account_ledger(
            account,
            period_start=query.validated_data.get("period_start"),
            period_end=query.validated_data.get("period_end"),
        )
        data = {
            "account_id": report.account.id,
            "account_name": report.account.name,
            "currency": report.account.native_currency,
            "period_start": report.period_start,
            "period_end": report.period_end,
            "opening_balance": report.opening_balance,
            "lines": [
                {
                    "entry_date": line.entry_date,
                    "description": line.description,
                    "debit_amount": line.debit_amount,
                    "credit_amount": line.credit_amount,
                    "running_balance": line.running_balance,
                }
                for line in report.lines
            ],
            "closing_balance": report.closing_balance,
        }
        return Response(AccountLedgerReportSerializer(data).data)


class BudgetVsActualView(_ReportView):
    def get(self, request):
        query = BudgetVsActualQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entity = _get_entity(request, query.validated_data["entity"])
        self.check_object_permissions(request, entity)

        report = compute_budget_vs_actual(
            entity, reporting_currency=query.validated_data["reporting_currency"]
        )
        data = {
            "reporting_currency": report.reporting_currency,
            "rows": [
                {
                    "budget_id": row.budget.id,
                    "account_name": row.budget.account.name,
                    "currency": row.budget.account.native_currency,
                    "period_start": row.budget.period_start,
                    "period_end": row.budget.period_end,
                    "budgeted_amount": row.budgeted_amount,
                    "actual_amount": row.actual_amount,
                    "percent_used": row.percent_used,
                    "budgeted_amount_converted": row.budgeted_amount_converted,
                    "actual_amount_converted": row.actual_amount_converted,
                }
                for row in report.rows
            ],
            "total_budgeted_converted": report.total_budgeted_converted,
            "total_actual_converted": report.total_actual_converted,
            "overall_percent_used": report.overall_percent_used,
        }
        return Response(BudgetVsActualReportSerializer(data).data)


class CashFlowView(_ReportView):
    def get(self, request):
        query = CashFlowQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entity = _get_entity(request, query.validated_data["entity"])
        self.check_object_permissions(request, entity)

        report = compute_cash_flow_statement(
            entity,
            period_start=query.validated_data["period_start"],
            period_end=query.validated_data["period_end"],
            reporting_currency=query.validated_data["reporting_currency"],
        )
        data = {
            "period_start": report.period_start,
            "period_end": report.period_end,
            "reporting_currency": report.reporting_currency,
            "opening_cash": report.opening_cash,
            "operating_total": report.operating_total,
            "investing_total": report.investing_total,
            "financing_total": report.financing_total,
            "other_total": report.other_total,
            "net_change": report.net_change,
            "closing_cash": report.closing_cash,
            "reconciles": report.reconciles,
        }
        return Response(CashFlowReportSerializer(data).data)


class NetWorthView(APIView):
    """
    Not scoped to a single entity -- the brief's "family net worth rollup"
    spans every entity the user has access to. There's no single object to
    check HasEntityRole against, so the accessible_by(user) queryset itself
    is the access boundary (same precedent as EntityViewSet's list action).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = NetWorthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        entities = Entity.objects.accessible_by(request.user)
        report = compute_net_worth(
            entities,
            as_of=query.validated_data.get("as_of"),
            reporting_currency=query.validated_data["reporting_currency"],
        )
        data = {
            "as_of": report.as_of,
            "reporting_currency": report.reporting_currency,
            "rows": [
                {
                    "entity_id": row.entity.id,
                    "entity_name": row.entity.name,
                    "total_assets": row.total_assets,
                    "total_liabilities": row.total_liabilities,
                    "net_worth": row.net_worth,
                }
                for row in report.rows
            ],
            "consolidated_net_worth": report.consolidated_net_worth,
        }
        return Response(NetWorthReportSerializer(data).data)


class ConsolidatedNetWorthView(APIView):
    """
    GL net worth + Fixed Asset Register valuations, per entity and
    summed -- a new endpoint, not a change to NetWorthView above (which
    stays GL-only). Same access pattern: spans every entity the user has
    access to, no single object to check HasEntityRole against.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = NetWorthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        entities = Entity.objects.accessible_by(request.user)
        report = compute_consolidated_net_worth(
            entities,
            as_of=query.validated_data.get("as_of"),
            reporting_currency=query.validated_data["reporting_currency"],
        )
        data = {
            "as_of": report.as_of,
            "reporting_currency": report.reporting_currency,
            "rows": [
                {
                    "entity_id": row.entity.id,
                    "entity_name": row.entity.name,
                    "gl_net_worth": row.gl_net_worth,
                    "asset_register_value": row.asset_register_value,
                    "consolidated_net_worth": row.consolidated_net_worth,
                }
                for row in report.rows
            ],
            "total_gl_net_worth": report.total_gl_net_worth,
            "total_asset_register_value": report.total_asset_register_value,
            "grand_total": report.grand_total,
        }
        return Response(ConsolidatedNetWorthReportSerializer(data).data)
