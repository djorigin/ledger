import { useQuery } from "@tanstack/react-query";

import { getBudgetProgress } from "@/api/budgets";
import { ProgressBar } from "@/components/ui/progress-bar";
import { formatMoney } from "@/lib/money";
import type { Account, Budget } from "@/types/api";

function BudgetRow({ budget, account }: { budget: Budget; account: Account | undefined }) {
  const progressQuery = useQuery({
    queryKey: ["budget-progress", budget.id],
    queryFn: () => getBudgetProgress(budget.id),
  });
  const currency = account?.native_currency ?? "";

  return (
    <div className="space-y-1 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{account?.name ?? budget.account}</span>
        <span className="text-sm text-muted-foreground">
          {budget.period_start} – {budget.period_end}
        </span>
      </div>
      {progressQuery.data && (
        <>
          <ProgressBar percent={progressQuery.data.percent_used ? Number(progressQuery.data.percent_used) : null} />
          <p className="text-sm text-muted-foreground">
            {formatMoney(progressQuery.data.actual_amount, currency)} of{" "}
            {formatMoney(progressQuery.data.budgeted_amount, currency)} spent
          </p>
        </>
      )}
    </div>
  );
}

interface BudgetListProps {
  budgets: Budget[];
  accounts: Account[];
}

export function BudgetList({ budgets, accounts }: BudgetListProps) {
  if (budgets.length === 0) {
    return <p className="text-muted-foreground">No budgets yet.</p>;
  }
  const accountsById = new Map(accounts.map((a) => [a.id, a]));
  return (
    <div className="space-y-3">
      {budgets.map((budget) => (
        <BudgetRow key={budget.id} budget={budget} account={accountsById.get(budget.account)} />
      ))}
    </div>
  );
}
