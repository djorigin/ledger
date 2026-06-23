/**
 * Ledger -> Google Sheets sync.
 *
 * Lives in Google Sheets (Extensions > Apps Script), not in the app repo
 * it talks to -- this copy is checked into the ledger repo purely as a
 * reference/diff target, it does not run there.
 *
 * Auth: a long-lived, read-only APIToken (apps.api_tokens.models.APIToken),
 * created once via Django Admin (a user with OWNER role on an entity can
 * generate one) and shown exactly once at creation time. This is
 * deliberately *not* the JWT flow the React frontend uses -- Apps Script
 * can't do JWT's rotating-refresh-token dance, so the backend exposes a
 * separate, simpler "Authorization: Token <token>" scheme just for this.
 * The token is enforced read-only server-side (DenyApiTokenWriteMiddleware)
 * regardless of what role the underlying user actually has, so even if
 * this script is buggy it cannot write anything back to the ledger.
 *
 * Setup:
 *   1. Extensions > Apps Script > Project Settings > Script Properties.
 *   2. Add LEDGER_BASE_URL (e.g. https://ledger.example.com/api/v1) and
 *      LEDGER_API_TOKEN (the plaintext shown once at creation).
 *      Never hardcode the token directly in this file.
 *   3. Reload the spreadsheet -- the "Ledger" menu (added by onOpen())
 *      appears, with "Refresh from Ledger".
 */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Ledger")
    .addItem("Refresh from Ledger", "refreshAll")
    .addToUi();
}

function refreshAll() {
  syncConsolidatedNetWorth();
  syncPayslipSummary();
}

/**
 * Generic GET against the ledger API, authenticated via the read-only
 * token. Throws (visibly, in the Apps Script execution log) on a non-200
 * response rather than silently writing nothing -- a stale number you
 * know is stale is far better than one you don't.
 */
function fetchLedgerJson(path) {
  const props = PropertiesService.getScriptProperties();
  const baseUrl = props.getProperty("LEDGER_BASE_URL");
  const token = props.getProperty("LEDGER_API_TOKEN");
  if (!baseUrl || !token) {
    throw new Error(
      "Set LEDGER_BASE_URL and LEDGER_API_TOKEN in Project Settings > Script Properties first."
    );
  }

  const response = UrlFetchApp.fetch(baseUrl + path, {
    method: "get",
    headers: { Authorization: "Token " + token },
    muteHttpExceptions: true,
  });

  if (response.getResponseCode() !== 200) {
    throw new Error(
      "Ledger API request failed (" + response.getResponseCode() + "): " + response.getContentText()
    );
  }
  return JSON.parse(response.getContentText());
}

/** Writes (or replaces) a sheet tab from an array of row objects, using
 * the keys of the first row as the header. Shared by every sync function
 * below -- don't reimplement this per endpoint. */
function writeRowsToSheet(sheetName, rows) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(sheetName);
  }
  if (rows.length === 0) {
    sheet.getRange(1, 1).setValue("(no data)");
    return;
  }
  const headers = Object.keys(rows[0]);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  const values = rows.map((row) => headers.map((key) => row[key]));
  sheet.getRange(2, 1, values.length, headers.length).setValues(values);
}

/**
 * GET /reports/consolidated-net-worth/ -- GL net worth + Fixed Asset
 * Register valuations, per entity. This is the report Addition 4 was
 * built around.
 */
function syncConsolidatedNetWorth() {
  const data = fetchLedgerJson("/reports/consolidated-net-worth/?reporting_currency=AUD");
  writeRowsToSheet("Net Worth", data.rows);
}

/**
 * GET /payslips/summary/ -- a second worked example showing the
 * copy-paste-and-rename pattern: swap the path, the query string, and the
 * sheet name; writeRowsToSheet()/fetchLedgerJson() don't change.
 *
 * NOTE: replace ENTITY_ID below with the real entity UUID (Smith
 * Household, etc.) -- unlike net-worth, this endpoint is scoped to one
 * entity, not "every entity the token's user can access".
 */
function syncPayslipSummary() {
  const ENTITY_ID = "REPLACE_WITH_ENTITY_UUID";
  const data = fetchLedgerJson("/payslips/summary/?entity=" + ENTITY_ID);
  writeRowsToSheet("Payslip Summary", [data]);
}

/**
 * Other endpoints available by the same pattern (see the ledger repo's
 * apps/api/urls.py for the full, current list):
 *   /reports/trial-balance/?entity=<id>&as_of=<date>
 *   /reports/balance-sheet/?entity=<id>&as_of=<date>&reporting_currency=AUD
 *   /reports/cash-flow/?entity=<id>&period_start=<date>&period_end=<date>&reporting_currency=AUD
 *   /reports/income-statement/?entity=<id>&period_start=<date>&period_end=<date>&reporting_currency=AUD
 *   /reports/budget-vs-actual/?entity=<id>&reporting_currency=AUD
 *   /reports/net-worth/?reporting_currency=AUD          (GL only, no asset register)
 *   /asset-classes/net-worth-summary/?reporting_currency=AUD
 *   /inventory/summary/?entity=<id>
 */
