import { apiRequest } from "@/api/client";
import type { Budget, BudgetProgress, PaginatedResponse } from "@/types/api";

export function listBudgets(entityId?: string): Promise<PaginatedResponse<Budget>> {
  return apiRequest<PaginatedResponse<Budget>>("/budgets/", { searchParams: { entity: entityId } });
}

export function createBudget(payload: Omit<Budget, "id" | "created_by" | "created_at" | "updated_at">): Promise<Budget> {
  return apiRequest<Budget>("/budgets/", { method: "POST", body: payload });
}

export function deleteBudget(id: string): Promise<void> {
  return apiRequest<void>(`/budgets/${id}/`, { method: "DELETE" });
}

export function getBudgetProgress(id: string): Promise<BudgetProgress> {
  return apiRequest<BudgetProgress>(`/budgets/${id}/progress/`);
}
