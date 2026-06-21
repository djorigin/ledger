import { useQuery } from "@tanstack/react-query";
import Decimal from "decimal.js";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getBalanceSheet } from "@/api/reports";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import type { BalanceSheetSection } from "@/types/api";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function Section({ title, section, currency }: { title: string; section: BalanceSheetSection; currency: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableBody>
            {section.rows.map((row) => (
              <TableRow key={row.account_id}>
                <TableCell>{row.account_name}</TableCell>
                <TableCell className="text-right">{formatMoney(row.amount, currency)}</TableCell>
              </TableRow>
            ))}
            <TableRow className="font-medium">
              <TableCell>Total</TableCell>
              <TableCell className="text-right">{formatMoney(section.total, currency)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function BalanceSheetPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [asOf, setAsOf] = useState(today);
  const [reportingCurrency, setReportingCurrency] = useState("AUD");

  const query = useQuery({
    queryKey: ["balance-sheet", entityId, asOf, reportingCurrency],
    queryFn: () => getBalanceSheet(entityId!, reportingCurrency, asOf),
    enabled: !!entityId,
  });

  if (!entityId) return null;
  const report = query.data;
  const equityTotal = report
    ? new Decimal(report.equity.total).plus(report.retained_earnings).toFixed(4)
    : null;

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="balance-sheet-as-of">As of</Label>
          <Input id="balance-sheet-as-of" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Reporting currency</Label>
          <CurrencySelect value={reportingCurrency} onChange={setReportingCurrency} />
        </div>
      </div>

      {query.isLoading && <p className="text-muted-foreground">Loading…</p>}

      {report && (
        <>
          <Section title="Assets" section={report.assets} currency={reportingCurrency} />
          <Section title="Liabilities" section={report.liabilities} currency={reportingCurrency} />

          <Card>
            <CardHeader>
              <CardTitle>Equity</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableBody>
                  {report.equity.rows.map((row) => (
                    <TableRow key={row.account_id}>
                      <TableCell>{row.account_name}</TableCell>
                      <TableCell className="text-right">{formatMoney(row.amount, reportingCurrency)}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell>Retained Earnings</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(report.retained_earnings, reportingCurrency)}
                    </TableCell>
                  </TableRow>
                  <TableRow className="font-medium">
                    <TableCell>Total</TableCell>
                    <TableCell className="text-right">{formatMoney(equityTotal!, reportingCurrency)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center justify-between pt-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Assets</p>
                <p className="text-lg font-semibold">{formatMoney(report.total_assets, reportingCurrency)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Liabilities + Equity</p>
                <p className="text-lg font-semibold">
                  {formatMoney(report.total_liabilities_and_equity, reportingCurrency)}
                </p>
              </div>
            </CardContent>
          </Card>

          {!report.balances && (
            <Alert variant="destructive">
              <AlertDescription>
                Balance sheet does not balance -- this indicates a bug, please report it.
              </AlertDescription>
            </Alert>
          )}
        </>
      )}
    </div>
  );
}
