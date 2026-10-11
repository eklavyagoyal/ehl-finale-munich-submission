import { cn } from "cn";

// Thin track on a 0..max scale with the low–high band filled. A point value gets a short mark.
export function ScoreBar({
  low,
  high,
  max = 100,
  hypothesis = false,
  className,
}: {
  low: number | null | undefined;
  high: number | null | undefined;
  max?: number;
  hypothesis?: boolean;
  className?: string;
}) {
  const has = low != null && high != null;
  const l = has ? Math.max(0, Math.min(100, (low! / max) * 100)) : 0;
  const h = has ? Math.max(l, Math.min(100, (high! / max) * 100)) : 0;
  return (
    <span className={cn("relative h-1 w-12 shrink-0 rounded-full bg-muted", className)} aria-hidden>
      {has && (
        <span
          className={cn(
            "absolute inset-y-0 rounded-full",
            hypothesis ? "bg-[repeating-linear-gradient(90deg,var(--foreground)_0_3px,transparent_3px_5px)] opacity-70" : "bg-foreground",
          )}
          style={{ left: `${l}%`, width: `${Math.max(h - l, 2)}%` }}
        />
      )}
    </span>
  );
}
