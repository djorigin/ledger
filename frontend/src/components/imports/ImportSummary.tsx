import { Link } from "react-router-dom";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ImportBatch } from "@/types/api";

interface ImportSummaryProps {
  batch: ImportBatch;
  entityId: string;
}

export function ImportSummary({ batch, entityId }: ImportSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Import complete</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p>
          Imported <strong>{batch.row_count}</strong> transaction
          {batch.row_count === 1 ? "" : "s"}.
          {batch.duplicate_count > 0 && (
            <>
              {" "}
              <strong>{batch.duplicate_count}</strong> already existed and{" "}
              {batch.duplicate_count === 1 ? "was" : "were"} skipped.
            </>
          )}
        </p>
        <Link
          to={`/entities/${entityId}/accounts/${batch.account}/reconciliation`}
          className={buttonVariants({ variant: "default" })}
        >
          Go to reconciliation
        </Link>
      </CardContent>
    </Card>
  );
}
