import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { AppShell } from "@/components/layout/AppShell";
import { getLastSelectedEntityId } from "@/lib/entityStorage";
import { AccountsPage } from "@/pages/AccountsPage";
import { ImportPage } from "@/pages/ImportPage";
import { JournalEntriesPage } from "@/pages/JournalEntriesPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ReconciliationPage } from "@/pages/ReconciliationPage";
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
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
