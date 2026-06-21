import { apiRequest } from "@/api/client";
import type { PaginatedResponse, Project, ProjectProgress } from "@/types/api";

export function listProjects(entityId?: string): Promise<PaginatedResponse<Project>> {
  return apiRequest<PaginatedResponse<Project>>("/projects/", {
    searchParams: { entity: entityId },
  });
}

export function createProject(
  payload: Omit<Project, "id" | "created_by" | "created_at" | "updated_at">,
): Promise<Project> {
  return apiRequest<Project>("/projects/", { method: "POST", body: payload });
}

export function deleteProject(id: string): Promise<void> {
  return apiRequest<void>(`/projects/${id}/`, { method: "DELETE" });
}

export function getProjectProgress(id: string): Promise<ProjectProgress> {
  return apiRequest<ProjectProgress>(`/projects/${id}/progress/`);
}
