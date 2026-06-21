import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getBudgetVsActual } from "@/api/reports";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

export function BudgetVsActualPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [reportingCurrency, setReportingCurrency] = useState("AUD");

  const query = useQuery({
    queryKey: ["budget-vs-actual", entityId, reportingCurrency],
    queryFn: () => getBudgetVsActual(entityId!, reportingCurrency),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  const report = query.data;

  return (
    <div className="space-y-6">
      <div className="space-y-2 max-w-xs">
        <Label>Reporting currency</Label>
        <CurrencySelect value={reportingCurrency} onChange={setReportingCurrency} />
      </div>

      {query.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {report && report.rows.length === 0 && <p className="text-muted-foreground">No budgets yet.</p>}

      {report && report.rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Budgets</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Budgeted</TableHead>
                  <TableHead className="text-right">Actual</TableHead>
                  <TableHead>Progress</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.rows.map((row) => (
                  <TableRow key={row.budget_id}>
                    <TableCell>{row.account_name}</TableCell>
                    <TableCell>
                      {row.period_start} – {row.period_end}
                    </TableCell>
                    <TableCell className="text-right">{formatMoney(row.budgeted_amount, row.currency)}</TableCell>
                    <TableCell className="text-right">{formatMoney(row.actual_amount, row.currency)}</TableCell>
                    <TableCell className="w-32">
                      <ProgressBar percent={row.percent_used ? Number(row.percent_used) : null} />
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-medium">
                  <TableCell colSpan={2}>Total ({reportingCurrency})</TableCell>
                  <TableCell className="text-right">
                    {formatMoney(report.total_budgeted_converted, reportingCurrency)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(report.total_actual_converted, reportingCurrency)}
                  </TableCell>
                  <TableCell className="w-32">
                    <ProgressBar
                      percent={report.overall_percent_used ? Number(report.overall_percent_used) : null}
                    />
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
