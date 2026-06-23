from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.api.views.ap_ar import BillViewSet, InvoiceViewSet
from apps.api.views.assets import AssetClassViewSet
from apps.api.views.auth import EmailTokenObtainPairView, MeView
from apps.api.views.budgets import (
    BudgetViewSet,
    ProjectViewSet,
    SavingsGoalViewSet,
    SuperannuationProjectionView,
)
from apps.api.views.entities import EntityViewSet
from apps.api.views.imports import (
    AccountReconciliationRecordsView,
    ColumnMappingViewSet,
    ImportBatchViewSet,
    ImportConfirmView,
    ImportedTransactionViewSet,
    ImportPreviewView,
)
from apps.api.views.inventory import InventoryItemViewSet
from apps.api.views.ledger import AccountViewSet, JournalEntryViewSet
from apps.api.views.payroll import PayslipViewSet
from apps.api.views.recurring import PendingRecurringEntryViewSet, RecurringTransactionTemplateViewSet
from apps.api.views.reports import (
    AccountLedgerView,
    BalanceSheetView,
    BudgetVsActualView,
    CashFlowView,
    ConsolidatedNetWorthView,
    IncomeStatementView,
    NetWorthView,
    TrialBalanceView,
)

router = DefaultRouter()
router.register("entities", EntityViewSet, basename="entity")
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")
router.register("column-mappings", ColumnMappingViewSet, basename="column-mapping")
router.register("import-batches", ImportBatchViewSet, basename="import-batch")
router.register("imported-transactions", ImportedTransactionViewSet, basename="imported-transaction")
router.register("budgets", BudgetViewSet, basename="budget")
router.register("savings-goals", SavingsGoalViewSet, basename="savings-goal")
router.register("projects", ProjectViewSet, basename="project")
router.register("bills", BillViewSet, basename="bill")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("recurring-templates", RecurringTransactionTemplateViewSet, basename="recurring-template")
router.register("recurring-pending", PendingRecurringEntryViewSet, basename="recurring-pending")
router.register("asset-classes", AssetClassViewSet, basename="asset-class")
router.register("inventory", InventoryItemViewSet, basename="inventory-item")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("auth/login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # Distinct paths from the router's plain "import-batches/" (GET list) --
    # a router-registered viewset and a hand-added path can't share one URL.
    path("import-batches/preview/", ImportPreviewView.as_view(), name="import-batch-preview"),
    path("import-batches/confirm/", ImportConfirmView.as_view(), name="import-batch-confirm"),
    path(
        "accounts/<uuid:account_id>/reconciliation-records/",
        AccountReconciliationRecordsView.as_view(),
        name="account-reconciliation-records",
    ),
    path(
        "superannuation/project/",
        SuperannuationProjectionView.as_view(),
        name="superannuation-project",
    ),
    path("reports/trial-balance/", TrialBalanceView.as_view(), name="report-trial-balance"),
    path("reports/balance-sheet/", BalanceSheetView.as_view(), name="report-balance-sheet"),
    path(
        "reports/income-statement/",
        IncomeStatementView.as_view(),
        name="report-income-statement",
    ),
    path("reports/account-ledger/", AccountLedgerView.as_view(), name="report-account-ledger"),
    path(
        "reports/budget-vs-actual/",
        BudgetVsActualView.as_view(),
        name="report-budget-vs-actual",
    ),
    path("reports/cash-flow/", CashFlowView.as_view(), name="report-cash-flow"),
    path("reports/net-worth/", NetWorthView.as_view(), name="report-net-worth"),
    path(
        "reports/consolidated-net-worth/",
        ConsolidatedNetWorthView.as_view(),
        name="report-consolidated-net-worth",
    ),
    path("", include(router.urls)),
]
