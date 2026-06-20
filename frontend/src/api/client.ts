import {
  clearStoredRefreshToken,
  getStoredRefreshToken,
  setStoredRefreshToken,
} from "@/auth/tokenStorage";
import type { TokenPair } from "@/types/api";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

// In-memory only -- never persisted. Read directly by fetchWithAuth rather
// than threaded through React state, so requests always use the latest
// value without waiting on a render.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// Called by AuthContext to learn when a session has been forcibly ended
// (e.g. the refresh token itself was rejected). client.ts has no React
// context of its own, so this is a simple callback registry instead.
let sessionExpiredHandler: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

// Ensures concurrent 401s (e.g. two requests firing right as the access
// token expires) trigger exactly one network refresh, not one per request.
let refreshPromise: Promise<string> | null = null;

export async function performRefresh(): Promise<string> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const refreshToken = getStoredRefreshToken();
    if (!refreshToken) {
      throw new ApiError(401, { detail: "No refresh token available." });
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      clearStoredRefreshToken();
      sessionExpiredHandler?.();
      throw new ApiError(response.status, await safeJson(response));
    }

    const data = (await response.json()) as TokenPair;
    // Rotation: the old refresh token is now blacklisted, so the new one
    // must overwrite storage every time, not just on first login.
    setStoredRefreshToken(data.refresh);
    setAccessToken(data.access);
    return data.access;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  searchParams?: Record<string, string | number | undefined>;
  skipAuth?: boolean;
}

async function performRequest(path: string, options: RequestOptions): Promise<Response> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (options.searchParams) {
    for (const [key, value] of Object.entries(options.searchParams)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (!options.skipAuth && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  return fetch(url.toString(), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await performRequest(path, options);

  if (response.status === 401 && !options.skipAuth) {
    try {
      await performRefresh();
    } catch {
      throw new ApiError(401, await safeJson(response));
    }
    response = await performRequest(path, options);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await safeJson(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
