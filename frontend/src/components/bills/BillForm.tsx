import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createBill } from "@/api/bills";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Account } from "@/types/api";

interface BillFormProps {
  entityId: string;
  expenseAccounts: Account[];
  payableAccounts: Account[];
}

export function BillForm({ entityId, expenseAccounts, payableAccounts }: BillFormProps) {
  const queryClient = useQueryClient();
  const [vendorName, setVendorName] = useState("");
  const [description, setDescription] = useState("");
  const [billDate, setBillDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("AUD");
  const [expenseAccount, setExpenseAccount] = useState("");
  const [payableAccount, setPayableAccount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createBill,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      setVendorName("");
      setDescription("");
      setDueDate("");
      setAmount("");
      setExpenseAccount("");
      setPayableAccount("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create bill.");
      } else {
        setError("Could not create bill.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!vendorName || !billDate || !dueDate || !amount || !expenseAccount || !payableAccount) {
      setError("Vendor, dates, amount, and both accounts are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      vendor_name: vendorName,
      description,
      bill_date: billDate,
      due_date: dueDate,
      amount,
      currency,
      expense_account: expenseAccount,
      payable_account: payableAccount,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New bill</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label htmlFor="bill-vendor">Vendor</Label>
          <Input id="bill-vendor" value={vendorName} onChange={(e) => setVendorName(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="bill-description">Description</Label>
          <Input
            id="bill-description" value={description} onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="bill-date">Bill date</Label>
          <Input id="bill-date" type="date" value={billDate} onChange={(e) => setBillDate(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="bill-due-date">Due date</Label>
          <Input id="bill-due-date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="bill-amount">Amount</Label>
          <Input
            id="bill-amount" inputMode="decimal" value={amount}
            onChange={(e) => setAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
        <div className="space-y-2">
          <Label>Currency</Label>
          <CurrencySelect value={currency} onChange={setCurrency} />
        </div>
        <div className="space-y-2">
          <Label>Expense account</Label>
          <Select value={expenseAccount} onValueChange={(v) => setExpenseAccount(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(v: string | null) => expenseAccounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {expenseAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id} label={a.name}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Payable account</Label>
          <Select value={payableAccount} onValueChange={(v) => setPayableAccount(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(v: string | null) => payableAccounts.find((a) => a.id === v)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {payableAccounts.map((a) => (
                <SelectItem key={a.id} value={a.id} label={a.name}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create bill"}
      </Button>
    </form>
  );
}
