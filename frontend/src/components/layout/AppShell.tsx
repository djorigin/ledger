import { Link, Navigate, Outlet, useParams } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { EntitySwitcher } from "@/components/layout/EntitySwitcher";
import { UserMenu } from "@/components/layout/UserMenu";

export function AppShell() {
  const { user } = useAuth();
  const { entityId } = useParams<{ entityId: string }>();

  if (!user) {
    return null;
  }

  if (user.memberships.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center text-center">
        <div>
          <p className="text-lg font-medium">No entities yet</p>
          <p className="text-muted-foreground">
            You don't have access to any entities yet — contact an administrator.
          </p>
        </div>
      </div>
    );
  }

  const isValidEntity = user.memberships.some((m) => m.entity_id === entityId);
  if (!isValidEntity) {
    return <Navigate to={`/entities/${user.memberships[0].entity_id}/journal-entries`} replace />;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-4">
          <span className="font-semibold">Ledger</span>
          <EntitySwitcher />
          <nav className="flex items-center gap-3 text-sm text-muted-foreground">
            <Link to={`/entities/${entityId}/journal-entries`} className="hover:text-foreground">
              Journal Entries
            </Link>
            <Link to={`/entities/${entityId}/accounts`} className="hover:text-foreground">
              Accounts
            </Link>
            <Link to={`/entities/${entityId}/budgets`} className="hover:text-foreground">
              Budgets
            </Link>
            <Link to={`/entities/${entityId}/savings-goals`} className="hover:text-foreground">
              Savings Goals
            </Link>
            <Link to={`/entities/${entityId}/projects`} className="hover:text-foreground">
              Projects
            </Link>
            <Link to={`/entities/${entityId}/superannuation`} className="hover:text-foreground">
              Superannuation
            </Link>
            <Link to={`/entities/${entityId}/reports`} className="hover:text-foreground">
              Reports
            </Link>
          </nav>
        </div>
        <UserMenu />
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
