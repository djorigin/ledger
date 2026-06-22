import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listRecurringTemplates } from "@/api/recurring";
import { useAuth } from "@/auth/AuthContext";
import { RecurringTemplateForm } from "@/components/recurring/RecurringTemplateForm";
import { RecurringTemplateList } from "@/components/recurring/RecurringTemplateList";

export function RecurringTemplatesPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const templatesQuery = useQuery({
    queryKey: ["recurring-templates", entityId],
    queryFn: () => listRecurringTemplates(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (accountsQuery.isLoading || templatesQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const templates = templatesQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Recurring Transactions</h1>
      <p className="text-sm text-muted-foreground">
        Defines recurring entries (mortgage, salary, subscriptions). These never post automatically —
        each occurrence lands in Pending Review for approval.
      </p>
      {canEdit && accounts.length > 0 && <RecurringTemplateForm entityId={entityId} accounts={accounts} />}
      <RecurringTemplateList templates={templates} accounts={accounts} />
    </div>
  );
}
