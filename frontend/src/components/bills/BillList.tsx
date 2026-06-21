import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { cancelBill, getBillProgress, recordBillPayment } from "@/api/bills";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatMoney } from "@/lib/money";
import type { Account, Bill } from "@/types/api";

function BillRow({ bank_accounts, bill }: { bank_accounts: Account[]; bill: Bill }) {
  const queryClient = useQueryClient();
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentAccount, setPaymentAccount] = useState(bank_accounts[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);

  const progressQuery = useQuery({
    queryKey: ["bill-progress", bill.id],
    queryFn: () => getBillProgress(bill.id),
  });

  const paymentMutation = useMutation({
    mutationFn: () =>
      recordBillPayment(bill.id, {
        payment_date: paymentDate,
        amount: paymentAmount,
        payment_account: paymentAccount,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill-progress", bill.id] });
      setPaymentAmount("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not record payment.");
      } else {
        setError("Could not record payment.");
      }
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelBill(bill.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill-progress", bill.id] });
    },
  });

  function handleRecordPayment(event: FormEvent) {
    event.preventDefault();
    if (!paymentAmount || !paymentAccount) {
      setError("Amount and account are required.");
      return;
    }
    paymentMutation.mutate();
  }

  const progress = progressQuery.data;
  const hasPayments = bill.payments.length > 0;

  return (
    <div className="space-y-2 rounded border p-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-medium">{bill.vendor_name}</span>
          {bill.description && <span className="text-muted-foreground"> — {bill.description}</span>}
        </div>
        <div className="flex items-center gap-2 text-sm">
          {progress?.is_overdue && (
            <span className="rounded bg-destructive px-2 py-0.5 text-destructive-foreground">Overdue</span>
          )}
          <span className="text-muted-foreground">{progress?.status}</span>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">Due {bill.due_date}</p>
      {progress && (
        <p className="text-sm">
          {formatMoney(progress.amount_paid, bill.currency)} of {formatMoney(progress.amount, bill.currency)} paid
          {" "}({formatMoney(progress.amount_due, bill.currency)} remaining)
        </p>
      )}

      {!bill.is_cancelled && progress?.status !== "PAID" && (
        <form onSubmit={handleRecordPayment} className="flex items-end gap-2">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Input
            type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)}
            className="w-40"
          />
          <Input
            inputMode="decimal" placeholder="Amount" value={paymentAmount}
            onChange={(e) => setPaymentAmount(e.target.value)} className="w-28"
          />
          <select
            value={paymentAccount}
            onChange={(e) => setPaymentAccount(e.target.value)}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          >
            {bank_accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <Button type="submit" size="sm" variant="outline" disabled={paymentMutation.isPending}>
            Record payment
          </Button>
        </form>
      )}

      {!bill.is_cancelled && (
        <Button
          size="sm" variant="ghost" disabled={hasPayments || cancelMutation.isPending}
          onClick={() => cancelMutation.mutate()}
        >
          Cancel
        </Button>
      )}
    </div>
  );
}

interface BillListProps {
  bills: Bill[];
  bankAccounts: Account[];
}

export function BillList({ bills, bankAccounts }: BillListProps) {
  if (bills.length === 0) {
    return <p className="text-muted-foreground">No bills yet.</p>;
  }
  return (
    <div className="space-y-3">
      {bills.map((bill) => (
        <BillRow key={bill.id} bill={bill} bank_accounts={bankAccounts} />
      ))}
    </div>
  );
}
