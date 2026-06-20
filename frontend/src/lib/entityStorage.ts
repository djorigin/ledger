const LAST_ENTITY_STORAGE_KEY = "ledger.lastEntityId";

export function getLastSelectedEntityId(): string | null {
  return localStorage.getItem(LAST_ENTITY_STORAGE_KEY);
}

export function setLastSelectedEntityId(entityId: string): void {
  localStorage.setItem(LAST_ENTITY_STORAGE_KEY, entityId);
}
