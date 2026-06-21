import { apiRequest } from "@/api/client";
import type { PaginatedResponse, SavingsGoal, SavingsGoalProgress } from "@/types/api";

export function listSavingsGoals(entityId?: string): Promise<PaginatedResponse<SavingsGoal>> {
  return apiRequest<PaginatedResponse<SavingsGoal>>("/savings-goals/", {
    searchParams: { entity: entityId },
  });
}

export function createSavingsGoal(
  payload: Omit<SavingsGoal, "id" | "created_by" | "created_at" | "updated_at">,
): Promise<SavingsGoal> {
  return apiRequest<SavingsGoal>("/savings-goals/", { method: "POST", body: payload });
}

export function deleteSavingsGoal(id: string): Promise<void> {
  return apiRequest<void>(`/savings-goals/${id}/`, { method: "DELETE" });
}

export function getSavingsGoalProgress(id: string): Promise<SavingsGoalProgress> {
  return apiRequest<SavingsGoalProgress>(`/savings-goals/${id}/progress/`);
}
