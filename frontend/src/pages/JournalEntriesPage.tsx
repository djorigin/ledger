import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listJournalEntries } from "@/api/journalEntries";
import { useAuth } from "@/auth/AuthContext";
import { JournalEntryForm } from "@/components/journal-entries/JournalEntryForm";
import { JournalEntryList } from "@/components/journal-entries/JournalEntryList";

export function JournalEntriesPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  });
  const entriesQuery = useQuery({
    queryKey: ["journal-entries"],
    queryFn: listJournalEntries,
  });

  if (!entityId) return null;

  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  if (accountsQuery.isLoading || entriesQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const entries = (entriesQuery.data?.results ?? []).filter((e) => e.entity === entityId);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Journal entries</h1>
      {canEdit && accounts.length > 0 && (
        <JournalEntryForm entityId={entityId} accounts={accounts} />
      )}
      <JournalEntryList entries={entries} accounts={accounts} />
    </div>
  );
}
