import { NavLink, Outlet, useParams } from "react-router-dom";

const REPORTS = [
  { path: "trial-balance", label: "Trial Balance" },
  { path: "balance-sheet", label: "Balance Sheet" },
  { path: "cash-flow", label: "Cash Flow Statement" },
  { path: "income-statement", label: "Income Statement" },
  { path: "account-ledger", label: "Account Ledger" },
  { path: "budget-vs-actual", label: "Budget vs Actual" },
  { path: "net-worth", label: "Net Worth" },
];

export function ReportsLayout() {
  const { entityId } = useParams<{ entityId: string }>();
  if (!entityId) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Reports</h1>
      <nav className="flex items-center gap-4 border-b text-sm">
        {REPORTS.map((report) => (
          <NavLink
            key={report.path}
            to={`/entities/${entityId}/reports/${report.path}`}
            className={({ isActive }) =>
              `pb-2 -mb-px border-b-2 ${
                isActive
                  ? "border-foreground font-medium text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`
            }
          >
            {report.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
