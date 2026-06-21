import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createJournalEntry } from "@/api/journalEntries";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Account, Project } from "@/types/api";

interface LineFormState {
  account: string;
  debit_amount: string;
  credit_amount: string;
}

const emptyLine: LineFormState = { account: "", debit_amount: "", credit_amount: "" };

interface JournalEntryFormProps {
  entityId: string;
  accounts: Account[];
  projects?: Project[];
}

export function JournalEntryForm({ entityId, accounts, projects = [] }: JournalEntryFormProps) {
  const queryClient = useQueryClient();
  const [entryDate, setEntryDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [project, setProject] = useState("");
  const [lines, setLines] = useState<[LineFormState, LineFormState]>([emptyLine, emptyLine]);
  const [formError, setFormError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createJournalEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
      queryClient.invalidateQueries({ queryKey: ["project-progress"] });
      setDescription("");
      setProject("");
      setLines([emptyLine, emptyLine]);
      setFormError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setFormError(body?.non_field_errors?.join(" ") ?? "Could not create journal entry.");
      } else {
        setFormError("Could not create journal entry.");
      }
    },
  });

  function updateLine(index: 0 | 1, patch: Partial<LineFormState>) {
    setLines((prev) => {
      const next = [...prev] as [LineFormState, LineFormState];
      next[index] = { ...next[index], ...patch };
      return next;
    });
  }

  function accountFor(accountId: string): Account | undefined {
    return accounts.find((a) => a.id === accountId);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (!entryDate || !description.trim()) {
      setFormError("Date and description are required.");
      return;
    }
    for (const line of lines) {
      if (!line.account) {
        setFormError("Select an account for both lines.");
        return;
      }
      if (!line.debit_amount && !line.credit_amount) {
        setFormError("Each line needs a debit or credit amount.");
        return;
      }
    }

    mutation.mutate({
      entity: entityId,
      entry_date: entryDate,
      description,
      project: project || null,
      lines: lines.map((line) => {
        const account = accountFor(line.account);
        return {
          account: line.account,
          currency: account?.native_currency ?? "AUD",
          debit_amount: line.debit_amount || "0",
          credit_amount: line.credit_amount || "0",
        };
      }),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New transaction</h2>

      {formError && (
        <Alert variant="destructive">
          <AlertTitle>Could not save</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="entry_date">Date</Label>
          <Input
            id="entry_date"
            type="date"
            value={entryDate}
            onChange={(e) => setEntryDate(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Input
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>
      </div>

      {projects.length > 0 && (
        <div className="space-y-2 max-w-sm">
          <Label>Project (optional)</Label>
          <Select value={project} onValueChange={(v) => setProject(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="None">
                {(v: string | null) => projects.find((p) => p.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="" label="None">
                None
              </SelectItem>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id} label={p.name}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {lines.map((line, index) => (
        <div key={index} className="grid grid-cols-4 gap-2 items-end">
          <div className="space-y-2 col-span-2">
            <Label>Account {index + 1}</Label>
            <Select
              value={line.account}
              onValueChange={(value) => updateLine(index as 0 | 1, { account: value ?? "" })}
            >
              <SelectTrigger>
                {/* Select.Value needs an explicit value->label mapping --
                    without it, the closed trigger shows the raw value (an
                    account UUID here), not the item's rendered children. */}
                <SelectValue placeholder="Select account">
                  {(value: string | null) => {
                    const selected = accountFor(value ?? "");
                    return selected ? `${selected.name} (${selected.native_currency})` : null;
                  }}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {accounts.map((account) => (
                  <SelectItem
                    key={account.id}
                    value={account.id}
                    label={`${account.name} (${account.native_currency})`}
                  >
                    {account.name} ({account.native_currency})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Debit</Label>
            <Input
              inputMode="decimal"
              value={line.debit_amount}
              onChange={(e) => updateLine(index as 0 | 1, { debit_amount: e.target.value })}
              placeholder="0.00"
            />
          </div>
          <div className="space-y-2">
            <Label>Credit</Label>
            <Input
              inputMode="decimal"
              value={line.credit_amount}
              onChange={(e) => updateLine(index as 0 | 1, { credit_amount: e.target.value })}
              placeholder="0.00"
            />
          </div>
        </div>
      ))}

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Save transaction"}
      </Button>
    </form>
  );
}
