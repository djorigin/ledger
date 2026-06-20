import { apiRequest } from "@/api/client";
import type { ReconciliationRecord } from "@/types/api";

export function listReconciliationRecords(accountId: string): Promise<ReconciliationRecord[]> {
  return apiRequest<ReconciliationRecord[]>(`/accounts/${accountId}/reconciliation-records/`);
}

export function markAccountReconciled(
  accountId: string,
  payload: { statement_date: string; statement_balance: string; notes?: string },
): Promise<ReconciliationRecord> {
  return apiRequest<ReconciliationRecord>(`/accounts/${accountId}/reconciliation-records/`, {
    method: "POST",
    body: payload,
  });
}
