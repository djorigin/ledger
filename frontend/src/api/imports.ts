import { apiRequest } from "@/api/client";
import type {
  ColumnMapping,
  ImportBatch,
  ImportedTransaction,
  ImportFileFormat,
  ImportPreviewResponse,
  InlineMappingFields,
  JournalLine,
  PaginatedResponse,
} from "@/types/api";

interface ImportRequestPayload {
  account: string;
  fileFormat: ImportFileFormat;
  file: File;
  columnMappingId?: string;
  inlineMapping?: InlineMappingFields;
}

function buildImportFormData(payload: ImportRequestPayload): FormData {
  const form = new FormData();
  form.append("account", payload.account);
  form.append("file_format", payload.fileFormat);
  form.append("file", payload.file);
  if (payload.columnMappingId) {
    form.append("column_mapping", payload.columnMappingId);
  }
  if (payload.inlineMapping) {
    for (const [key, value] of Object.entries(payload.inlineMapping)) {
      if (value !== undefined && value !== "") {
        form.append(key, String(value));
      }
    }
  }
  return form;
}

export function previewImport(payload: ImportRequestPayload): Promise<ImportPreviewResponse> {
  return apiRequest<ImportPreviewResponse>("/import-batches/preview/", {
    method: "POST",
    body: buildImportFormData(payload),
  });
}

export function confirmImport(
  payload: ImportRequestPayload & { saveMappingAs?: string },
): Promise<ImportBatch> {
  const form = buildImportFormData(payload);
  if (payload.saveMappingAs) {
    form.append("save_mapping_as", payload.saveMappingAs);
  }
  return apiRequest<ImportBatch>("/import-batches/confirm/", { method: "POST", body: form });
}

export function listImportBatches(accountId?: string): Promise<PaginatedResponse<ImportBatch>> {
  return apiRequest<PaginatedResponse<ImportBatch>>("/import-batches/", {
    searchParams: { account: accountId },
  });
}

export function listBatchTransactions(batchId: string): Promise<ImportedTransaction[]> {
  return apiRequest<ImportedTransaction[]>(`/import-batches/${batchId}/transactions/`);
}

export function listImportedTransactions(
  accountId?: string,
): Promise<PaginatedResponse<ImportedTransaction>> {
  return apiRequest<PaginatedResponse<ImportedTransaction>>("/imported-transactions/", {
    searchParams: { account: accountId },
  });
}

export function getCandidateMatches(importedTransactionId: string): Promise<JournalLine[]> {
  return apiRequest<JournalLine[]>(
    `/imported-transactions/${importedTransactionId}/candidate-matches/`,
  );
}

export function confirmMatch(
  importedTransactionId: string,
  journalLineId: string,
): Promise<ImportedTransaction> {
  return apiRequest<ImportedTransaction>(
    `/imported-transactions/${importedTransactionId}/confirm-match/`,
    { method: "POST", body: { journal_line: journalLineId } },
  );
}

export function createEntryFromImport(
  importedTransactionId: string,
  offsettingAccountId: string,
  description?: string,
): Promise<ImportedTransaction> {
  return apiRequest<ImportedTransaction>(
    `/imported-transactions/${importedTransactionId}/create-entry/`,
    { method: "POST", body: { offsetting_account: offsettingAccountId, description } },
  );
}

export function ignoreImportedTransaction(
  importedTransactionId: string,
): Promise<ImportedTransaction> {
  return apiRequest<ImportedTransaction>(
    `/imported-transactions/${importedTransactionId}/ignore/`,
    { method: "POST", body: {} },
  );
}

export function listColumnMappings(accountId: string): Promise<PaginatedResponse<ColumnMapping>> {
  return apiRequest<PaginatedResponse<ColumnMapping>>("/column-mappings/", {
    searchParams: { account: accountId },
  });
}
