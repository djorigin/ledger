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
