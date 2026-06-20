import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { listImportedTransactions } from "@/api/imports";
import { listReconciliationRecords } from "@/api/reconciliation";
import { ImportedTransactionList } from "@/components/reconciliation/ImportedTransactionList";
import { ReconciliationSummaryBar } from "@/components/reconciliation/ReconciliationSummaryBar";

export function ReconciliationPage() {
  const { entityId, accountId } = useParams<{ entityId: string; accountId: string }>();

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const transactionsQuery = useQuery({
    queryKey: ["imported-transactions", accountId],
    queryFn: () => listImportedTransactions(accountId),
    enabled: !!accountId,
  });
  const recordsQuery = useQuery({
    queryKey: ["reconciliation-records", accountId],
    queryFn: () => listReconciliationRecords(accountId!),
    enabled: !!accountId,
  });

  if (!entityId || !accountId) return null;
  if (accountsQuery.isLoading || transactionsQuery.isLoading || recordsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);
  const account = accounts.find((a) => a.id === accountId);
  const transactions = transactionsQuery.data?.results ?? [];
  const records = recordsQuery.data ?? [];

  function unmatchedCountOnOrBefore(statementDate: string) {
    return transactions.filter(
      (t) => t.status === "UNMATCHED" && t.transaction_date <= statementDate,
    ).length;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Reconciliation — {account?.name}</h1>
      <ReconciliationSummaryBar
        accountId={accountId}
        currency={account?.native_currency ?? ""}
        records={records}
        unmatchedCountOnOrBefore={unmatchedCountOnOrBefore}
      />
      <ImportedTransactionList transactions={transactions} accounts={accounts} />
    </div>
  );
}
