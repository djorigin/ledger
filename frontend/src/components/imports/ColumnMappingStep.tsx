import { useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AmountConvention, ColumnMapping, InlineMappingFields } from "@/types/api";

const DATE_FORMAT_PRESETS = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"];

interface ColumnSelectProps {
  label: string;
  headers: string[];
  value: string;
  onChange: (value: string) => void;
  allowNone?: boolean;
}

function ColumnSelect({ label, headers, value, onChange, allowNone }: ColumnSelectProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Select value={value} onValueChange={(v) => onChange(v ?? "")}>
        <SelectTrigger>
          <SelectValue placeholder="Select column">
            {(v: string | null) => v || null}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {allowNone && (
            <SelectItem value="" label="(none)">
              (none)
            </SelectItem>
          )}
          {headers.map((header) => (
            <SelectItem key={header} value={header} label={header}>
              {header}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface ColumnMappingStepProps {
  headers: string[];
  previewRows: Record<string, string>[];
  availableMappings: ColumnMapping[];
  onSubmitMapping: (mapping: InlineMappingFields) => void;
  onSelectSavedMapping: (mappingId: string) => void;
  isSubmitting: boolean;
}

export function ColumnMappingStep({
  headers,
  previewRows,
  availableMappings,
  onSubmitMapping,
  onSelectSavedMapping,
  isSubmitting,
}: ColumnMappingStepProps) {
  const [dateColumn, setDateColumn] = useState("");
  const [dateFormat, setDateFormat] = useState(DATE_FORMAT_PRESETS[0]);
  const [descriptionColumn, setDescriptionColumn] = useState("");
  const [memoColumn, setMemoColumn] = useState("");
  const [amountConvention, setAmountConvention] = useState<AmountConvention>("DEBIT_CREDIT");
  const [amountColumn, setAmountColumn] = useState("");
  const [debitColumn, setDebitColumn] = useState("");
  const [creditColumn, setCreditColumn] = useState("");
  const [balanceColumn, setBalanceColumn] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmitMapping({
      date_column: dateColumn,
      date_format: dateFormat,
      description_column: descriptionColumn,
      memo_column: memoColumn,
      amount_convention: amountConvention,
      amount_column: amountConvention === "SIGNED_AMOUNT" ? amountColumn : undefined,
      debit_column: amountConvention === "DEBIT_CREDIT" ? debitColumn : undefined,
      credit_column: amountConvention === "DEBIT_CREDIT" ? creditColumn : undefined,
      balance_column: balanceColumn || undefined,
    });
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">Map columns</h2>

      {availableMappings.length > 0 && (
        <div className="space-y-2 max-w-sm">
          <Label>Use a saved mapping</Label>
          <Select onValueChange={(id: string | null) => id && onSelectSavedMapping(id)}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a saved mapping" />
            </SelectTrigger>
            <SelectContent>
              {availableMappings.map((mapping) => (
                <SelectItem key={mapping.id} value={mapping.id} label={mapping.name}>
                  {mapping.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="overflow-x-auto rounded border">
        <Table>
          <TableHeader>
            <TableRow>
              {headers.map((h) => (
                <TableHead key={h}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {previewRows.map((row, i) => (
              <TableRow key={i}>
                {headers.map((h) => (
                  <TableCell key={h}>{row[h]}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <ColumnSelect label="Date column" headers={headers} value={dateColumn} onChange={setDateColumn} />
          <div className="space-y-2">
            <Label>Date format</Label>
            <Select value={dateFormat} onValueChange={(v) => v && setDateFormat(v)}>
              <SelectTrigger>
                <SelectValue>{(v: string | null) => v}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {DATE_FORMAT_PRESETS.map((fmt) => (
                  <SelectItem key={fmt} value={fmt} label={fmt}>
                    {fmt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <ColumnSelect
            label="Description column"
            headers={headers}
            value={descriptionColumn}
            onChange={setDescriptionColumn}
          />
          <ColumnSelect
            label="Memo column (optional)"
            headers={headers}
            value={memoColumn}
            onChange={setMemoColumn}
            allowNone
          />
          <ColumnSelect
            label="Balance column (optional)"
            headers={headers}
            value={balanceColumn}
            onChange={setBalanceColumn}
            allowNone
          />
          <div className="space-y-2">
            <Label>Amount style</Label>
            <Select
              value={amountConvention}
              onValueChange={(v) => v && setAmountConvention(v as AmountConvention)}
            >
              <SelectTrigger>
                <SelectValue>{(v: string | null) => v}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DEBIT_CREDIT" label="Separate debit/credit columns">
                  Separate debit/credit columns
                </SelectItem>
                <SelectItem value="SIGNED_AMOUNT" label="Single signed amount column">
                  Single signed amount column
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          {amountConvention === "SIGNED_AMOUNT" ? (
            <ColumnSelect
              label="Amount column"
              headers={headers}
              value={amountColumn}
              onChange={setAmountColumn}
            />
          ) : (
            <>
              <ColumnSelect
                label="Debit column"
                headers={headers}
                value={debitColumn}
                onChange={setDebitColumn}
                allowNone
              />
              <ColumnSelect
                label="Credit column"
                headers={headers}
                value={creditColumn}
                onChange={setCreditColumn}
                allowNone
              />
            </>
          )}
        </div>
        <Button type="submit" disabled={isSubmitting || !dateColumn || !descriptionColumn}>
          {isSubmitting ? "Loading preview…" : "Preview mapped rows"}
        </Button>
      </form>
    </div>
  );
}
