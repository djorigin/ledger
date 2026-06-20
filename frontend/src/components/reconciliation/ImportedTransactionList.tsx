import { Fragment, useState } from "react";

import { CandidateMatchPanel } from "@/components/reconciliation/CandidateMatchPanel";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import type { Account, ImportedTransaction } from "@/types/api";

interface ImportedTransactionListProps {
  transactions: ImportedTransaction[];
  accounts: Account[];
}

export function ImportedTransactionList({ transactions, accounts }: ImportedTransactionListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const accountsById = new Map(accounts.map((a) => [a.id, a]));

  if (transactions.length === 0) {
    return <p className="text-muted-foreground">No imported transactions yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Description</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {transactions.map((txn) => (
          <Fragment key={txn.id}>
            <TableRow
              className={txn.status === "UNMATCHED" ? "cursor-pointer" : undefined}
              onClick={() =>
                txn.status === "UNMATCHED" &&
                setExpandedId(expandedId === txn.id ? null : txn.id)
              }
            >
              <TableCell>{txn.transaction_date}</TableCell>
              <TableCell>{txn.description}</TableCell>
              <TableCell className="text-right">
                {formatMoney(
                  txn.amount.replace("-", ""),
                  accountsById.get(txn.account)?.native_currency ?? "",
                )}
                {txn.amount.startsWith("-") ? " (out)" : " (in)"}
              </TableCell>
              <TableCell>{txn.status}</TableCell>
            </TableRow>
            {expandedId === txn.id && (
              <TableRow>
                <TableCell colSpan={4}>
                  <CandidateMatchPanel imported={txn} accounts={accounts} />
                </TableCell>
              </TableRow>
            )}
          </Fragment>
        ))}
      </TableBody>
    </Table>
  );
}
