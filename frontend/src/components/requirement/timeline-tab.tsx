"use client";

import { ErrorState, LoadingRows } from "@/components/states";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useRequirementAudit, useVersions } from "@/lib/api/hooks";
import type { AuditEvent } from "@/lib/api/types";
import { actorLabel, fmtDateTime, humanize } from "@/lib/format";
import { cn } from "cn";

import { useRequirementContext } from "./context";

export function TimelineTab() {
  const { id } = useRequirementContext();
  const audit = useRequirementAudit(id);
  const versions = useVersions(id);

  if (audit.error) return <ErrorState error={audit.error} />;
  if (!audit.data) return <LoadingRows />;

  const events = [...audit.data].sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      {versions.data && versions.data.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span className="mr-1">Versions</span>
          {versions.data.map((v) => (
            <Tooltip key={v.id}>
              <TooltipTrigger asChild>
                <span className="rounded-md border px-1.5 py-0.5 tabular-nums">v{v.version}</span>
              </TooltipTrigger>
              <TooltipContent>
                {fmtDateTime(v.created_at)} · {actorLabel(v.actor_id)}
                {v.change_reason && ` · ${v.change_reason}`}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      )}

      <ol className="flex flex-col">
        {events.map((event, index) => (
          <TimelineItem key={event.id} event={event} first={index === 0} last={index === events.length - 1} />
        ))}
      </ol>
    </div>
  );
}

function TimelineItem({ event, first, last }: { event: AuditEvent; first: boolean; last: boolean }) {
  const human = event.actor_id.startsWith("pm:") || event.actor_type === "human" || event.actor_type === "pm";
  const ai = !human && (event.category === "ai" || event.actor_type === "agent" || event.actor_type === "ai");
  return (
    <li className="grid grid-cols-[110px_20px_minmax(0,1fr)] gap-4">
      <span className="py-3 font-mono text-xs text-muted-foreground">{fmtDateTime(event.occurred_at)}</span>
      <span className="relative flex justify-center pt-[18px]">
        <span
          className={cn("absolute left-1/2 w-px -translate-x-1/2 bg-border", first ? "top-[22px]" : "top-0", last ? "h-[22px]" : "bottom-0")}
          aria-hidden
        />
        <span
          className={cn(
            "relative",
            human ? "size-2 rounded-[2px] bg-foreground" : ai ? "size-1.5 rounded-full bg-blue-600" : "size-1.5 rounded-full bg-muted-foreground/50",
          )}
          aria-hidden
        />
      </span>
      <span className="flex flex-col gap-0.5 py-3 text-sm">
        <span className="font-medium">{describe(event)}</span>
        <span className="text-[13px] text-muted-foreground">
          {actorLabel(event.actor_id)} · {humanize(event.category)}
          {event.rationale && ` · “${event.rationale}”`}
        </span>
      </span>
    </li>
  );
}

function describe(event: AuditEvent): string {
  const after = event.after ?? {};
  const before = event.before ?? {};
  const action = humanize(event.action.replace(/\./g, " "));
  if (typeof after.status === "string" && before.status && after.status !== before.status) {
    return `${action}: ${humanize(String(before.status))} → ${humanize(after.status)}`;
  }
  if (typeof after.action === "string") return `${action}: ${humanize(after.action)}`;
  if (typeof after.value === "string" && typeof after.gate === "string") return `${action}: ${humanize(after.gate)} → ${after.value}`;
  return action;
}
