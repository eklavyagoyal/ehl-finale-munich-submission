"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { refreshAll, startRun, useTasks } from "@/lib/api/hooks";
import type { Task } from "@/lib/api/types";
import { fmtRange, fmtScore, humanize, STAGE_LABEL } from "@/lib/format";

const GROUPS: { kind: string; title: string }[] = [
  { kind: "decide", title: "To decide" },
  { kind: "running", title: "Running" },
  { kind: "simulate", title: "Ready to simulate" },
  { kind: "review_evidence", title: "Evidence to review" },
];

export default function TasksPage() {
  const { data, error, isLoading } = useTasks();

  return (
    <>
      <PageHeader crumbs={[{ label: "My tasks" }]} />
      <div className="mt-4 flex max-w-5xl flex-col gap-10">
        {error && <ErrorState error={error} />}
        {isLoading && <LoadingRows />}
        {data && data.length === 0 && (
          <EmptyState title="Nothing waits for you">
            New requirements appear here once evidence is imported and drafted. The{" "}
            <Link href="/pipeline" className="text-foreground underline-offset-4 hover:underline">
              pipeline
            </Link>{" "}
            shows the next step.
          </EmptyState>
        )}
        {data &&
          GROUPS.map((group) => {
            const items = data.filter((t) => t.kind === group.kind);
            if (items.length === 0) return null;
            return (
              <section key={group.kind}>
                <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">
                  {group.title} <span className="ml-1 text-muted-foreground/60">{items.length}</span>
                </h2>
                {items.map((task, i) => (
                  <TaskRow key={`${task.kind}-${task.requirement_id ?? task.run_id ?? i}`} task={task} />
                ))}
              </section>
            );
          })}
      </div>
    </>
  );
}

function TaskRow({ task }: { task: Task }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function simulate() {
    if (!task.requirement_id) return;
    setBusy(true);
    try {
      const run = await startRun([task.requirement_id]);
      toast.success(`Run started for ${task.requirement_id}`);
      await refreshAll();
      router.push(`/requirements/${task.requirement_id}/simulation?run=${run.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const meta =
    task.kind === "running"
      ? STAGE_LABEL[task.stage ?? ""] ?? humanize(task.stage)
      : task.kind === "review_evidence"
        ? `${task.count ?? ""} source(s) pending`
        : [
            task.ai_recommendation && `AI: ${humanize(task.ai_recommendation)}`,
            task.score != null &&
              `score ${fmtScore(task.score)} (${fmtRange(task.score_low, task.score_high)})`,
            task.failed_gates?.length ? `${task.failed_gates.length} gate failed` : null,
          ]
            .filter(Boolean)
            .join(" · ");

  return (
    <div className="grid grid-cols-[150px_minmax(0,1fr)_220px_96px] items-center gap-4 border-b border-border/60 px-2 py-3 hover:bg-muted/40">
      <span className="truncate font-mono text-xs text-muted-foreground">
        {task.requirement_id ?? task.run_id?.slice(0, 8) ?? ""}
      </span>
      <span className="truncate font-medium">
        {task.title ?? task.label}
        {task.kind === "running" && task.requirement_ids && task.requirement_ids.length > 1 && (
          <span className="font-normal text-muted-foreground"> · {task.requirement_ids.length} requirements</span>
        )}
      </span>
      <span className="truncate text-[13px] text-muted-foreground">{meta}</span>
      <span className="justify-self-end">
        {task.kind === "decide" && task.requirement_id && (
          <Button size="sm" variant="outline" asChild>
            <Link href={`/requirements/${task.requirement_id}`}>Decide</Link>
          </Button>
        )}
        {task.kind === "simulate" && (
          <Button size="sm" variant="outline" onClick={simulate} disabled={busy}>
            {busy ? "Starting…" : "Simulate"}
          </Button>
        )}
        {task.kind === "review_evidence" && (
          <Button size="sm" variant="outline" asChild>
            <Link href="/sources?tab=list">Review</Link>
          </Button>
        )}
        {task.kind === "running" &&
          (task.run_id ? (
            <Button size="sm" variant="outline" asChild>
              <Link href={`/experts?run=${task.run_id}`}>Watch</Link>
            </Button>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="size-1.5 animate-pulse rounded-full bg-blue-600" aria-hidden />
              running
            </span>
          ))}
      </span>
    </div>
  );
}
