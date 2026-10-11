import { cn } from "cn";

// Owner verdicts in a fixed order and color, shared by the decision path and the councils tab.
export const VERDICTS = [
  { key: "must_have", label: "Must have", color: "bg-emerald-600" },
  { key: "nice_to_have", label: "Nice to have", color: "bg-emerald-300 dark:bg-emerald-700" },
  { key: "dont_care", label: "Don't care", color: "bg-zinc-300 dark:bg-zinc-600" },
  { key: "against", label: "Against", color: "bg-red-400" },
  { key: "unknown", label: "Not asked", color: "bg-muted-foreground/20" },
] as const;

export function verdictLabel(verdict: string | null | undefined): string {
  return VERDICTS.find((v) => v.key === (verdict ?? "unknown"))?.label ?? verdict ?? "Not asked";
}

export function verdictColor(verdict: string | null | undefined): string {
  return VERDICTS.find((v) => v.key === (verdict ?? "unknown"))?.color ?? "bg-muted-foreground/20";
}

export function VerdictBar({ verdicts, className }: { verdicts: Record<string, number>; className?: string }) {
  const total = Object.values(verdicts).reduce((n, v) => n + v, 0);
  const title = VERDICTS.filter((v) => verdicts[v.key])
    .map((v) => `${verdicts[v.key]} ${v.label.toLowerCase()}`)
    .join(" · ");
  return (
    <span className={cn("flex h-1.5 min-w-16 overflow-hidden rounded-full bg-muted", className)} title={title} role="img" aria-label={title}>
      {VERDICTS.map((v) =>
        verdicts[v.key] ? <span key={v.key} className={v.color} style={{ width: `${(verdicts[v.key] / Math.max(total, 1)) * 100}%` }} /> : null,
      )}
    </span>
  );
}

// Budget points are shared: each owner splits 100 points over every proposal of the run plus "keep the price down".
export function BudgetBar({ points, className }: { points: number | null | undefined; className?: string }) {
  if (points == null) return <span className="text-xs text-muted-foreground">not asked</span>;
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <span className="flex h-1.5 w-20 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span className="bg-sky-600" style={{ width: `${Math.min(100, Math.max(0, points))}%` }} />
      </span>
      <span className="text-xs tabular-nums">{points.toFixed(0)}</span>
    </span>
  );
}
