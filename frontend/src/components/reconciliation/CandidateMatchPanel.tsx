import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "@/api/client";
import {
  confirmMatch,
  createEntryFromImport,
  getCandidateMatches,
  ignoreImportedTransaction,
} from "@/api/imports";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatMoney } from "@/lib/money";
import type { Account, ImportedTransaction } from "@/types/api";

interface CandidateMatchPanelProps {
  imported: ImportedTransaction;
  accounts: Account[];
}

export function CandidateMatchPanel({ imported, accounts }: CandidateMatchPanelProps) {
  const queryClient = useQueryClient();
  const [offsettingAccount, setOffsettingAccount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const candidatesQuery = useQuery({
    queryKey: ["candidate-matches", imported.id],
    queryFn: () => getCandidateMatches(imported.id),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["imported-transactions"] });
  }

  function handleApiError(err: unknown) {
    if (err instanceof ApiError) {
      const body = err.body as { non_field_errors?: string[] } | null;
      setError(body?.non_field_errors?.join(" ") ?? "Something went wrong.");
    } else {
      setError("Something went wrong.");
    }
  }

  const confirmMatchMutation = useMutation({
    mutationFn: (journalLineId: string) => confirmMatch(imported.id, journalLineId),
    onSuccess: invalidate,
    onError: handleApiError,
  });

  const createEntryMutation = useMutation({
    mutationFn: () => createEntryFromImport(imported.id, offsettingAccount),
    onSuccess: invalidate,
    onError: handleApiError,
  });

  const ignoreMutation = useMutation({
    mutationFn: () => ignoreImportedTransaction(imported.id),
    onSuccess: invalidate,
    onError: handleApiError,
  });

  return (
    <div className="space-y-3 rounded border bg-muted/30 p-3">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div>
        <p className="text-sm font-medium">Candidate matches</p>
        {candidatesQuery.isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {candidatesQuery.data && candidatesQuery.data.length === 0 && (
          <p className="text-sm text-muted-foreground">No candidates found.</p>
        )}
        <ul className="space-y-1">
          {candidatesQuery.data?.map((line) => (
            <li key={line.id} className="flex items-center justify-between text-sm">
              <span>
                {line.description || "(no description)"} —{" "}
                {formatMoney(line.debit_amount !== "0.0000" ? line.debit_amount : line.credit_amount, line.currency)}
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => confirmMatchMutation.mutate(line.id)}
                disabled={confirmMatchMutation.isPending}
              >
                Confirm match
              </Button>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-end gap-2">
        <div className="space-y-1">
          <p className="text-sm font-medium">Categorize as new transaction</p>
          <Select value={offsettingAccount} onValueChange={(v) => setOffsettingAccount(v ?? "")}>
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder="Offsetting account">
                {(v: string | null) => accounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {accounts.map((account) => (
                <SelectItem key={account.id} value={account.id} label={account.name}>
                  {account.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          size="sm"
          disabled={!offsettingAccount || createEntryMutation.isPending}
          onClick={() => createEntryMutation.mutate()}
        >
          Create entry
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={ignoreMutation.isPending}
          onClick={() => ignoreMutation.mutate()}
        >
          Ignore
        </Button>
      </div>
    </div>
  );
}
