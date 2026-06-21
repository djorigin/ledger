import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listInvoices } from "@/api/invoices";
import { useAuth } from "@/auth/AuthContext";
import { InvoiceForm } from "@/components/invoices/InvoiceForm";
import { InvoiceList } from "@/components/invoices/InvoiceList";

export function InvoicesPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const { user } = useAuth();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const invoicesQuery = useQuery({
    queryKey: ["invoices", entityId],
    queryFn: () => listInvoices(entityId),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  if (accountsQuery.isLoading || invoicesQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const incomeAccounts = accounts.filter((a) => a.account_type === "INCOME");
  const assetAccounts = accounts.filter((a) => a.account_type === "ASSET");
  const receivableAccounts = assetAccounts;
  // Prefer accounts flagged as actual cash/bank (is_cash_equivalent) for
  // *receiving* a payment -- falls back to all ASSET accounts if none are
  // flagged yet (the flag is admin-set, opt-in).
  const cashAccounts = assetAccounts.filter((a) => a.is_cash_equivalent);
  const bankAccounts = cashAccounts.length > 0 ? cashAccounts : assetAccounts;
  const invoices = invoicesQuery.data?.results ?? [];
  const role = user?.memberships.find((m) => m.entity_id === entityId)?.role;
  const canEdit = role === "EDITOR" || role === "OWNER";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Invoices (Accounts Receivable)</h1>
      {canEdit && incomeAccounts.length > 0 && receivableAccounts.length > 0 && (
        <InvoiceForm entityId={entityId} incomeAccounts={incomeAccounts} receivableAccounts={receivableAccounts} />
      )}
      <InvoiceList invoices={invoices} bankAccounts={bankAccounts} />
    </div>
  );
}
