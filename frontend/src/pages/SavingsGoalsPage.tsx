import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listSavingsGoals } from "@/api/savingsGoals";
import { useAuth } from "@/auth/AuthContext";
import { SavingsGoalForm } from "@/components/savings-goals/SavingsGoalForm";
import { SavingsGoalList } from "@/components/savings-goals/SavingsGoalList";

export function SavingsGoalsPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const goalsQuery = useQuery({
    queryKey: ["savings-goals", entityId],
    queryFn: () => listSavingsGoals(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (accountsQuery.isLoading || goalsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const goals = goalsQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Savings goals</h1>
      {canEdit && accounts.length > 0 && (
        <SavingsGoalForm entityId={entityId} accounts={accounts} />
      )}
      <SavingsGoalList goals={goals} accounts={accounts} />
    </div>
  );
}
