import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getCashFlow } from "@/api/reports";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";

function firstOfMonth(): string {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CashFlowStatementPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd, setPeriodEnd] = useState(today);
  const [reportingCurrency, setReportingCurrency] = useState("AUD");

  const query = useQuery({
    queryKey: ["cash-flow", entityId, periodStart, periodEnd, reportingCurrency],
    queryFn: () => getCashFlow(entityId!, periodStart, periodEnd, reportingCurrency),
    enabled: !!entityId && !!periodStart && !!periodEnd,
  });

  if (!entityId) return null;
  const report = query.data;

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="cash-flow-period-start">Period start</Label>
          <Input
            id="cash-flow-period-start" type="date" value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
        </div>
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="cash-flow-period-end">Period end</Label>
          <Input
            id="cash-flow-period-end" type="date" value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Reporting currency</Label>
          <CurrencySelect value={reportingCurrency} onChange={setReportingCurrency} />
        </div>
      </div>

      {query.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {report && (
        <>
          <Card>
            <CardContent className="pt-4">
              <Table>
                <TableBody>
                  <TableRow>
                    <TableCell>Opening cash</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.opening_cash, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Operating activities</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.operating_total, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Investing activities</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.investing_total, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Financing activities</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.financing_total, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  {report.other_total !== "0.0000" && (
                    <TableRow>
                      <TableCell>Other (mixed-category entries)</TableCell>
                      <TableCell className="text-right">
                        {formatMoney(report.other_total, reportingCurrency)}
                      </TableCell>
                    </TableRow>
                  )}
                  <TableRow className="font-medium">
                    <TableCell>Net change in cash</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.net_change, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  <TableRow className="font-medium">
                    <TableCell>Closing cash</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.closing_cash, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {!report.reconciles && (
            <Alert variant="destructive">
              <AlertDescription>
                Cash flow statement does not reconcile -- this indicates a bug, please report it.
              </AlertDescription>
            </Alert>
          )}
        </>
      )}
    </div>
  );
}
