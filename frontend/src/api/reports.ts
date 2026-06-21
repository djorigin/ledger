import { apiRequest } from "@/api/client";
import type {
  AccountLedgerReport,
  BalanceSheetReport,
  BudgetVsActualReport,
  IncomeStatementReport,
  TrialBalanceReport,
} from "@/types/api";

export function getTrialBalance(entityId: string, asOf?: string): Promise<TrialBalanceReport> {
  return apiRequest<TrialBalanceReport>("/reports/trial-balance/", {
    searchParams: { entity: entityId, as_of: asOf },
  });
}

export function getBalanceSheet(
  entityId: string,
  reportingCurrency: string,
  asOf?: string,
): Promise<BalanceSheetReport> {
  return apiRequest<BalanceSheetReport>("/reports/balance-sheet/", {
    searchParams: { entity: entityId, reporting_currency: reportingCurrency, as_of: asOf },
  });
}

export function getIncomeStatement(
  entityId: string,
  periodStart: string,
  periodEnd: string,
  reportingCurrency: string,
): Promise<IncomeStatementReport> {
  return apiRequest<IncomeStatementReport>("/reports/income-statement/", {
    searchParams: {
      entity: entityId,
      period_start: periodStart,
      period_end: periodEnd,
      reporting_currency: reportingCurrency,
    },
  });
}

export function getAccountLedger(
  accountId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<AccountLedgerReport> {
  return apiRequest<AccountLedgerReport>("/reports/account-ledger/", {
    searchParams: { account: accountId, period_start: periodStart, period_end: periodEnd },
  });
}

export function getBudgetVsActual(
  entityId: string,
  reportingCurrency: string,
): Promise<BudgetVsActualReport> {
  return apiRequest<BudgetVsActualReport>("/reports/budget-vs-actual/", {
    searchParams: { entity: entityId, reporting_currency: reportingCurrency },
  });
}
