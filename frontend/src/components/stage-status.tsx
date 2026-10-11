import type { StageStatus } from "@/lib/api/types";
import { STATUS_LABEL } from "@/lib/stages";
import { cn } from "cn";

export function StageStatusDot({ status, className }: { status: StageStatus; className?: string }) {
  return (
    <span
      role="img"
      aria-label={STATUS_LABEL[status]}
      className={cn(
        "inline-block size-2.5 shrink-0 rounded-full",
        status === "done" && "bg-emerald-600",
        status === "in_progress" && "bg-amber-500",
        status === "todo" && "border border-muted-foreground/50 bg-background",
        className,
      )}
    />
  );
}
