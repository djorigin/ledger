import { apiRequest } from "@/api/client";
import type { SuperannuationProjectionRequest, SuperannuationProjectionResponse } from "@/types/api";

export function projectSuperannuationBalance(
  payload: SuperannuationProjectionRequest,
): Promise<SuperannuationProjectionResponse> {
  return apiRequest<SuperannuationProjectionResponse>("/superannuation/project/", {
    method: "POST",
    body: payload,
  });
}
