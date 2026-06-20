import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { confirmImport, previewImport } from "@/api/imports";
import { ApiError } from "@/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ColumnMappingStep } from "@/components/imports/ColumnMappingStep";
import { FileUploadStep } from "@/components/imports/FileUploadStep";
import { ImportSummary } from "@/components/imports/ImportSummary";
import type {
  ColumnMapping,
  ImportBatch,
  ImportFileFormat,
  ImportPreviewRow,
  InlineMappingFields,
} from "@/types/api";

type WizardStep = "upload" | "mapping" | "mapped-preview" | "done";

export function ImportPage() {
  const { entityId, accountId } = useParams<{ entityId: string; accountId: string }>();
  const [step, setStep] = useState<WizardStep>("upload");
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<ImportFileFormat>("CSV");
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawPreviewRows, setRawPreviewRows] = useState<Record<string, string>[]>([]);
  const [mappedPreviewRows, setMappedPreviewRows] = useState<ImportPreviewRow[]>([]);
  const [availableMappings, setAvailableMappings] = useState<ColumnMapping[]>([]);
  const [inlineMapping, setInlineMapping] = useState<InlineMappingFields | undefined>(undefined);
  const [columnMappingId, setColumnMappingId] = useState<string | undefined>(undefined);
  const [saveMappingAs, setSaveMappingAs] = useState("");
  const [batch, setBatch] = useState<ImportBatch | null>(null);

  const previewMutation = useMutation({ mutationFn: previewImport });
  const confirmMutation = useMutation({ mutationFn: confirmImport });

  function handleApiError(err: unknown) {
    if (err instanceof ApiError) {
      const body = err.body as { non_field_errors?: string[] } | null;
      setError(body?.non_field_errors?.join(" ") ?? "Something went wrong.");
    } else {
      setError("Something went wrong.");
    }
  }

  async function handleFileSubmit(selectedFile: File, format: ImportFileFormat) {
    if (!accountId) return;
    setError(null);
    setFile(selectedFile);
    setFileFormat(format);
    try {
      const result = await previewMutation.mutateAsync({
        account: accountId,
        fileFormat: format,
        file: selectedFile,
      });
      if (result.mapped) {
        setMappedPreviewRows(result.preview_rows as ImportPreviewRow[]);
        setStep("mapped-preview");
      } else {
        setHeaders(result.headers ?? []);
        setRawPreviewRows(result.preview_rows as Record<string, string>[]);
        setAvailableMappings(result.available_mappings ?? []);
        setStep("mapping");
      }
    } catch (err) {
      handleApiError(err);
    }
  }

  async function handleMappingSubmit(mapping: InlineMappingFields) {
    if (!accountId || !file) return;
    setError(null);
    try {
      const result = await previewMutation.mutateAsync({
        account: accountId,
        fileFormat,
        file,
        inlineMapping: mapping,
      });
      setInlineMapping(mapping);
      setColumnMappingId(undefined);
      setMappedPreviewRows(result.preview_rows as ImportPreviewRow[]);
      setStep("mapped-preview");
    } catch (err) {
      handleApiError(err);
    }
  }

  async function handleSelectSavedMapping(mappingId: string) {
    if (!accountId || !file) return;
    setError(null);
    try {
      const result = await previewMutation.mutateAsync({
        account: accountId,
        fileFormat,
        file,
        columnMappingId: mappingId,
      });
      setColumnMappingId(mappingId);
      setInlineMapping(undefined);
      setMappedPreviewRows(result.preview_rows as ImportPreviewRow[]);
      setStep("mapped-preview");
    } catch (err) {
      handleApiError(err);
    }
  }

  async function handleConfirm() {
    if (!accountId || !file) return;
    setError(null);
    try {
      const result = await confirmMutation.mutateAsync({
        account: accountId,
        fileFormat,
        file,
        inlineMapping,
        columnMappingId,
        saveMappingAs: saveMappingAs || undefined,
      });
      setBatch(result);
      setStep("done");
    } catch (err) {
      handleApiError(err);
    }
  }

  if (!entityId || !accountId) return null;

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-xl font-semibold">Import statement</h1>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not import</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {step === "upload" && (
        <FileUploadStep onSubmit={handleFileSubmit} isSubmitting={previewMutation.isPending} />
      )}

      {step === "mapping" && (
        <ColumnMappingStep
          headers={headers}
          previewRows={rawPreviewRows}
          availableMappings={availableMappings}
          onSubmitMapping={handleMappingSubmit}
          onSelectSavedMapping={handleSelectSavedMapping}
          isSubmitting={previewMutation.isPending}
        />
      )}

      {step === "mapped-preview" && (
        <div className="space-y-4 rounded-lg border p-4">
          <h2 className="font-medium">Preview</h2>
          <div className="overflow-x-auto rounded border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mappedPreviewRows.map((row, i) => (
                  <TableRow key={i}>
                    <TableCell>{row.transaction_date}</TableCell>
                    <TableCell>{row.description}</TableCell>
                    <TableCell className="text-right">{row.amount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {fileFormat === "CSV" && !columnMappingId && (
            <div className="space-y-2 max-w-sm">
              <Label htmlFor="save-mapping-as">Save this mapping as (optional)</Label>
              <Input
                id="save-mapping-as"
                value={saveMappingAs}
                onChange={(e) => setSaveMappingAs(e.target.value)}
                placeholder="e.g. CommBank Everyday CSV"
              />
            </div>
          )}
          <Button onClick={handleConfirm} disabled={confirmMutation.isPending}>
            {confirmMutation.isPending ? "Importing…" : "Confirm import"}
          </Button>
        </div>
      )}

      {step === "done" && batch && <ImportSummary batch={batch} entityId={entityId} />}
    </div>
  );
}
