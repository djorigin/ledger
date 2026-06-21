import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createSavingsGoal } from "@/api/savingsGoals";
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

interface SavingsGoalFormProps {
  entityId: string;
  accounts: Account[];
}

export function SavingsGoalForm({ entityId, accounts }: SavingsGoalFormProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [targetDate, setTargetDate] = useState("2030-01-01");
  const [linkedAccount, setLinkedAccount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createSavingsGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      setName("");
      setTargetAmount("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create savings goal.");
      } else {
        setError("Could not create savings goal.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name || !targetAmount || !targetDate || !linkedAccount) {
      setError("All fields are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      name,
      target_amount: targetAmount,
      target_date: targetDate,
      linked_account: linkedAccount,
      notes: "",
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New savings goal</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label htmlFor="goal-name">Name</Label>
          <Input id="goal-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="goal-amount">Target amount</Label>
          <Input
            id="goal-amount" inputMode="decimal" value={targetAmount}
            onChange={(e) => setTargetAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="goal-date">Target date</Label>
          <Input
            id="goal-date" type="date" value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label>Linked account</Label>
          <Select value={linkedAccount} onValueChange={(v) => setLinkedAccount(v ?? "")}>
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
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create goal"}
      </Button>
    </form>
  );
}
