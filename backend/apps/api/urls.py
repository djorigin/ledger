from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

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
from apps.api.views.ledger import AccountViewSet, JournalEntryViewSet

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
    path("", include(router.urls)),
]
