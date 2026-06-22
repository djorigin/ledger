import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { AppShell } from "@/components/layout/AppShell";
import { ReportsLayout } from "@/components/layout/ReportsLayout";
import { getLastSelectedEntityId } from "@/lib/entityStorage";
import { AccountsPage } from "@/pages/AccountsPage";
import { BillsPage } from "@/pages/BillsPage";
import { BudgetsPage } from "@/pages/BudgetsPage";
import { ImportPage } from "@/pages/ImportPage";
import { InvoicesPage } from "@/pages/InvoicesPage";
import { JournalEntriesPage } from "@/pages/JournalEntriesPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PendingReviewPage } from "@/pages/PendingReviewPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { RecurringTemplatesPage } from "@/pages/RecurringTemplatesPage";
import { ReconciliationPage } from "@/pages/ReconciliationPage";
import { AccountLedgerPage } from "@/pages/reports/AccountLedgerPage";
import { BalanceSheetPage } from "@/pages/reports/BalanceSheetPage";
import { BudgetVsActualPage } from "@/pages/reports/BudgetVsActualPage";
import { CashFlowStatementPage } from "@/pages/reports/CashFlowStatementPage";
import { IncomeStatementPage } from "@/pages/reports/IncomeStatementPage";
import { NetWorthPage } from "@/pages/reports/NetWorthPage";
import { TrialBalancePage } from "@/pages/reports/TrialBalancePage";
import { SavingsGoalsPage } from "@/pages/SavingsGoalsPage";
import { SuperannuationPage } from "@/pages/SuperannuationPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

function RootRedirect() {
  const { user } = useAuth();
  const memberships = user?.memberships ?? [];
  const lastSelected = getLastSelectedEntityId();
  const defaultEntityId =
    (lastSelected && memberships.some((m) => m.entity_id === lastSelected)
      ? lastSelected
      : memberships[0]?.entity_id) ?? null;

  if (!defaultEntityId) {
    return <AppShell />;
  }
  return <Navigate to={`/entities/${defaultEntityId}/journal-entries`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/entities/:entityId" element={<AppShell />}>
          <Route path="journal-entries" element={<JournalEntriesPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="accounts/:accountId/import" element={<ImportPage />} />
          <Route path="accounts/:accountId/reconciliation" element={<ReconciliationPage />} />
          <Route path="budgets" element={<BudgetsPage />} />
          <Route path="savings-goals" element={<SavingsGoalsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="superannuation" element={<SuperannuationPage />} />
          <Route path="bills" element={<BillsPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="recurring" element={<RecurringTemplatesPage />} />
          <Route path="pending-review" element={<PendingReviewPage />} />
          <Route path="reports" element={<ReportsLayout />}>
            <Route index element={<Navigate to="trial-balance" replace />} />
            <Route path="trial-balance" element={<TrialBalancePage />} />
            <Route path="balance-sheet" element={<BalanceSheetPage />} />
            <Route path="cash-flow" element={<CashFlowStatementPage />} />
            <Route path="income-statement" element={<IncomeStatementPage />} />
            <Route path="account-ledger" element={<AccountLedgerPage />} />
            <Route path="budget-vs-actual" element={<BudgetVsActualPage />} />
            <Route path="net-worth" element={<NetWorthPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
