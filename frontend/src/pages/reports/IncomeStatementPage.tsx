import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getIncomeStatement } from "@/api/reports";
import { CurrencySelect } from "@/components/reports/CurrencySelect";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import type { IncomeStatementSection } from "@/types/api";

function firstOfMonth(): string {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function Section({ title, section, currency }: { title: string; section: IncomeStatementSection; currency: string }) {
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

export function IncomeStatementPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const [periodStart, setPeriodStart] = useState(firstOfMonth);
  const [periodEnd, setPeriodEnd] = useState(today);
  const [reportingCurrency, setReportingCurrency] = useState("AUD");

  const query = useQuery({
    queryKey: ["income-statement", entityId, periodStart, periodEnd, reportingCurrency],
    queryFn: () => getIncomeStatement(entityId!, periodStart, periodEnd, reportingCurrency),
    enabled: !!entityId && !!periodStart && !!periodEnd,
  });

  if (!entityId) return null;
  const report = query.data;

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="income-statement-period-start">Period start</Label>
          <Input
            id="income-statement-period-start" type="date" value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
        </div>
        <div className="space-y-2 max-w-xs">
          <Label htmlFor="income-statement-period-end">Period end</Label>
          <Input
            id="income-statement-period-end" type="date" value={periodEnd}
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
          <Section title="Income" section={report.income} currency={reportingCurrency} />
          <Section title="Expenses" section={report.expenses} currency={reportingCurrency} />
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Net Income</p>
              <p className="text-lg font-semibold">{formatMoney(report.net_income, reportingCurrency)}</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
