"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { type Lane, LaneDetail } from "@/components/requirement/lane-detail";
import { buildLanes, LanesView, Legend, ownersById } from "@/components/requirement/simulation-tab";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { refreshAll, startRun, useConversation, useRequirements, useRun, useRunCalls, useRunResults, useRuns } from "@/lib/api/hooks";
import type { LlmCall, Requirement, ResearchItem, Run, RunResults } from "@/lib/api/types";
import { agentLabel, fmtCount, fmtDateTime, humanize, runStatusLabel, STAGE_LABEL, STAGES, stanceTone, statusTone } from "@/lib/format";
import { cn } from "cn";
import { V } from "@/lib/routes";

const ACTIVE = new Set(["queued", "running"]);
const NO_LINKS = new Set<string>();
const marketOrder = (m: string) => (["US", "EU", "CN"].indexOf(m) + 99) % 99;

export default function ExpertsPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <ExpertsView />
    </Suspense>
  );
}

function ExpertsView() {
  const params = useSearchParams();
  const runs = useRuns(12);
  // Only expert-pipeline runs; condense and validation runs share the endpoint.
  const pipelineRuns = (runs.data ?? []).filter((r) => r.kind === "simulation" || r.kind === "followup");
  const runId = params.get("run") ?? pipelineRuns.find((r) => ACTIVE.has(r.status))?.id ?? pipelineRuns[0]?.id ?? null;

  return (
    <>
      <PageHeader crumbs={[{ label: "Expert pipeline" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">What do owners and departments think?</p>
      <div className="mt-6 flex max-w-6xl flex-col gap-10">
        <StartRun />
        {runs.error && <ErrorState error={runs.error} />}
        {runs.isLoading && <LoadingRows />}
        {runs.data && pipelineRuns.length === 0 && (
          <EmptyState title="No runs yet">Pick requirements above and start the expert pipeline.</EmptyState>
        )}
        {pipelineRuns.length > 0 && <RunPicker runs={pipelineRuns} selected={runId} />}
        {runId && <RunView key={runId} runId={runId} />}
      </div>
    </>
  );
}

// Pick requirements and start one run over all of them.
function StartRun() {
  const router = useRouter();
  const { data: requirements } = useRequirements();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const waiting = (requirements ?? []).filter((r) => r.status === "proposed" || r.status === "challenged");

  async function start() {
    setBusy(true);
    try {
      const run = await startRun([...selected]);
      toast.success(`Run started for ${selected.size} requirement${selected.size === 1 ? "" : "s"}`);
      setOpen(false);
      setSelected(new Set());
      await refreshAll();
      router.replace(`${V}/experts?run=${run.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col">
      <h2 className="flex items-baseline gap-3 border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">
        Requirements
        {waiting.length > 0 && (
          <button type="button" className="text-xs hover:text-foreground" onClick={() => setSelected(new Set(waiting.map((r) => r.id)))}>
            Select the {waiting.length} not yet run
          </button>
        )}
        <span className="ml-auto">
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" disabled={selected.size === 0}>
                Run expert pipeline{selected.size > 0 ? ` (${selected.size})` : ""}
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Run the expert pipeline</DialogTitle>
                <DialogDescription>
                  Owner personas in the US, Europe and China, the company departments, research, scoring, a challenger and a judge review{" "}
                  {selected.size} requirement{selected.size === 1 ? "" : "s"}. This uses the model budget and takes a few minutes.
                </DialogDescription>
              </DialogHeader>
              <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto text-sm">
                {(requirements ?? [])
                  .filter((r) => selected.has(r.id))
                  .map((r) => (
                    <li key={r.id} className="flex gap-2">
                      <span className="font-mono text-xs text-muted-foreground">{r.id}</span>
                      <span className="truncate">{r.title}</span>
                    </li>
                  ))}
              </ul>
              <DialogFooter>
                <Button onClick={start} disabled={busy}>
                  {busy ? "Starting…" : "Start run"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </span>
      </h2>
      {(requirements ?? []).map((r) => (
        <label key={r.id} className="flex cursor-pointer items-center gap-3 border-b border-border/60 px-2 py-2 text-sm hover:bg-muted/40">
          <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} className="size-3.5 accent-foreground" />
          <span className="w-28 shrink-0 font-mono text-xs text-muted-foreground">{r.id}</span>
          <span className="min-w-0 flex-1 truncate">{r.title}</span>
          {r.market && <span className="font-mono text-xs text-muted-foreground">{r.market}</span>}
          <ToneBadge tone={statusTone(r.status)}>{humanize(r.status)}</ToneBadge>
        </label>
      ))}
    </section>
  );
}

function RunPicker({ runs, selected }: { runs: Run[]; selected: string | null }) {
  const router = useRouter();
  return (
    <nav aria-label="Runs" className="-ml-2 flex gap-1 overflow-x-auto pb-1">
      {runs.map((r) => (
        <button
          key={r.id}
          type="button"
          onClick={() => router.replace(`${V}/experts?run=${r.id}`)}
          aria-current={r.id === selected ? "true" : undefined}
          className={cn(
            "flex shrink-0 items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs",
            r.id === selected ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <span
            className={cn(
              "size-1.5 rounded-full",
              ACTIVE.has(r.status) ? "animate-pulse bg-blue-600" : r.status === "completed" ? "bg-foreground/60" : "bg-red-500",
            )}
            aria-hidden
          />
          <span className="font-mono">{r.id.slice(0, 8)}</span>
          <span>
            {r.requirement_ids.length} req · {fmtDateTime(r.created_at)}
            {r.status === "queued" && " · waiting"}
          </span>
        </button>
      ))}
    </nav>
  );
}

function RunView({ runId }: { runId: string }) {
  const run = useRun(runId);
  const status = run.data?.run.status;
  const live = !!status && ACTIVE.has(status);
  const calls = useRunCalls(runId, live);
  // Results are read once the run has settled; the key includes the status so they reload when it finishes.
  const results = useRunResults(status && !live ? runId : null);
  const { data: requirements } = useRequirements();
  const titles = new Map((requirements ?? []).map((r) => [r.id, r]));
  const conversation = useConversation(runId, status);
  const owners = useMemo(() => ownersById(conversation.data?.owners_by_market), [conversation.data]);
  const model = useMemo(() => buildLanes(undefined, calls.data ?? [], runId, owners), [calls.data, runId, owners]);

  if (run.error) return <ErrorState error={run.error} />;
  if (!run.data) return <LoadingRows />;
  const r = run.data.run;
  const done = new Set(r.progress?.completed_stages ?? []);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground" role="status">
        <span className={cn("flex items-center gap-1.5", live && "text-foreground")}>
          {live && <span className="size-1.5 animate-pulse rounded-full bg-blue-600" aria-hidden />}
          {runStatusLabel(r.status)}
        </span>
        {STAGES.map((stage) => (
          <span key={stage} className={cn("flex items-center gap-1.5", stage === r.progress?.stage && "text-foreground")}>
            <span
              className={cn("size-1.5 rounded-full", done.has(stage) ? "bg-foreground" : stage === r.progress?.stage ? "bg-blue-600" : "bg-border")}
              aria-hidden
            />
            {STAGE_LABEL[stage]}
          </span>
        ))}
        <span className="tabular-nums">{fmtCount(r.llm_calls)} LLM calls</span>
        <span className="tabular-nums">{fmtCount(r.input_tokens + r.output_tokens)} tokens</span>
        {r.challenge_question && <span>Challenge: “{r.challenge_question}”</span>}
        <span className="ml-auto flex items-center gap-4">
          <Legend kind="call" label="LLM call" />
          <Legend kind="verify" label="Verifier" />
        </span>
      </div>
      {r.error && <p className="text-sm text-red-700 dark:text-red-300">{r.error}</p>}

      {calls.error && <ErrorState error={calls.error} />}
      {calls.data && <LanesView model={model} requirementId="" linked={NO_LINKS} decisions={[]} live={live} empty={calls.data.length === 0} />}

      {live && <p className="text-[13px] text-muted-foreground">Results per requirement appear when the run has finished.</p>}
      {results.error && <ErrorState error={results.error} />}
      {results.data && (
        <div className="flex flex-col">
          {r.requirement_ids.map((id) => (
            <RequirementResult key={id} id={id} runId={runId} requirement={titles.get(id)} outputs={results.data!.requirements[id]} calls={calls.data ?? []} />
          ))}
        </div>
      )}
    </div>
  );
}

type Outputs = RunResults["requirements"][string];

function laneFor(agentId: string, calls: LlmCall[], extra: Partial<Lane>): Lane {
  const { group, name } = agentLabel(agentId);
  return { id: agentId, group: "", region: group, name, calls: calls.filter((c) => c.agent_id === agentId), ...extra };
}

// Every agent output of one requirement in this run: owners by market, departments, research, judges, challenger.
function RequirementResult({
  id,
  runId,
  requirement,
  outputs,
  calls,
}: {
  id: string;
  runId: string;
  requirement?: Requirement;
  outputs?: Outputs;
  calls: LlmCall[];
}) {
  const recommendation = outputs?.recommendation[0];
  const byMarket = new Map<string, Outputs["persona_responses"]>();
  for (const p of outputs?.persona_responses ?? []) {
    const market = agentLabel(p.agent_id).group || "Other";
    byMarket.set(market, [...(byMarket.get(market) ?? []), p]);
  }

  return (
    <section className="border-t py-5">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Link href={`${V}/decision/${encodeURIComponent(id)}/simulation?run=${runId}`} className="font-mono text-xs text-muted-foreground hover:underline">
          {id}
        </Link>
        <span className="font-medium">{requirement?.title ?? ""}</span>
        {recommendation && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
            AI recommends <ToneBadge tone={stanceTone(recommendation.recommendation)}>{humanize(recommendation.recommendation)}</ToneBadge>
          </span>
        )}
      </div>
      {!outputs ? (
        <p className="mt-3 text-[13px] text-muted-foreground">No outputs recorded for this requirement.</p>
      ) : (
        <dl className="mt-4 grid grid-cols-[110px_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm">
          <dt className="text-[13px] text-muted-foreground">Owners</dt>
          <dd className="flex flex-col gap-1.5">
            {[...byMarket.entries()].sort(([a], [b]) => marketOrder(a) - marketOrder(b)).map(([market, responses]) => (
              <span key={market} className="flex flex-wrap items-center gap-1">
                <span className="w-7 font-mono text-[11px] text-muted-foreground">{market}</span>
                {responses.map((p) => (
                  <AgentChip key={p.agent_id} lane={laneFor(p.agent_id, calls, { persona: p })} stance={p.stance} />
                ))}
              </span>
            ))}
            {byMarket.size === 0 && <span className="text-muted-foreground">–</span>}
          </dd>

          <dt className="text-[13px] text-muted-foreground">Departments</dt>
          <dd className="flex flex-wrap gap-1">
            {outputs.department_memos.map((m) => (
              <AgentChip key={m.agent_id} lane={laneFor(m.agent_id, calls, { memo: m })} stance={m.stance} />
            ))}
            {outputs.department_memos.length === 0 && <span className="text-muted-foreground">–</span>}
          </dd>

          <dt className="text-[13px] text-muted-foreground">Research</dt>
          <dd className="flex flex-wrap gap-1">
            {outputs.research.map((q, i) => (
              <ResearchChip key={i} item={q} />
            ))}
            {outputs.research.length === 0 && <span className="text-muted-foreground">–</span>}
          </dd>

          <dt className="text-[13px] text-muted-foreground">Judge</dt>
          <dd className="flex flex-wrap gap-1">
            {outputs.votes.map((v) => (
              <AgentChip key={v.agent_id} lane={laneFor(v.agent_id, calls, { judge: v })} stance={v.vote} label={`${agentLabel(v.agent_id).name} · ${humanize(v.vote)}`} />
            ))}
            {outputs.votes.length === 0 && <span className="text-muted-foreground">–</span>}
          </dd>

          {recommendation?.challenge?.counter_position && (
            <>
              <dt className="text-[13px] text-muted-foreground">Challenger</dt>
              <dd className="max-w-3xl text-[13px]">{recommendation.challenge.counter_position}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  );
}

function AgentChip({ lane, stance, label }: { lane: Lane; stance: string; label?: string }) {
  return (
    <HoverCard openDelay={100} closeDelay={60}>
      <HoverCardTrigger asChild>
        <button type="button">
          <ToneBadge tone={stanceTone(stance)}>{label ?? lane.name}</ToneBadge>
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <LaneDetail lane={lane} />
      </HoverCardContent>
    </HoverCard>
  );
}

function ResearchChip({ item }: { item: ResearchItem }) {
  return (
    <HoverCard openDelay={100} closeDelay={60}>
      <HoverCardTrigger asChild>
        <button type="button">
          <ToneBadge tone={item.verdict === "supported" ? "green" : item.verdict === "contradicted" ? "red" : "muted"}>
            {humanize(item.verdict ?? item.status ?? "open")}
          </ToneBadge>
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <p className="font-medium">{item.question}</p>
        <p className="mt-0.5 text-muted-foreground">Asked by {agentLabel(item.requested_by).name}</p>
        {(item.findings ?? []).map((f, i) => (
          <div key={i} className="mt-2 flex flex-col gap-0.5">
            {f.answer_summary && <p className="text-foreground/80">{f.answer_summary}</p>}
            {f.source_url && (
              <a href={f.source_url} target="_blank" rel="noreferrer noopener" className="truncate text-muted-foreground hover:underline">
                {f.source_title ?? f.source_url}
              </a>
            )}
          </div>
        ))}
      </HoverCardContent>
    </HoverCard>
  );
}
