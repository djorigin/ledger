import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getTrialBalance } from "@/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function TrialBalancePage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [asOf, setAsOf] = useState(today);

  const query = useQuery({
    queryKey: ["trial-balance", entityId, asOf],
    queryFn: () => getTrialBalance(entityId!, asOf),
    enabled: !!entityId,
  });

  if (!entityId) return null;

  return (
    <div className="space-y-6">
      <div className="space-y-2 max-w-xs">
        <Label htmlFor="trial-balance-as-of">As of</Label>
        <Input id="trial-balance-as-of" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
      </div>

      {query.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {query.data?.currency_groups.map((group) => (
        <Card key={group.currency}>
          <CardHeader>
            <CardTitle>{group.currency}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Debit</TableHead>
                  <TableHead className="text-right">Credit</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.rows.map((row) => (
                  <TableRow key={row.account_id}>
                    <TableCell>{row.account_name}</TableCell>
                    <TableCell>{row.account_type}</TableCell>
                    <TableCell className="text-right">
                      {row.debit_balance !== null ? formatMoney(row.debit_balance, "") : ""}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.credit_balance !== null ? formatMoney(row.credit_balance, "") : ""}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-medium">
                  <TableCell colSpan={2}>Total</TableCell>
                  <TableCell className="text-right">{formatMoney(group.total_debits, "")}</TableCell>
                  <TableCell className="text-right">{formatMoney(group.total_credits, "")}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}

      {query.data && query.data.currency_groups.length === 0 && (
        <p className="text-muted-foreground">No active accounts yet.</p>
      )}
    </div>
  );
}
