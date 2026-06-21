import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { projectSuperannuationBalance } from "@/api/superannuation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatMoney } from "@/lib/money";

export function SuperannuationPage() {
  const [currentBalance, setCurrentBalance] = useState("");
  const [targetDate, setTargetDate] = useState("2030-01-01");
  const [annualContribution, setAnnualContribution] = useState("");
  const [annualGrowthRate, setAnnualGrowthRate] = useState("0.07");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: projectSuperannuationBalance,
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not compute projection.");
      } else {
        setError("Could not compute projection.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    mutation.mutate({
      current_balance: currentBalance,
      target_date: targetDate,
      annual_contribution: annualContribution,
      annual_growth_rate: annualGrowthRate,
    });
  }

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-xl font-semibold">Superannuation projection</h1>
      <p className="text-sm text-muted-foreground">
        A simple compounding-growth estimate -- not financial advice, not
        inflation- or tax-adjusted.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Projection inputs</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="current-balance">Current balance</Label>
              <Input
                id="current-balance" inputMode="decimal" value={currentBalance}
                onChange={(e) => setCurrentBalance(e.target.value)} placeholder="0.00" required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="target-date">Target date</Label>
              <Input
                id="target-date" type="date" value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)} required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="annual-contribution">Annual contribution</Label>
              <Input
                id="annual-contribution" inputMode="decimal" value={annualContribution}
                onChange={(e) => setAnnualContribution(e.target.value)} placeholder="0.00" required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="annual-growth-rate">Annual growth rate (e.g. 0.07 for 7%)</Label>
              <Input
                id="annual-growth-rate" inputMode="decimal" value={annualGrowthRate}
                onChange={(e) => setAnnualGrowthRate(e.target.value)} required
              />
            </div>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Calculating…" : "Calculate projection"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {mutation.data && (
        <Card>
          <CardHeader>
            <CardTitle>Projected balance</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">
              {formatMoney(mutation.data.projected_balance, "")}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
