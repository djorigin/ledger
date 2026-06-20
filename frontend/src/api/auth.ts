import { apiRequest } from "@/api/client";
import type { MeResponse, TokenPair } from "@/types/api";

export function login(email: string, password: string): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/login/", {
    method: "POST",
    body: { email, password },
    skipAuth: true,
  });
}

export function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/auth/me/");
}
