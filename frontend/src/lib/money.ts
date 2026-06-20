import Decimal from "decimal.js";

// Money amounts arrive from the API as strings (e.g. "50.0000") -- never
// parse them into a native JS number for anything that matters
// financially. This module is display-only formatting via decimal.js, not
// a substitute for the backend's own balance/currency validation.

export function formatMoney(amount: string, currency: string): string {
  const value = new Decimal(amount);
  return `${value.toFixed(2)} ${currency}`;
}

export function isZeroOrBlank(amount: string | undefined): boolean {
  if (!amount) return true;
  try {
    return new Decimal(amount).isZero();
  } catch {
    return true;
  }
}
