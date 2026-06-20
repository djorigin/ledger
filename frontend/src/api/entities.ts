import { apiRequest } from "@/api/client";
import type { Entity, PaginatedResponse } from "@/types/api";

export function listEntities(): Promise<PaginatedResponse<Entity>> {
  return apiRequest<PaginatedResponse<Entity>>("/entities/");
}
