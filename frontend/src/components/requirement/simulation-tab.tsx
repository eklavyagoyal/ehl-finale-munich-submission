"use client";

import { useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useLlmCalls, useRun } from "@/lib/api/hooks";
import type { Decision, LlmCall, RequirementDetail } from "@/lib/api/types";
import { agentLabel, fmtDateTime, humanize, STAGE_LABEL, stanceTone } from "@/lib/format";
import { cn } from "cn";

import { useRequirementContext } from "./context";
import { FlowView } from "./flow-view";
import { CallDetail } from "./call-records";
import { type Lane, LaneDetail } from "./lane-detail";

const ACTIVE = new Set(["queued", "running"]);
const REGION_ORDER: Record<string, number> = { US: 0, EU: 1, CN: 2 };
const AGENT_ORDER = ["agent:research", "agent:verifier", "agent:synthesizer", "agent:challenger"];

const PURPOSE_STAGE: Record<string, string> = {
  persona_reaction: "market_and_company_twin",
  ssr_responses: "market_and_company_twin",
  department_review: "market_and_company_twin",
  web_research: "research",
  research_verification: "research",
  synthesis: "synthesis_and_vote",
  vote: "synthesis_and_vote",
  challenge: "synthesis_and_vote",
};

const STANCE_WORD: Record<string, string> = {
  positive: "For",
  support: "For",
  negative: "Against",
  oppose: "Against",
  neutral: "Unsure",
  mixed: "Unsure",
};

export function SimulationTab() {
  const { id, detail, runId } = useRequirementContext();
  const run = useRun(runId);
  const live = !!run.data && ACTIVE.has(run.data.run.status);
  const calls = useLlmCalls(runId, id, live);

  const model = useMemo(() => buildLanes(detail, calls.data ?? [], runId), [detail, calls.data, runId]);
  const linked = useMemo(() => new Set((detail?.evidence ?? []).map((e) => e.record_id)), [detail]);
  const [view, setView] = useState<"lanes" | "flow">("lanes");

  if (!runId) {
    return (
      <EmptyState title="No simulation yet">
        Start “Run Parallax” above. Personas from the US, Europe and China and the company departments then review this requirement in
        parallel, and every model call shows up here as a dot.
      </EmptyState>
    );
  }
  if (calls.error) return <ErrorState error={calls.error} />;
  if (!calls.data) return <LoadingRows />;

  const r = run.data?.run;
  const tokens = r ? r.input_tokens + r.output_tokens : 0;

  return (
    <div className="flex max-w-6xl flex-col gap-5">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
        <span className="font-mono">Run {runId.slice(0, 8)}</span>
        {r && <span>{humanize(r.status)}</span>}
        <span className="tabular-nums">{calls.data.length} calls for this requirement</span>
        {r && <span className="tabular-nums">{tokens.toLocaleString("en-US")} tokens in the run</span>}
        {r?.challenge_question && <span>Challenge: “{r.challenge_question}”</span>}
        <span className="ml-auto flex items-center gap-4">
          <span className="flex rounded-lg bg-muted p-0.5" role="radiogroup" aria-label="View">
            {(["lanes", "flow"] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={view === v}
                onClick={() => setView(v)}
                className={cn(
                  "h-6 rounded-md px-2.5 text-xs",
                  view === v ? "bg-background font-medium text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {v === "lanes" ? "Lanes" : "Flow"}
              </button>
            ))}
          </span>
          <Legend kind="call" label="LLM call" />
          <Legend kind="verify" label="Verifier" />
          <Legend kind="pm" label="PM decision" />
        </span>
      </div>

      {view === "flow" && (
        <FlowView
          lanes={model.groups.flatMap((g) => g.lanes)}
          calls={calls.data}
          decisions={detail?.decisions ?? []}
          title={detail?.requirement.title ?? ""}
          live={live}
          requirementId={id}
          linked={linked}
        />
      )}

      {view === "lanes" && (
        <LanesView model={model} requirementId={id} linked={linked} decisions={detail?.decisions ?? []} live={live} empty={calls.data.length === 0} />
      )}
    </div>
  );
}

// The table-like lane view: one row per agent, every model call a dot. Also used run-wide on the
// Expert pipeline page, where requirementId is empty and record links go to the records view.
export function LanesView({
  model,
  requirementId,
  linked,
  decisions,
  live,
  empty,
}: {
  model: ReturnType<typeof buildLanes>;
  requirementId: string;
  linked: Set<string>;
  decisions: Decision[];
  live: boolean;
  empty: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[860px]">
        <div className="grid grid-cols-[230px_minmax(0,1fr)] gap-4">
          <span />
          <div className="relative h-5 text-[11px] text-muted-foreground">
            {model.stages.map((s) => (
              <span key={s.stage} className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: `${s.center}%` }}>
                {STAGE_LABEL[s.stage] ?? humanize(s.stage)}
              </span>
            ))}
          </div>
        </div>

        {model.groups.map((group) => (
          <section key={group.title} className="mt-3">
            <h3 className="px-2 pb-1 text-xs font-medium text-foreground/70">
              {group.title} <span className="font-normal text-muted-foreground/70">{group.lanes.length}</span>
            </h3>
            {group.lanes.map((lane) => (
              <LaneRow key={lane.id} lane={lane} position={model.position} requirementId={requirementId} linked={linked} />
            ))}
          </section>
        ))}

        {decisions.length > 0 && (
          <section className="mt-3">
            <h3 className="px-2 pb-1 text-xs font-medium text-foreground/70">Human</h3>
            <div className="grid h-7 grid-cols-[230px_minmax(0,1fr)] items-center gap-4 rounded-md px-2">
              <span className="text-xs">Product manager</span>
              <div className="relative h-full">
                {decisions.map((d, i) => (
                  <Tooltip key={d.id}>
                    <TooltipTrigger asChild>
                      <span
                        className="absolute top-1/2 size-2.5 -translate-y-1/2 rounded-[2px] bg-foreground"
                        style={{ left: `calc(${100 - i * 2}% - 10px)` }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      {humanize(d.action)} · {fmtDateTime(d.created_at)} · “{d.rationale}”
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          </section>
        )}

        {empty && (
          <p className="px-2 py-6 text-sm text-muted-foreground">
            {live ? "Waiting for the first model calls…" : "This run made no model calls here."}
          </p>
        )}
      </div>
    </div>
  );
}

function LaneRow({
  lane,
  position,
  requirementId,
  linked,
}: {
  lane: Lane;
  position: Map<number, number>;
  requirementId: string;
  linked: Set<string>;
}) {
  const xs = lane.calls.map((c) => position.get(c.id) ?? 0);
  const first = Math.min(...xs);
  const last = Math.max(...xs);

  return (
    <div className="group grid h-7 grid-cols-[230px_minmax(0,1fr)] items-center gap-4 rounded-md px-2 hover:bg-muted/50">
      <HoverCard openDelay={120} closeDelay={60}>
        <HoverCardTrigger asChild>
          <button type="button" className="flex min-w-0 items-center gap-2 text-left text-xs">
            {lane.region && <span className="w-5 font-mono text-[11px] text-muted-foreground/70">{lane.region}</span>}
            <span className="truncate">{lane.name}</span>
            {lane.vote && (
              <ToneBadge tone={lane.voteTone ?? "muted"} className="ml-auto">
                {lane.vote}
              </ToneBadge>
            )}
          </button>
        </HoverCardTrigger>
        <HoverCardContent align="start" side="right" className="w-80 text-xs">
          <LaneDetail lane={lane} />
        </HoverCardContent>
      </HoverCard>

      <div className="relative h-full">
        {lane.calls.length > 1 && (
          <span
            className="absolute top-1/2 h-px -translate-y-1/2 bg-border"
            style={{ left: `${first}%`, width: `${last - first}%` }}
            aria-hidden
          />
        )}
        {lane.calls.map((call) => {
          const verify = call.purpose === "research_verification" || call.agent_id === "agent:verifier";
          return (
            <HoverCard key={call.id} openDelay={80} closeDelay={120}>
              <HoverCardTrigger asChild>
                <button
                  type="button"
                  className={cn(
                    "absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full",
                    verify ? "size-2.5 border-[1.5px] border-blue-600 bg-background" : "size-1.5 bg-blue-600",
                    call.status !== "ok" && "bg-red-500",
                  )}
                  style={{ left: `${position.get(call.id) ?? 0}%` }}
                  aria-label={`${humanize(call.purpose)} call, saw ${call.input_record_ids.length} records`}
                />
              </HoverCardTrigger>
              <HoverCardContent side="top" className="w-72 text-xs">
                <CallDetail call={call} requirementId={requirementId} linked={linked} />
              </HoverCardContent>
            </HoverCard>
          );
        })}
      </div>
    </div>
  );
}

export function Legend({ kind, label }: { kind: "call" | "verify" | "pm"; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className={cn(
          kind === "call" && "size-1.5 rounded-full bg-blue-600",
          kind === "verify" && "size-2.5 rounded-full border-[1.5px] border-blue-600",
          kind === "pm" && "size-2 rounded-[2px] bg-foreground",
        )}
        aria-hidden
      />
      {label}
    </span>
  );
}

const STAGE_ORDER = ["market_and_company_twin", "research", "synthesis_and_vote", "other"];
const MIN_BAND = 0.18;

// Lanes are the real agent ids. Each run stage gets its own band on the x axis (at least 18 % wide),
// and inside a band dots follow call order (rank of created_at). Parallel calls stay readable even
// when a mock run finishes within a second, and short stages do not get squeezed against the edge.
function placeCalls(sorted: LlmCall[]) {
  const byStage = new Map<string, LlmCall[]>();
  for (const call of sorted) {
    const stage = PURPOSE_STAGE[call.purpose] ?? "other";
    byStage.set(stage, [...(byStage.get(stage) ?? []), call]);
  }
  const present = STAGE_ORDER.filter((s) => byStage.has(s));
  const raw = present.map((s) => Math.max(byStage.get(s)!.length / Math.max(sorted.length, 1), MIN_BAND));
  const total = raw.reduce((a, b) => a + b, 0) || 1;

  const position = new Map<number, number>();
  const stages: { stage: string; center: number }[] = [];
  let start = 2;
  present.forEach((stage, i) => {
    const width = (raw[i] / total) * 96;
    const items = byStage.get(stage)!;
    const pad = Math.min(3, width / 6);
    items.forEach((call, j) => {
      const x = items.length > 1 ? start + pad + (j / (items.length - 1)) * (width - 2 * pad) : start + width / 2;
      position.set(call.id, x);
    });
    if (stage !== "other") stages.push({ stage, center: start + width / 2 });
    start += width;
  });
  return { position, stages };
}

export function buildLanes(
  detail: Pick<RequirementDetail, "persona_responses" | "department_memos" | "votes"> | undefined,
  calls: LlmCall[],
  runId: string | null,
) {
  const sorted = [...calls].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id);
  const { position, stages } = placeCalls(sorted);

  const sameRun = <T extends { run_id?: string }>(items: T[] | undefined) =>
    (items ?? []).filter((x) => !runId || !x.run_id || x.run_id === runId);
  const personas = new Map(sameRun(detail?.persona_responses).map((p) => [p.agent_id, p]));
  const memos = new Map(sameRun(detail?.department_memos).map((m) => [m.agent_id, m]));
  const judges = new Map(sameRun(detail?.votes).map((v) => [v.agent_id, v]));

  const lanes = new Map<string, Lane>();
  const lane = (agentId: string) => {
    if (!lanes.has(agentId)) {
      const { group, name } = agentLabel(agentId);
      const kind = agentId.split(":")[0];
      lanes.set(agentId, {
        id: agentId,
        group: kind === "persona" ? "Public panel" : kind === "dept" ? "Company departments" : "Agents",
        region: group,
        name,
        calls: [],
      });
    }
    return lanes.get(agentId)!;
  };
  for (const id of personas.keys()) lane(id);
  for (const id of memos.keys()) lane(id);
  for (const call of sorted) lane(call.agent_id).calls.push(call);

  for (const l of lanes.values()) {
    const persona = personas.get(l.id);
    const memo = memos.get(l.id);
    const judge = judges.get(l.id);
    l.persona = persona;
    l.memo = memo;
    l.judge = judge;
    const stance = persona?.stance ?? memo?.stance ?? judge?.vote;
    if (stance) {
      l.vote = STANCE_WORD[stance] ?? humanize(stance);
      l.voteTone = stanceTone(stance);
    }
  }

  const order = (l: Lane) =>
    l.id.startsWith("agent:")
      ? AGENT_ORDER.indexOf(l.id) >= 0
        ? AGENT_ORDER.indexOf(l.id)
        : 10
      : l.id.startsWith("judge:")
        ? 20
        : (REGION_ORDER[l.region] ?? 5) * 100;
  const all = [...lanes.values()].sort((a, b) => order(a) - order(b) || a.name.localeCompare(b.name));
  const groups = ["Public panel", "Company departments", "Agents"]
    .map((title) => ({ title, lanes: all.filter((l) => l.group === title) }))
    .filter((g) => g.lanes.length > 0);

  return { groups, position, stages };
}
