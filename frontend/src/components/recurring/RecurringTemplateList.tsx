import { useMutation, useQueryClient } from "@tanstack/react-query";

import { setRecurringTemplateActive } from "@/api/recurring";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/money";
import type { Account, RecurringTransactionTemplate } from "@/types/api";

function TemplateRow({
  template,
  accountsById,
}: {
  template: RecurringTransactionTemplate;
  accountsById: Map<string, Account>;
}) {
  const queryClient = useQueryClient();
  const toggleMutation = useMutation({
    mutationFn: () => setRecurringTemplateActive(template.id, !template.is_active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-templates"] });
    },
  });

  return (
    <div className="space-y-1 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{template.description}</span>
        <span className="text-sm text-muted-foreground">
          {template.frequency} — next due {template.next_due_date}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">
        {accountsById.get(template.debit_account)?.name ?? template.debit_account} (Dr) /{" "}
        {accountsById.get(template.credit_account)?.name ?? template.credit_account} (Cr) —{" "}
        {formatMoney(template.amount, template.currency)}
      </p>
      <Button size="sm" variant="outline" disabled={toggleMutation.isPending} onClick={() => toggleMutation.mutate()}>
        {template.is_active ? "Deactivate" : "Reactivate"}
      </Button>
    </div>
  );
}

interface RecurringTemplateListProps {
  templates: RecurringTransactionTemplate[];
  accounts: Account[];
}

export function RecurringTemplateList({ templates, accounts }: RecurringTemplateListProps) {
  if (templates.length === 0) {
    return <p className="text-muted-foreground">No recurring transactions yet.</p>;
  }
  const accountsById = new Map(accounts.map((a) => [a.id, a]));
  return (
    <div className="space-y-3">
      {templates.map((template) => (
        <TemplateRow key={template.id} template={template} accountsById={accountsById} />
      ))}
    </div>
  );
}
