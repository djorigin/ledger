import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { listAccounts } from "@/api/accounts";
import { getAccountLedger } from "@/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

export function AccountLedgerPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [accountId, setAccountId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const accounts = (accountsQuery.data?.results ?? []).filter((a) => a.entity === entityId);

  const ledgerQuery = useQuery({
    queryKey: ["account-ledger", accountId, periodStart, periodEnd],
    queryFn: () => getAccountLedger(accountId, periodStart || undefined, periodEnd || undefined),
    enabled: !!accountId,
  });

  if (!entityId) return null;
  const report = ledgerQuery.data;
  const currency = accounts.find((a) => a.id === accountId)?.native_currency ?? "";

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="space-y-2 max-w-xs">
          <Label>Account</Label>
          <Select value={accountId} onValueChange={(v) => setAccountId(v ?? "")}>
            <SelectTrigger>
              <SelectValue placeholder="Select account">
                {(value: string | null) => accounts.find((a) => a.id === value)?.name ?? null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {accounts.map((account) => (
                <SelectItem key={account.id} value={account.id} label={account.name}>
                  {account.name} ({account.native_currency})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="account-ledger-period-start">Period start (optional)</Label>
          <Input
            id="account-ledger-period-start" type="date" value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
        </div>
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="account-ledger-period-end">Period end (optional)</Label>
          <Input
            id="account-ledger-period-end" type="date" value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </div>
      </div>

      {ledgerQuery.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {report && (
        <Card>
          <CardHeader>
            <CardTitle>{report.account_name}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Debit</TableHead>
                  <TableHead className="text-right">Credit</TableHead>
                  <TableHead className="text-right">Running balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground">
                    Opening balance
                  </TableCell>
                  <TableCell className="text-right">{formatMoney(report.opening_balance, currency)}</TableCell>
                </TableRow>
                {report.lines.map((line, index) => (
                  <TableRow key={index}>
                    <TableCell>{line.entry_date}</TableCell>
                    <TableCell>{line.description}</TableCell>
                    <TableCell className="text-right">{formatMoney(line.debit_amount, "")}</TableCell>
                    <TableCell className="text-right">{formatMoney(line.credit_amount, "")}</TableCell>
                    <TableCell className="text-right">{formatMoney(line.running_balance, currency)}</TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-medium">
                  <TableCell colSpan={4}>Closing balance</TableCell>
                  <TableCell className="text-right">{formatMoney(report.closing_balance, currency)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {!accountId && <p className="text-muted-foreground">Select an account to view its ledger.</p>}
    </div>
  );
}
