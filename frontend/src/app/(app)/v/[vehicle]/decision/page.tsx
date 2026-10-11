"use client";

import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ScoreBar } from "@/components/score-bar";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { type RequirementQuery, useMeta, useRequirements } from "@/lib/api/hooks";
import type { Requirement, RequirementProgress } from "@/lib/api/types";
import { fmtDateTime, fmtRange, fmtScore, humanize, statusTone } from "@/lib/format";
import { cn } from "cn";
import { V } from "@/lib/routes";

const SORTS: { value: NonNullable<RequirementQuery["sort"]>; label: string }[] = [
  { value: "priority", label: "Priority" },
  { value: "score", label: "Score" },
  { value: "updated", label: "Last updated" },
  { value: "created", label: "Created" },
];

export default function RequirementsPage() {
  const { data: meta } = useMeta();
  const [status, setStatus] = useState<string | undefined>();
  const [sort, setSort] = useState<NonNullable<RequirementQuery["sort"]>>("priority");
  const all = useRequirements({ sort });
  const { data, error, isLoading } = useRequirements({ sort, status });

  const counts = new Map<string, number>();
  for (const r of all.data ?? []) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const statuses = (meta?.enums.requirement_status ?? []).filter((s) => counts.has(s));

  return (
    <>
      <PageHeader crumbs={[{ label: "Decision" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">What goes into the successor?</p>

      <div className="-ml-2.5 mt-2 flex flex-wrap items-center gap-1">
        <FilterPill active={!status} onClick={() => setStatus(undefined)} label="All" count={all.data?.length} />
        {statuses.map((s) => (
          <FilterPill key={s} active={status === s} onClick={() => setStatus(s)} label={humanize(s)} count={counts.get(s)} />
        ))}
        <div className="ml-auto">
          <Select value={sort} onValueChange={(v) => setSort(v as typeof sort)}>
            <SelectTrigger size="sm" className="w-40" aria-label="Sort by">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORTS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="mt-3 overflow-x-auto">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-[150px_minmax(0,1fr)_56px_150px_96px_110px_110px] gap-4 px-2 py-2.5 text-xs text-muted-foreground">
            <span><span className="inline-block w-6">#</span>ID</span>
            <span>Requirement</span>
            <span>Market</span>
            <span>Score · range</span>
            <span>Progress</span>
            <span>AI suggests</span>
            <span>Your decision</span>
          </div>
          {error && <ErrorState error={error} />}
          {isLoading && <LoadingRows />}
          {data && data.length === 0 && (
            <EmptyState title="No requirements yet">
              Requirements exist once evidence is imported. Draft them from the signals in{" "}
              <Link href={`${V}/signals`} className="text-foreground underline-offset-4 hover:underline">
                Signals
              </Link>
              .
            </EmptyState>
          )}
          {data?.map((r) => (
            <Link
              key={r.id}
              href={`${V}/decision/${r.id}`}
              className="grid grid-cols-[150px_minmax(0,1fr)_56px_150px_96px_110px_110px] items-center gap-4 border-t border-border/60 px-2 py-3 hover:bg-muted/40"
            >
              <span className="font-mono text-xs text-muted-foreground">
                <span className="inline-block w-6 text-foreground/50">{r.priority_rank ? `#${r.priority_rank}` : ""}</span>
                {r.id}
              </span>
              <span className="truncate font-medium">{r.title}</span>
              <span className="text-[13px] text-muted-foreground">{r.market ?? "All"}</span>
              <span className="flex items-center gap-2">
                <span className="w-7 tabular-nums">{fmtScore(r.score)}</span>
                <ScoreBar low={r.score_low} high={r.score_high} />
                <span className="text-xs text-muted-foreground tabular-nums">{fmtRange(r.score_low, r.score_high)}</span>
              </span>
              <Progress steps={progressOf(r)} />
              {/* Advice, not a decision: muted text only. */}
              <span className="truncate text-[13px] text-muted-foreground">{r.ai_recommendation ? humanize(r.ai_recommendation) : "–"}</span>
              <span>
                {DECIDED.has(r.status) ? (
                  <ToneBadge tone={statusTone(r.status)}>{humanize(r.status)}</ToneBadge>
                ) : (
                  <span className="text-[13px] text-muted-foreground">{r.status === "challenged" ? "Challenged" : "Open"}</span>
                )}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}

function FilterPill({ active, onClick, label, count }: { active: boolean; onClick: () => void; label: string; count?: number }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex h-8 items-center gap-2 rounded-lg px-2.5 text-[13px]",
        active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
      {count !== undefined && <span className="font-normal text-muted-foreground/70">{count}</span>}
    </button>
  );
}

const DECIDED = new Set(["approved", "rejected", "deferred"]);

// Older payloads have no progress[]; derive the same four steps from the requirement itself.
function progressOf(r: Requirement): RequirementProgress[] {
  return (
    r.progress ?? [
      { key: "drafted", label: "Drafted", done: true, at: r.created_at, value: r.created_by },
      { key: "councils", label: "Councils", done: !!r.last_run_id, at: null, value: null },
      { key: "recommendation", label: "AI suggests", done: !!r.ai_recommendation, at: null, value: r.ai_recommendation },
      { key: "decision", label: "Your decision", done: DECIDED.has(r.status), at: null, value: DECIDED.has(r.status) ? r.status : null },
    ]
  );
}

// Drafted · Councils · AI suggests · Your decision as four small steps; filled = done, details on hover.
function Progress({ steps }: { steps: RequirementProgress[] }) {
  return (
    <span className="flex items-center gap-1">
      {steps.map((step) => (
        <Tooltip key={step.key}>
          <TooltipTrigger asChild>
            <span
              className={cn(
                "h-1.5 w-4 rounded-full",
                step.done ? (step.key === "decision" ? "bg-foreground" : "bg-foreground/50") : "border border-muted-foreground/40",
              )}
              aria-label={`${step.label}: ${step.done ? "done" : "not yet"}`}
            />
          </TooltipTrigger>
          <TooltipContent>
            {step.label}
            {step.value ? ` · ${humanize(step.value)}` : ""}
            {step.done ? (step.at ? ` · ${fmtDateTime(step.at)}` : "") : " · not yet"}
          </TooltipContent>
        </Tooltip>
      ))}
    </span>
  );
}
