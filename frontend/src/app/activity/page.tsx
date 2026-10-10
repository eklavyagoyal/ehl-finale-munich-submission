"use client";

import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { useAudit } from "@/lib/api/hooks";
import type { AuditEvent } from "@/lib/api/types";
import { actorLabel, fmtDateTime, humanize } from "@/lib/format";
import { cn } from "cn";

const CATEGORIES = ["change", "decision", "ai", "evidence", "system"];

export default function ActivityPage() {
  const [category, setCategory] = useState<string | undefined>();
  const { data, error, isLoading } = useAudit(category);

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "Activity" }]}>
        <span className="flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
          Live
        </span>
      </PageHeader>

      <div className="-ml-2.5 mt-2 flex flex-wrap gap-1">
        {[undefined, ...CATEGORIES].map((c) => (
          <button
            key={c ?? "all"}
            type="button"
            onClick={() => setCategory(c)}
            className={cn(
              "h-8 rounded-lg px-2.5 text-[13px]",
              category === c ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {c ? (c === "ai" ? "AI" : humanize(c)) : "All"}
          </button>
        ))}
        {data && <span className="ml-auto self-center text-xs text-muted-foreground tabular-nums">{data.total} events</span>}
      </div>

      <div className="mt-3 max-w-5xl overflow-x-auto">
        <div className="min-w-[760px] border-t">
          {error && <ErrorState error={error} />}
          {isLoading && <LoadingRows />}
          {data && data.items.length === 0 && <EmptyState title="No activity yet" />}
          {data?.items.map((event) => <ActivityRow key={event.id} event={event} />)}
        </div>
      </div>
    </>
  );
}

function ActivityRow({ event }: { event: AuditEvent }) {
  const human = event.actor_id.startsWith("pm:");
  const ai = !human && event.category === "ai";
  return (
    <div className="grid grid-cols-[110px_16px_210px_minmax(0,1fr)_130px] items-center gap-3 border-b border-border/60 px-2 py-2.5 text-sm hover:bg-muted/40">
      <span className="font-mono text-xs text-muted-foreground">{fmtDateTime(event.occurred_at)}</span>
      <span className="flex justify-center" aria-hidden>
        <span
          className={cn(
            human ? "size-2 rounded-[2px] bg-foreground" : ai ? "size-1.5 rounded-full bg-blue-600" : "size-1.5 rounded-full bg-muted-foreground/40",
          )}
        />
      </span>
      <span className="truncate font-medium">{actorLabel(event.actor_id)}</span>
      <span className="truncate text-muted-foreground">
        {humanize(event.action.replace(/\./g, " "))}
        {event.rationale && ` · “${event.rationale}”`}
      </span>
      <span className="truncate text-right font-mono text-xs text-muted-foreground">
        {event.requirement_id ? (
          <Link href={`/requirements/${event.requirement_id}/timeline`} className="hover:text-foreground">
            {event.requirement_id}
          </Link>
        ) : event.run_id ? (
          `run ${event.run_id.slice(0, 8)}`
        ) : (
          humanize(event.entity_type)
        )}
      </span>
    </div>
  );
}
