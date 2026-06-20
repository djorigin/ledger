import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { markAccountReconciled } from "@/api/reconciliation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatMoney } from "@/lib/money";
import type { ReconciliationRecord } from "@/types/api";

interface ReconciliationSummaryBarProps {
  accountId: string;
  currency: string;
  records: ReconciliationRecord[];
  unmatchedCountOnOrBefore: (statementDate: string) => number;
}

export function ReconciliationSummaryBar({
  accountId,
  currency,
  records,
  unmatchedCountOnOrBefore,
}: ReconciliationSummaryBarProps) {
  const queryClient = useQueryClient();
  const [statementDate, setStatementDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [statementBalance, setStatementBalance] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      markAccountReconciled(accountId, { statement_date: statementDate, statement_balance: statementBalance }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reconciliation-records", accountId] });
      queryClient.invalidateQueries({ queryKey: ["imported-transactions"] });
      setStatementBalance("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not reconcile.");
      } else {
        setError("Could not reconcile.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  const mostRecent = records[0];
  const outstanding = unmatchedCountOnOrBefore(statementDate);

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <h2 className="font-medium">Reconciliation</h2>
      {mostRecent && (
        <p className="text-sm text-muted-foreground">
          Last reconciled to {formatMoney(mostRecent.statement_balance, currency)} as of{" "}
          {mostRecent.statement_date}.
        </p>
      )}
      {outstanding > 0 && (
        <Alert>
          <AlertDescription>
            {outstanding} unmatched transaction{outstanding === 1 ? "" : "s"} on or before this
            date will be left for a future pass.
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="flex items-end gap-3">
        <div className="space-y-2">
          <Label htmlFor="statement-date">Statement date</Label>
          <Input
            id="statement-date"
            type="date"
            value={statementDate}
            onChange={(e) => setStatementDate(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="statement-balance">Statement balance</Label>
          <Input
            id="statement-balance"
            inputMode="decimal"
            value={statementBalance}
            onChange={(e) => setStatementBalance(e.target.value)}
            placeholder="0.00"
            required
          />
        </div>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Mark reconciled"}
        </Button>
      </form>
    </div>
  );
}
