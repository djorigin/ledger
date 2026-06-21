import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "@/api/client";
import { createProject } from "@/api/projects";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ProjectFormProps {
  entityId: string;
}

export function ProjectForm({ entityId }: ProjectFormProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [currency, setCurrency] = useState("AUD");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setName("");
      setDescription("");
      setBudgetAmount("");
      setError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        const body = err.body as { non_field_errors?: string[] } | null;
        setError(body?.non_field_errors?.join(" ") ?? "Could not create project.");
      } else {
        setError("Could not create project.");
      }
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name || !budgetAmount || !currency) {
      setError("Name, budget amount, and currency are required.");
      return;
    }
    mutation.mutate({
      entity: entityId,
      name,
      description,
      budget_amount: budgetAmount,
      currency,
      status: "ACTIVE",
      start_date: null,
      target_completion_date: null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border p-4">
      <h2 className="font-medium">New project</h2>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label htmlFor="project-name">Name</Label>
          <Input id="project-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-description">Description</Label>
          <Input
            id="project-description" value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-budget">Budget amount</Label>
          <Input
            id="project-budget" inputMode="decimal" value={budgetAmount}
            onChange={(e) => setBudgetAmount(e.target.value)} placeholder="0.00" required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-currency">Currency</Label>
          <Input
            id="project-currency" value={currency}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())} maxLength={3} required
          />
        </div>
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Create project"}
      </Button>
    </form>
  );
}
