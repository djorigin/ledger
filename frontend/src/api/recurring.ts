import { apiRequest } from "@/api/client";
import type { PaginatedResponse, PendingRecurringEntry, RecurringTransactionTemplate } from "@/types/api";

export type CreateRecurringTemplatePayload = Omit<
  RecurringTransactionTemplate,
  "id" | "created_by" | "created_at" | "updated_at"
>;

export function listRecurringTemplates(
  entityId?: string,
): Promise<PaginatedResponse<RecurringTransactionTemplate>> {
  return apiRequest<PaginatedResponse<RecurringTransactionTemplate>>("/recurring-templates/", {
    searchParams: { entity: entityId },
  });
}

export function createRecurringTemplate(
  payload: CreateRecurringTemplatePayload,
): Promise<RecurringTransactionTemplate> {
  return apiRequest<RecurringTransactionTemplate>("/recurring-templates/", {
    method: "POST",
    body: payload,
  });
}

export function setRecurringTemplateActive(id: string, isActive: boolean): Promise<RecurringTransactionTemplate> {
  return apiRequest<RecurringTransactionTemplate>(`/recurring-templates/${id}/`, {
    method: "PATCH",
    body: { is_active: isActive },
  });
}

export function listPendingRecurringEntries(
  entityId?: string,
  status?: string,
): Promise<PaginatedResponse<PendingRecurringEntry>> {
  return apiRequest<PaginatedResponse<PendingRecurringEntry>>("/recurring-pending/", {
    searchParams: { entity: entityId, status },
  });
}

export function approvePendingRecurringEntry(id: string, amount?: string): Promise<PendingRecurringEntry> {
  return apiRequest<PendingRecurringEntry>(`/recurring-pending/${id}/approve/`, {
    method: "POST",
    body: amount ? { amount } : {},
  });
}

export function dismissPendingRecurringEntry(id: string): Promise<PendingRecurringEntry> {
  return apiRequest<PendingRecurringEntry>(`/recurring-pending/${id}/dismiss/`, {
    method: "POST",
    body: {},
  });
}
