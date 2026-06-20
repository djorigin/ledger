import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { JournalEntryRow } from "@/components/journal-entries/JournalEntryRow";
import type { Account, JournalEntry } from "@/types/api";

interface JournalEntryListProps {
  entries: JournalEntry[];
  accounts: Account[];
}

export function JournalEntryList({ entries, accounts }: JournalEntryListProps) {
  const accountsById = new Map(accounts.map((a) => [a.id, a]));

  if (entries.length === 0) {
    return <p className="text-muted-foreground">No transactions yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Account</TableHead>
          <TableHead className="text-right">Debit</TableHead>
          <TableHead className="text-right">Credit</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <JournalEntryRow key={entry.id} entry={entry} accountsById={accountsById} />
        ))}
      </TableBody>
    </Table>
  );
}
