import { useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ImportFileFormat } from "@/types/api";

interface FileUploadStepProps {
  onSubmit: (file: File, fileFormat: ImportFileFormat) => void;
  isSubmitting: boolean;
}

export function FileUploadStep({ onSubmit, isSubmitting }: FileUploadStepProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<ImportFileFormat>("CSV");

  function handleFileChange(selected: File | null) {
    setFile(selected);
    if (selected && /\.(ofx|qfx)$/i.test(selected.name)) {
      setFileFormat("OFX");
    } else if (selected) {
      setFileFormat("CSV");
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    onSubmit(file, fileFormat);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">Upload statement</h2>
      <div className="space-y-2">
        <Label htmlFor="statement-file">File</Label>
        <Input
          id="statement-file"
          type="file"
          accept=".csv,.ofx,.qfx"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
          required
        />
      </div>
      <div className="space-y-2 max-w-[200px]">
        <Label>Format</Label>
        <Select
          value={fileFormat}
          onValueChange={(value) => value && setFileFormat(value as ImportFileFormat)}
        >
          <SelectTrigger>
            <SelectValue>{(value: string | null) => value ?? "CSV"}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="CSV" label="CSV">CSV</SelectItem>
            <SelectItem value="OFX" label="OFX">OFX</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" disabled={!file || isSubmitting}>
        {isSubmitting ? "Reading…" : "Continue"}
      </Button>
    </form>
  );
}
