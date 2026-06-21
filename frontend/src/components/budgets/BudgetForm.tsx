import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createBudget } from "@/api/budgets";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import type { Account } from "@/types/api";

interface BudgetFormProps {
  entityId: string;
  accounts: Account[];
}

const PERIOD_TYPE = "MONTHLY" as const;

export function BudgetForm({ entityId, accounts }: BudgetFormProps) {
  const queryClient = useQueryClient();
  const [account, setAccount] = useState("");
  const [periodStart, setPeriodStart] = useState(() => new Date().toISOString().slice(0, 8) + "01");
  const [periodEnd, setPeriodEnd] = useState("");
  const [budgetedAmount, setBudgetedAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      setAccount("");
      setBudgetedAmount("");
      setPeriodEnd("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create budget.");
      } else {
        setError("Could not create budget.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!account || !periodStart || !periodEnd || !budgetedAmount) {
      setError("All fields are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      account,
      name: "",
      period_type: PERIOD_TYPE,
      period_start: periodStart,
      period_end: periodEnd,
      budgeted_amount: budgetedAmount,
      include_descendants: true,
      notes: "",
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New budget</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label>Account</Label>
          <Select value={account} onValueChange={(v) => setAccount(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(v: string | null) => accounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {accounts.map((a) => (
                <SelectItem key={a.id} value={a.id} label={a.name}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="period-start">Period start</Label>
          <Input
            id="period-start" type="date" value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="period-end">Period end</Label>
          <Input
            id="period-end" type="date" value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="budgeted-amount">Budgeted amount</Label>
          <Input
            id="budgeted-amount" inputMode="decimal" value={budgetedAmount}
            onChange={(e) => setBudgetedAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create budget"}
      </Button>
    </form>
  );
}
