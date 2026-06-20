import { Navigate, Outlet, useParams } from "react-router-dom";

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
        </div>
        <UserMenu />
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
