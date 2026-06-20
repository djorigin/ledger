import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function AccountsPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });

  if (!entityId) return null;
  if (accountsQuery.isLoading) return <p className="text-muted-foreground">Loading…</p>;

  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Accounts</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Currency</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((account) => (
            <TableRow key={account.id}>
              <TableCell>{account.name}</TableCell>
              <TableCell>{account.account_type}</TableCell>
              <TableCell>{account.native_currency}</TableCell>
              <TableCell className="text-right space-x-2">
                <Link
                  to={`/entities/${entityId}/accounts/${account.id}/import`}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  Import
                </Link>
                <Link
                  to={`/entities/${entityId}/accounts/${account.id}/reconciliation`}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  Reconcile
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
