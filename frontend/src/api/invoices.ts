import { apiRequest } from "@/api/client";
import type { Invoice, InvoicePayment, InvoiceProgress, PaginatedResponse } from "@/types/api";

export type CreateInvoicePayload = Omit<
  Invoice,
  "id" | "journal_entry" | "is_cancelled" | "payments" | "created_by" | "created_at" | "updated_at"
>;

export function listInvoices(entityId?: string): Promise<PaginatedResponse<Invoice>> {
  return apiRequest<PaginatedResponse<Invoice>>("/invoices/", { searchParams: { entity: entityId } });
}

export function createInvoice(payload: CreateInvoicePayload): Promise<Invoice> {
  return apiRequest<Invoice>("/invoices/", { method: "POST", body: payload });
}

export function getInvoiceProgress(id: string): Promise<InvoiceProgress> {
  return apiRequest<InvoiceProgress>(`/invoices/${id}/progress/`);
}

export interface RecordInvoicePaymentPayload {
  payment_date: string;
  amount: string;
  payment_account: string;
}

export function recordInvoicePayment(
  id: string,
  payload: RecordInvoicePaymentPayload,
): Promise<InvoicePayment> {
  return apiRequest<InvoicePayment>(`/invoices/${id}/payments/`, { method: "POST", body: payload });
}

export function cancelInvoice(id: string): Promise<Invoice> {
  return apiRequest<Invoice>(`/invoices/${id}/cancel/`, { method: "POST", body: {} });
}
