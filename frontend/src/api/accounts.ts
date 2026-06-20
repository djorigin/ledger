import { apiRequest } from "@/api/client";
import type { Account, PaginatedResponse } from "@/types/api";

// AccountViewSet has no query-param entity filter today -- fetch the full
// accessible list and filter client-side. Fine at this app's data volumes
// (a private family's chart of accounts is small); revisit if it grows.
export function listAccounts(): Promise<PaginatedResponse<Account>> {
  return apiRequest<PaginatedResponse<Account>>("/accounts/");
}
