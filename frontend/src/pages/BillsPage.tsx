import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listBills } from "@/api/bills";
import { useAuth } from "@/auth/AuthContext";
import { BillForm } from "@/components/bills/BillForm";
import { BillList } from "@/components/bills/BillList";

export function BillsPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const billsQuery = useQuery({
    queryKey: ["bills", entityId],
    queryFn: () => listBills(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (accountsQuery.isLoading || billsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const expenseAccounts = accounts.filter((a) => a.account_type === "EXPENSE");
  const payableAccounts = accounts.filter((a) => a.account_type === "LIABILITY");
  const assetAccounts = accounts.filter((a) => a.account_type === "ASSET");
  // Prefer accounts flagged as actual cash/bank (is_cash_equivalent) over
  // other assets like Accounts Receivable -- falls back to all ASSET
  // accounts if none are flagged yet (the flag is admin-set, opt-in).
  const cashAccounts = assetAccounts.filter((a) => a.is_cash_equivalent);
  const bankAccounts = cashAccounts.length > 0 ? cashAccounts : assetAccounts;
  const bills = billsQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Bills (Accounts Payable)</h1>
      {canEdit && expenseAccounts.length > 0 && payableAccounts.length > 0 && (
        <BillForm entityId={entityId} expenseAccounts={expenseAccounts} payableAccounts={payableAccounts} />
      )}
      <BillList bills={bills} bankAccounts={bankAccounts} />
    </div>
  );
}
