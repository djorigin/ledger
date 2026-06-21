import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getNetWorth } from "@/api/reports";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function NetWorthPage() {
  const [asOf, setAsOf] = useState(today);
  const [reportingCurrency, setReportingCurrency] = useState("AUD");

  const query = useQuery({
    queryKey: ["net-worth", asOf, reportingCurrency],
    queryFn: () => getNetWorth(reportingCurrency, asOf),
  });

  const report = query.data;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Consolidated across every entity you have access to, converted to one reporting currency.
      </p>
      <div className="flex gap-4">
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="net-worth-as-of">As of</Label>
          <Input id="net-worth-as-of" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Reporting currency</Label>
          <CurrencySelect value={reportingCurrency} onChange={setReportingCurrency} />
        </div>
      </div>

      {query.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {report && (
        <Card>
          <CardHeader>
            <CardTitle>Net worth by entity</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Entity</TableHead>
                  <TableHead className="text-right">Assets</TableHead>
                  <TableHead className="text-right">Liabilities</TableHead>
                  <TableHead className="text-right">Net worth</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.rows.map((row) => (
                  <TableRow key={row.entity_id}>
                    <TableCell>{row.entity_name}</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(row.total_assets, reportingCurrency)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatMoney(row.total_liabilities, reportingCurrency)}
                    </TableCell>
                    <TableCell className="text-right">{formatMoney(row.net_worth, reportingCurrency)}</TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-medium">
                  <TableCell colSpan={3}>Consolidated net worth</TableCell>
                  <TableCell className="text-right">
                    {formatMoney(report.consolidated_net_worth, reportingCurrency)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
