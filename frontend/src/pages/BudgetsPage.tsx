import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listBudgets } from "@/api/budgets";
import { BudgetForm } from "@/components/budgets/BudgetForm";
import { BudgetList } from "@/components/budgets/BudgetList";
import { useAuth } from "@/auth/AuthContext";

export function BudgetsPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const budgetsQuery = useQuery({
    queryKey: ["budgets", entityId],
    queryFn: () => listBudgets(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (accountsQuery.isLoading || budgetsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const budgets = budgetsQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Budgets</h1>
      {canEdit && accounts.length > 0 && <BudgetForm entityId={entityId} accounts={accounts} />}
      <BudgetList budgets={budgets} accounts={accounts} />
    </div>
  );
}
