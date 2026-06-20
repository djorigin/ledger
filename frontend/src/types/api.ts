// Mirrors the DRF serializers in backend/apps/api/serializers/ exactly.
// Money fields (debit_amount/credit_amount) are JSON strings, never
// numbers -- the backend's MoneyField deliberately renders Decimal as a
// string so nothing here should ever parse them into a JS `number` for
// anything that matters financially.

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type EntityType = "HOUSEHOLD" | "BUSINESS" | "PROPERTY" | "SUPERANNUATION" | "OTHER";
export type EntityRole = "OWNER" | "EDITOR" | "VIEWER";
export type AccountType = "ASSET" | "LIABILITY" | "EQUITY" | "INCOME" | "EXPENSE";
export type JournalEntryStatus = "DRAFT" | "POSTED" | "REVERSED";

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Account {
  id: string;
  entity: string;
  parent: string | null;
  account_type: AccountType;
  name: string;
  code: string;
  native_currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  entity_id: string;
  entity_name: string;
  role: EntityRole;
}

export interface MeResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  memberships: Membership[];
}

export interface JournalLine {
  id: string;
  account: string;
  debit_amount: string;
  credit_amount: string;
  currency: string;
  description: string;
}

export interface JournalEntry {
  id: string;
  entity: string;
  entry_date: string;
  description: string;
  memo: string;
  status: JournalEntryStatus;
  created_by: string;
  created_at: string;
  posted_at: string | null;
  reverses: string | null;
  reversed_by: string | null;
  lines_detail: JournalLine[];
}

export interface JournalLineInput {
  account: string;
  currency: string;
  debit_amount?: string;
  credit_amount?: string;
  description?: string;
}

export interface CreateJournalEntryPayload {
  entity: string;
  entry_date: string;
  description: string;
  memo?: string;
  lines: JournalLineInput[];
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export type ImportFileFormat = "CSV" | "OFX";
export type ImportBatchStatus = "PREVIEW" | "IMPORTED" | "FAILED";
export type ImportedTransactionStatus = "UNMATCHED" | "MATCHED" | "POSTED" | "IGNORED";
export type AmountConvention = "SIGNED_AMOUNT" | "DEBIT_CREDIT";

export interface ColumnMapping {
  id: string;
  account: string;
  name: string;
  date_column: string;
  date_format: string;
  description_column: string;
  memo_column: string;
  amount_convention: AmountConvention;
  amount_column: string;
  debit_column: string;
  credit_column: string;
  type_column: string;
  type_debit_value: string;
  balance_column: string;
  has_header_row: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ImportBatch {
  id: string;
  account: string;
  file_format: ImportFileFormat;
  original_filename: string;
  column_mapping: string | null;
  status: ImportBatchStatus;
  statement_start_date: string | null;
  statement_end_date: string | null;
  row_count: number;
  duplicate_count: number;
  imported_by: string;
  created_at: string;
  confirmed_at: string | null;
}

export interface ImportedTransaction {
  id: string;
  import_batch: string;
  account: string;
  transaction_date: string;
  description: string;
  memo: string;
  amount: string; // money: string, never number
  running_balance: string | null;
  external_id: string;
  status: ImportedTransactionStatus;
  matched_line: string | null;
  created_entry: string | null;
  matched_by: string | null;
  matched_at: string | null;
}

export interface ImportPreviewRow {
  transaction_date: string;
  description: string;
  memo: string;
  amount: string;
  running_balance: string | null;
}

export interface ImportPreviewResponse {
  file_format: ImportFileFormat;
  mapped: boolean;
  headers?: string[];
  preview_rows: ImportPreviewRow[] | Record<string, string>[];
  total_row_count: number;
  available_mappings?: ColumnMapping[];
}

export interface InlineMappingFields {
  date_column?: string;
  date_format?: string;
  description_column?: string;
  memo_column?: string;
  amount_convention?: AmountConvention;
  amount_column?: string;
  debit_column?: string;
  credit_column?: string;
  type_column?: string;
  type_debit_value?: string;
  balance_column?: string;
  has_header_row?: boolean;
}

export interface ReconciliationRecord {
  id: string;
  account: string;
  statement_date: string;
  statement_balance: string;
  reconciled_by: string;
  reconciled_at: string;
  notes: string;
}
