import { apiRequest } from "@/api/client";
import type { Bill, BillPayment, BillProgress, PaginatedResponse } from "@/types/api";

export type CreateBillPayload = Omit<
  Bill,
  "id" | "journal_entry" | "is_cancelled" | "payments" | "created_by" | "created_at" | "updated_at"
>;

export function listBills(entityId?: string): Promise<PaginatedResponse<Bill>> {
  return apiRequest<PaginatedResponse<Bill>>("/bills/", { searchParams: { entity: entityId } });
}

export function createBill(payload: CreateBillPayload): Promise<Bill> {
  return apiRequest<Bill>("/bills/", { method: "POST", body: payload });
}

export function getBillProgress(id: string): Promise<BillProgress> {
  return apiRequest<BillProgress>(`/bills/${id}/progress/`);
}

export interface RecordBillPaymentPayload {
  payment_date: string;
  amount: string;
  payment_account: string;
}

export function recordBillPayment(id: string, payload: RecordBillPaymentPayload): Promise<BillPayment> {
  return apiRequest<BillPayment>(`/bills/${id}/payments/`, { method: "POST", body: payload });
}

export function cancelBill(id: string): Promise<Bill> {
  return apiRequest<Bill>(`/bills/${id}/cancel/`, { method: "POST", body: {} });
}
