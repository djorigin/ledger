import { useQuery } from "@tanstack/react-query";

import { getSavingsGoalProgress } from "@/api/savingsGoals";
import { ProgressBar } from "@/components/ui/progress-bar";
import { formatMoney } from "@/lib/money";
import type { Account, SavingsGoal } from "@/types/api";

function SavingsGoalRow({ goal, account }: { goal: SavingsGoal; account: Account | undefined }) {
  const progressQuery = useQuery({
    queryKey: ["savings-goal-progress", goal.id],
    queryFn: () => getSavingsGoalProgress(goal.id),
  });
  const currency = account?.native_currency ?? "";

  return (
    <div className="space-y-1 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{goal.name}</span>
        <span className="text-sm text-muted-foreground">Target: {goal.target_date}</span>
      </div>
      {progressQuery.data && (
        <>
          <ProgressBar
            percent={
              progressQuery.data.percent_complete ? Number(progressQuery.data.percent_complete) : null
            }
          />
          <p className="text-sm text-muted-foreground">
            {formatMoney(progressQuery.data.current_balance, currency)} of{" "}
            {formatMoney(progressQuery.data.target_amount, currency)}
            {" — "}
            {progressQuery.data.days_remaining >= 0
              ? `${progressQuery.data.days_remaining} days remaining`
              : "target date passed"}
          </p>
        </>
      )}
    </div>
  );
}

interface SavingsGoalListProps {
  goals: SavingsGoal[];
  accounts: Account[];
}

export function SavingsGoalList({ goals, accounts }: SavingsGoalListProps) {
  if (goals.length === 0) {
    return <p className="text-muted-foreground">No savings goals yet.</p>;
  }
  const accountsById = new Map(accounts.map((a) => [a.id, a]));
  return (
    <div className="space-y-3">
      {goals.map((goal) => (
        <SavingsGoalRow key={goal.id} goal={goal} account={accountsById.get(goal.linked_account)} />
      ))}
    </div>
  );
}
