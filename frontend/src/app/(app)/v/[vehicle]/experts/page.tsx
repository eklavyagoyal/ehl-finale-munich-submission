"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { type Lane, LaneDetail } from "@/components/requirement/lane-detail";
import { FlowView } from "@/components/requirement/flow-view";
import { PipelineDiagram } from "@/components/pipeline-diagram";
import { buildLanes, LanesView, ownersById } from "@/components/requirement/simulation-tab";
import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { refreshAll, startRun, useConversation, useRequirements, useRun, useRunCalls, useRunResults, useRuns } from "@/lib/api/hooks";
import type { LlmCall, Requirement, ResearchItem, Run, RunResults } from "@/lib/api/types";
import { agentLabel, fmtCount, fmtDuration, humanize, runStatusLabel, stanceTone } from "@/lib/format";
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
  const router = useRouter();
  const params = useSearchParams();
  const runs = useRuns(12);
  const { data: requirements } = useRequirements();
  const titles = new Map((requirements ?? []).map((r) => [r.id, r]));
  // Only expert-pipeline runs; condense and validation runs share the endpoint.
  const pipelineRuns = (runs.data ?? []).filter((r) => r.kind === "simulation" || r.kind === "followup");
  const runId = params.get("run") ?? pipelineRuns.find((r) => ACTIVE.has(r.status))?.id ?? pipelineRuns[0]?.id ?? null;

  return (
    <>
      <PageHeader crumbs={[{ label: "Expert pipeline" }]}>
        {pipelineRuns.length > 0 && (
          <Select value={runId ?? undefined} onValueChange={(id) => router.replace(`${V}/experts?run=${id}`)}>
            <SelectTrigger size="sm" className="w-72" aria-label="Run">
              <SelectValue placeholder="Pick a run" />
            </SelectTrigger>
            <SelectContent>
              {pipelineRuns.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  {runLabel(r, titles)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <SendDialog />
      </PageHeader>
      <p className="mt-1 text-[13px] text-muted-foreground">What do owners and departments think?</p>
      <div className="mt-6 flex max-w-6xl flex-col gap-8">
        {runs.error && <ErrorState error={runs.error} />}
        {runId ? <RunView key={runId} runId={runId} titles={titles} /> : <PipelineDiagram />}
      </div>
    </>
  );
}

const durationOf = (r: Run) =>
  r.started_at ? ((r.finished_at ? Date.parse(r.finished_at) : Date.now()) - Date.parse(r.started_at)) / 1000 : null;

// A run in the history: which signals, how many agent calls, how long. No clock times.
function runLabel(r: Run, titles: Map<string, Requirement>) {
  const names = r.requirement_ids.map((id) => titles.get(id)?.signal_label ?? titles.get(id)?.title.split(":")[0] ?? id);
  const what = names.slice(0, 2).join(", ") + (names.length > 2 ? ` +${names.length - 2}` : "");
  const state = r.status === "completed" ? fmtDuration(durationOf(r)) : runStatusLabel(r.status).toLowerCase();
  return `${what} · ${fmtCount(r.llm_calls)} calls · ${state}`;
}

// "Send through pipeline": pick requirements (those not run yet are preselected) and start one run.
function SendDialog() {
  const router = useRouter();
  const { data: requirements } = useRequirements();
  const waiting = (requirements ?? []).filter((r) => r.status === "proposed" || r.status === "challenged");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  async function start() {
    setBusy(true);
    try {
      const run = await startRun([...selected]);
      toast.success(`Sent ${selected.size} requirement${selected.size === 1 ? "" : "s"} through the pipeline`);
      setOpen(false);
      await refreshAll();
      router.replace(`${V}/experts?run=${run.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setSelected(new Set(waiting.map((r) => r.id)));
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">Send through pipeline</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Send through the expert pipeline</DialogTitle>
          <DialogDescription>
            Owners, departments, research, a challenger and a judge review the selected requirements. This uses the model budget and takes a few
            minutes; if another run is going, this one waits.
          </DialogDescription>
        </DialogHeader>
        <ul className="flex max-h-72 flex-col overflow-y-auto">
          {(requirements ?? []).map((r) => (
            <li key={r.id}>
              <label className="flex cursor-pointer items-center gap-3 border-b border-border/60 py-2 text-sm">
                <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} className="size-3.5 accent-foreground" />
                <span className="min-w-0 flex-1 truncate">
                  <span className="font-medium">{r.signal_label ?? r.title.split(":")[0]}</span>
                  <span className="text-muted-foreground"> · {r.title.includes(":") ? r.title.split(":").slice(1).join(":").trim() : r.title}</span>
                </span>
                {r.market && <span className="font-mono text-xs text-muted-foreground">{r.market}</span>}
                <span className="text-xs text-muted-foreground">{humanize(r.status)}</span>
              </label>
            </li>
          ))}
        </ul>
        <DialogFooter>
          <Button onClick={start} disabled={busy || selected.size === 0}>
            {busy ? "Starting…" : `Send ${selected.size || ""}`.trim()}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RunView({ runId, titles }: { runId: string; titles: Map<string, Requirement> }) {
  const run = useRun(runId);
  const status = run.data?.run.status;
  const live = !!status && ACTIVE.has(status);
  const calls = useRunCalls(runId, live);
  // Results are read once the run has settled; the key includes the status so they reload when it finishes.
  const results = useRunResults(status && !live ? runId : null);
  const conversation = useConversation(runId, status);
  const owners = useMemo(() => ownersById(conversation.data?.owners_by_market), [conversation.data]);
  const model = useMemo(() => buildLanes(undefined, calls.data ?? [], runId, owners), [calls.data, runId, owners]);

  if (run.error) return <ErrorState error={run.error} />;
  if (!run.data) return <LoadingRows />;
  const r = run.data.run;

  return (
    <div className="flex flex-col gap-6">
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground" role="status">
        <span className={cn("flex items-center gap-1.5", live && "text-foreground")}>
          {live && <span className="size-1.5 animate-pulse rounded-full bg-blue-600" aria-hidden />}
          {runStatusLabel(r.status)}
        </span>
        <span className="tabular-nums">
          {r.requirement_ids.length} requirement{r.requirement_ids.length === 1 ? "" : "s"}
        </span>
        <span className="tabular-nums">{fmtCount(r.llm_calls)} agent calls</span>
        <span className="tabular-nums">
          {live ? "running for " : "took "}
          {fmtDuration(durationOf(r))}
        </span>
        {r.challenge_question && <span>Challenge: “{r.challenge_question}”</span>}
      </p>
      {r.error && <p className="text-sm text-red-700 dark:text-red-300">{r.error}</p>}

      <PipelineDiagram run={r} calls={calls.data ?? []} owners={owners} />

      <RequirementChips ids={r.requirement_ids} requirements={titles} />

      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
          <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
          Details: every agent, every call and every answer
        </summary>
        <div className="mt-4 flex flex-col gap-8">
          {calls.error && <ErrorState error={calls.error} />}
          {calls.data && (
            <FlowView
              lanes={model.groups.flatMap((g) => g.lanes)}
              calls={calls.data}
              decisions={[]}
              title={r.requirement_ids.map((id) => titles.get(id)?.signal_label ?? id).join(" · ")}
              live={live}
              requirementId=""
              linked={NO_LINKS}
            />
          )}
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
      </details>
    </div>
  );
}

// Which requirements this run covers: the signal they came from plus a short title, so look-alike titles
// ("…: meet customer expectations") stay distinguishable. Status sits next to each chip.
function RequirementChips({ ids, requirements }: { ids: string[]; requirements: Map<string, Requirement> }) {
  return (
    <div className="flex flex-wrap gap-2">
      {ids.map((id) => {
        const r = requirements.get(id);
        const short = r ? (r.title.includes(":") ? r.title.split(":").slice(1).join(":").trim() : r.title) : "";
        return (
          <Link
            key={id}
            href={`${V}/decision/${encodeURIComponent(id)}`}
            className="flex max-w-sm items-baseline gap-2 rounded-full border px-3 py-1 text-[13px] hover:border-foreground/30"
            title={r?.title ?? id}
          >
            <span className="shrink-0 font-medium">{r?.signal_label ?? (r ? r.title.split(":")[0] : id)}</span>
            {short && <span className="truncate text-muted-foreground">{short}</span>}
            {r && <span className="shrink-0 text-xs text-muted-foreground">· {humanize(r.status)}</span>}
          </Link>
        );
      })}
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
