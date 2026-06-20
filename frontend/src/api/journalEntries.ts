import { apiRequest } from "@/api/client";
import type { CreateJournalEntryPayload, JournalEntry, PaginatedResponse } from "@/types/api";

// JournalEntryViewSet has no query-param entity filter today -- fetch the
// full accessible list and filter client-side per entity. Fine at this
// app's data volumes; revisit (server-side filter + real pagination) once
// a single entity's history could exceed one page.
export function listJournalEntries(): Promise<PaginatedResponse<JournalEntry>> {
  return apiRequest<PaginatedResponse<JournalEntry>>("/journal-entries/");
}

export function createJournalEntry(
  payload: CreateJournalEntryPayload,
): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("/journal-entries/", {
    method: "POST",
    body: payload,
  });
}

export function reverseJournalEntry(entryId: string): Promise<JournalEntry> {
  return apiRequest<JournalEntry>(`/journal-entries/${entryId}/reverse/`, {
    method: "POST",
    body: {},
  });
}
