import { cn } from "@/lib/utils";

interface ProgressBarProps {
  percent: number | null;
  className?: string;
}

export function ProgressBar({ percent, className }: ProgressBarProps) {
  const clamped = percent === null ? 0 : Math.max(0, Math.min(100, percent));
  const overBudget = percent !== null && percent > 100;

  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-muted", className)}>
      <div
        className={cn("h-full rounded-full", overBudget ? "bg-destructive" : "bg-primary")}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
