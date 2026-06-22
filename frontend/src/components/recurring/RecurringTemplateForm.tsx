import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createRecurringTemplate } from "@/api/recurring";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Account, RecurrenceFrequency } from "@/types/api";

const FREQUENCIES: { value: RecurrenceFrequency; label: string }[] = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "ANNUALLY", label: "Annually" },
];

interface RecurringTemplateFormProps {
  entityId: string;
  accounts: Account[];
}

export function RecurringTemplateForm({ entityId, accounts }: RecurringTemplateFormProps) {
  const queryClient = useQueryClient();
  const [description, setDescription] = useState("");
  const [debitAccount, setDebitAccount] = useState("");
  const [creditAccount, setCreditAccount] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("AUD");
  const [frequency, setFrequency] = useState<RecurrenceFrequency>("MONTHLY");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createRecurringTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-templates"] });
      setDescription("");
      setDebitAccount("");
      setCreditAccount("");
      setAmount("");
      setEndDate("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create template.");
      } else {
        setError("Could not create template.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!description || !debitAccount || !creditAccount || !amount || !startDate) {
      setError("Description, both accounts, amount, and start date are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      description,
      debit_account: debitAccount,
      credit_account: creditAccount,
      amount,
      currency,
      frequency,
      start_date: startDate,
      end_date: endDate || null,
      next_due_date: startDate,
      is_active: true,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New recurring transaction</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label htmlFor="recurring-description">Description</Label>
          <Input
            id="recurring-description" value={description} onChange={(e) => setDescription(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label>Debit account</Label>
          <Select value={debitAccount} onValueChange={(v) => setDebitAccount(v ?? "")}>
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
          <Label>Credit account</Label>
          <Select value={creditAccount} onValueChange={(v) => setCreditAccount(v ?? "")}>
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
          <Label htmlFor="recurring-amount">Amount</Label>
          <Input
            id="recurring-amount" inputMode="decimal" value={amount}
            onChange={(e) => setAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
        <div className="space-y-2">
          <Label>Currency</Label>
          <CurrencySelect value={currency} onChange={setCurrency} />
        </div>
        <div className="space-y-2">
          <Label>Frequency</Label>
          <Select value={frequency} onValueChange={(v) => setFrequency((v as RecurrenceFrequency) ?? "MONTHLY")}>
            <SelectTrigger>
              <SelectValue placeholder="Frequency">
                {(v: string | null) => FREQUENCIES.find((f) => f.value === v)?.label ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {FREQUENCIES.map((f) => (
                <SelectItem key={f.value} value={f.value} label={f.label}>
                  {f.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="recurring-start-date">Start date (first due date)</Label>
          <Input
            id="recurring-start-date" type="date" value={startDate}
            onChange={(e) => setStartDate(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="recurring-end-date">End date (optional)</Label>
          <Input id="recurring-end-date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create recurring transaction"}
      </Button>
    </form>
  );
}
