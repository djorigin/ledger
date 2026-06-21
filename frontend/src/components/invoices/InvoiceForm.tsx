import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createInvoice } from "@/api/invoices";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Account } from "@/types/api";

interface InvoiceFormProps {
  entityId: string;
  incomeAccounts: Account[];
  receivableAccounts: Account[];
}

export function InvoiceForm({ entityId, incomeAccounts, receivableAccounts }: InvoiceFormProps) {
  const queryClient = useQueryClient();
  const [customerName, setCustomerName] = useState("");
  const [description, setDescription] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("AUD");
  const [incomeAccount, setIncomeAccount] = useState("");
  const [receivableAccount, setReceivableAccount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setCustomerName("");
      setDescription("");
      setDueDate("");
      setAmount("");
      setIncomeAccount("");
      setReceivableAccount("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create invoice.");
      } else {
        setError("Could not create invoice.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!customerName || !invoiceDate || !dueDate || !amount || !incomeAccount || !receivableAccount) {
      setError("Customer, dates, amount, and both accounts are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      customer_name: customerName,
      description,
      invoice_date: invoiceDate,
      due_date: dueDate,
      amount,
      currency,
      income_account: incomeAccount,
      receivable_account: receivableAccount,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New invoice</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label htmlFor="invoice-customer">Customer</Label>
          <Input
            id="invoice-customer" value={customerName} onChange={(e) => setCustomerName(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="invoice-description">Description</Label>
          <Input
            id="invoice-description" value={description} onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="invoice-date">Invoice date</Label>
          <Input
            id="invoice-date" type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="invoice-due-date">Due date</Label>
          <Input id="invoice-due-date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="invoice-amount">Amount</Label>
          <Input
            id="invoice-amount" inputMode="decimal" value={amount}
            onChange={(e) => setAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
        <div className="space-y-2">
          <Label>Currency</Label>
          <CurrencySelect value={currency} onChange={setCurrency} />
        </div>
        <div className="space-y-2">
          <Label>Income account</Label>
          <Select value={incomeAccount} onValueChange={(v) => setIncomeAccount(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(v: string | null) => incomeAccounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {incomeAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id} label={a.name}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Receivable account</Label>
          <Select value={receivableAccount} onValueChange={(v) => setReceivableAccount(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(v: string | null) => receivableAccounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {receivableAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id} label={a.name}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create invoice"}
      </Button>
    </form>
  );
}
