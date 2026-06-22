import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";

import { approvePendingRecurringEntry, dismissPendingRecurringEntry, listPendingRecurringEntries } from "@/api/recurring";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PendingRecurringEntry } from "@/types/api";

function PendingEntryRow({ entry }: { entry: PendingRecurringEntry }) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState(entry.amount);
  const [error, setError] = useState<string | null>(null);

  const approveMutation = useMutation({
    mutationFn: () => approvePendingRecurringEntry(entry.id, amount !== entry.amount ? amount : undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-pending"] });
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not approve entry.");
      } else {
        setError("Could not approve entry.");
      }
    },
  });

  const dismissMutation = useMutation({
    mutationFn: () => dismissPendingRecurringEntry(entry.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-pending"] });
    },
  });

  return (
    <div className="space-y-2 rounded border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{entry.template_description}</span>
        <span className="text-sm text-muted-foreground">Due {entry.due_date}</span>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex items-end gap-2">
        <Input
          inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} className="w-32"
        />
        <span className="text-sm text-muted-foreground">{entry.template_currency}</span>
        <Button size="sm" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
          Approve
        </Button>
        <Button
          size="sm" variant="ghost" disabled={dismissMutation.isPending} onClick={() => dismissMutation.mutate()}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}

export function PendingReviewPage() {
  const { entityId } = useParams<{ entityId: string }>();

  const query = useQuery({
    queryKey: ["recurring-pending", entityId],
    queryFn: () => listPendingRecurringEntries(entityId, "PENDING"),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (query.isLoading) return <p className="text-muted-foreground">Loading…</p>;

  const entries = query.data?.results ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Pending Review</h1>
      <p className="text-sm text-muted-foreground">
        Recurring transactions due for approval. Nothing here has posted to the ledger yet — approve to
        post, or dismiss to skip this occurrence.
      </p>
      {entries.length === 0 ? (
        <p className="text-muted-foreground">Nothing pending review.</p>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <PendingEntryRow key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
