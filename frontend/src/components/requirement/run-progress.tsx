"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { refreshAll, useRun } from "@/lib/api/hooks";
import { STAGE_LABEL, STAGES } from "@/lib/format";
import { cn } from "cn";

const ACTIVE = new Set(["queued", "running"]);

// Thin stage strip while a run is queued or running. When it finishes, everything refetches.
export function RunProgress({ runId }: { runId: string | null }) {
  const { data } = useRun(runId);
  const previous = useRef<string | undefined>(undefined);
  const status = data?.run.status;

  useEffect(() => {
    if (previous.current && ACTIVE.has(previous.current) && status && !ACTIVE.has(status)) {
      if (status === "completed") toast.success("Run finished");
      else toast.warning(`Run ${status}${data?.run.error ? `: ${data.run.error}` : ""}`);
      void refreshAll();
    }
    previous.current = status;
  }, [status, data?.run.error]);

  if (!data || !status || !ACTIVE.has(status)) return null;
  const done = new Set(data.run.progress?.completed_stages ?? []);
  const current = data.run.progress?.stage;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground" role="status">
      <span className="flex items-center gap-1.5 text-foreground">
        <span className="size-1.5 animate-pulse rounded-full bg-blue-600" aria-hidden />
        {status === "queued" ? "Queued" : "Running"}
      </span>
      {STAGES.map((stage) => (
        <span key={stage} className={cn("flex items-center gap-1.5", stage === current && "text-foreground")}>
          <span
            className={cn(
              "size-1.5 rounded-full",
              done.has(stage) ? "bg-foreground" : stage === current ? "bg-blue-600" : "bg-border",
            )}
            aria-hidden
          />
          {STAGE_LABEL[stage]}
        </span>
      ))}
      <span className="tabular-nums">{data.run.llm_calls} LLM calls</span>
    </div>
  );
}
