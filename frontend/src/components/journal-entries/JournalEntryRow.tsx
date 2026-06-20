import { TableCell, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/money";
import type { Account, JournalEntry } from "@/types/api";

interface JournalEntryRowProps {
  entry: JournalEntry;
  accountsById: Map<string, Account>;
}

export function JournalEntryRow({ entry, accountsById }: JournalEntryRowProps) {
  return (
    <>
      {entry.lines_detail.map((line, index) => (
        <TableRow key={line.id}>
          {index === 0 ? (
            <>
              <TableCell rowSpan={entry.lines_detail.length}>{entry.entry_date}</TableCell>
              <TableCell rowSpan={entry.lines_detail.length}>
                {entry.description}
                {entry.status === "REVERSED" && (
                  <span className="ml-2 text-xs text-muted-foreground">(reversed)</span>
                )}
              </TableCell>
            </>
          ) : null}
          <TableCell>{accountsById.get(line.account)?.name ?? line.account}</TableCell>
          <TableCell className="text-right">
            {line.debit_amount !== "0.0000" ? formatMoney(line.debit_amount, line.currency) : ""}
          </TableCell>
          <TableCell className="text-right">
            {line.credit_amount !== "0.0000" ? formatMoney(line.credit_amount, line.currency) : ""}
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}
