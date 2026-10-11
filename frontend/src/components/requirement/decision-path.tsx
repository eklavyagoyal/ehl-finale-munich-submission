"use client";

import { ArrowDownRight, ArrowRight, ArrowUpRight, ChevronDown, CircleHelp } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ReliabilityInfo } from "@/components/reliability-info";
import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useRun, useTrace } from "@/lib/api/hooks";
import type { TraceBasis, TraceDriver, TraceEffect, TraceStep, TraceTension } from "@/lib/api/types";
import { actorLabel, fmtCount, fmtDateTime, gateTone, humanize, stanceTone, type Tone } from "@/lib/format";
import { cn } from "cn";

import { AgentStack } from "./agent-icon";
import { BudgetBar, VerdictBar } from "./council-bits";
import { useRequirementContext } from "./context";
import { DecisionForm } from "./decision-dialog";
import { RunButton } from "./shell";
import { V } from "@/lib/routes";

const BASIS: Record<TraceBasis, { label: string; tone: Tone }> = {
  evidence: { label: "Real data", tone: "green" },
  simulation: { label: "Simulated owners", tone: "blue" },
  assumption: { label: "Simulated departments", tone: "amber" },
  mixed: { label: "Mixed", tone: "neutral" },
  human: { label: "You", tone: "neutral" },
  none: { label: "Not run", tone: "muted" },
};

const EFFECT: Record<TraceEffect | "unknown", { label: string; icon: typeof ArrowRight; className: string }> = {
  supports: { label: "supports approval", icon: ArrowUpRight, className: "text-emerald-600" },
  against: { label: "speaks against", icon: ArrowDownRight, className: "text-red-500" },
  neutral: { label: "neutral", icon: ArrowRight, className: "text-muted-foreground/70" },
  unknown: { label: "no data to judge", icon: CircleHelp, className: "text-muted-foreground/70" },
};

const SOURCE_LABEL: Record<string, string> = {
  evidence: "Evidence",
  customers: "Customers",
  company: "Company",
  research: "Research",
  scores: "Score",
  challenger: "Challenger",
  gates: "Gates",
};

// Where each step's details live in the UI; the API's drill_down text is never shown to the PM.
const DRILL: Record<string, { tab: string; label: string }> = {
  evidence: { tab: "evidence", label: "Open evidence" },
  customers: { tab: "councils", label: "Open councils" },
  company: { tab: "councils", label: "Open councils" },
  research: { tab: "councils", label: "Open councils" },
  scores: { tab: "overview", label: "Open score details" },
  synthesis: { tab: "overview", label: "Open overview" },
  challenger: { tab: "overview", label: "Open overview" },
  judge: { tab: "overview", label: "Open overview" },
  decision: { tab: "timeline", label: "Open timeline" },
};

type MarketRow = {
  market: string;
  personas: number;
  verdicts: Record<string, number>;
  mean_budget_points_of_100: number | null;
  top_concern: string | null;
  validated: boolean;
};

// The trace sets "against" when no owner gave budget points; that is missing data, not a verdict.
function effectOf(step: TraceStep): TraceEffect | "unknown" {
  if (step.key === "customers" && Array.isArray(step.output)) {
    const rows = step.output as MarketRow[];
    if (rows.length > 0 && rows.every((r) => r.mean_budget_points_of_100 == null)) return "unknown";
  }
  return step.effect;
}

export function DecisionPath() {
  const { id } = useRequirementContext();
  const { data, error, isLoading } = useTrace(id);
  const base = `${V}/decision/${encodeURIComponent(id)}`;

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;

  return (
    <div className="flex max-w-5xl flex-col gap-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-3">
          {(["supports", "against", "neutral"] as const).map((e) => {
            const Icon = EFFECT[e].icon;
            return (
              <span key={e} className="flex items-center gap-1">
                <Icon className={cn("size-3.5", EFFECT[e].className)} aria-hidden />
                {EFFECT[e].label}
              </span>
            );
          })}
        </span>
        <span className="ml-auto">
          <ReliabilityInfo />
        </span>
      </div>

      <ol className="relative">
        <span aria-hidden className="absolute top-5 bottom-5 left-[7px] w-px bg-border" />
        {data.steps.map((step) => (
          <StepRow key={`${step.order}-${step.key}`} step={step} base={base} />
        ))}
      </ol>
    </div>
  );
}

// One line per step: title, headline and the effect arrow. Everything else (agents, basis, why, output,
// caveat, drivers) opens on click. The decision and "not run yet" steps start open: they hold the action.
function StepRow({ step, base }: { step: TraceStep; base: string }) {
  const always = step.key === "decision" || step.key === "not_simulated";
  const [open, setOpen] = useState(always);
  const effect = effectOf(step);
  const Effect = EFFECT[effect].icon;
  const drivers = step.key === "judge" ? ((step.output as { drivers?: TraceDriver[] })?.drivers ?? []) : [];
  const headline = effect === "unknown" ? "No verdicts or budget points in this run" : (step.headline ?? step.question ?? "");

  return (
    <li className="relative pl-7">
      <span
        aria-hidden
        className={cn(
          "absolute top-[17px] left-[3px] size-[9px] rounded-full border-2 border-background ring-1 ring-border",
          effect === "supports" ? "bg-emerald-500" : effect === "against" ? "bg-red-400" : step.key === "decision" ? "bg-foreground" : "bg-muted-foreground/40",
        )}
      />
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="grid w-full grid-cols-[200px_minmax(0,1fr)_auto] items-center gap-4 rounded-md border-b border-border/60 py-2.5 text-left hover:bg-muted/30"
      >
        <span className="truncate text-sm font-medium">{step.title}</span>
        <span className="truncate text-[13px] text-muted-foreground">{headline}</span>
        <span className="flex items-center gap-2">
          <span title={EFFECT[effect].label} className="flex w-5 justify-center">
            <Effect className={cn("size-4", EFFECT[effect].className)} aria-label={EFFECT[effect].label} />
          </span>
          <ChevronDown className={cn("size-3.5 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
        </span>
      </button>

      {open && (
        <div className="flex flex-col gap-4 border-b border-border/60 pt-3 pb-5">
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            {step.agents?.length ? <AgentStack agents={step.agents} /> : null}
            <ToneBadge tone={BASIS[step.basis]?.tone ?? "muted"}>{BASIS[step.basis]?.label ?? humanize(step.basis)}</ToneBadge>
            {step.question && <span>{step.question}</span>}
          </div>
          {effect === "unknown" ? (
            <p className="max-w-3xl text-[13px] text-foreground/80">This run did not ask the owners for a verdict or budget points.</p>
          ) : (
            step.why && <p className="max-w-3xl text-[13px] text-foreground/80">{step.why}</p>
          )}
          {step.caveat && <p className="max-w-3xl text-xs text-muted-foreground">{step.caveat}</p>}
          {drivers.length > 0 && <Drivers drivers={drivers} />}
          <StepDetail step={step} />
          {step.tensions && step.tensions.length > 0 && <Tensions tensions={step.tensions} />}
          {DRILL[step.key] && (
            <Link href={`${base}/${DRILL[step.key].tab}`} className="self-start text-xs text-muted-foreground hover:text-foreground hover:underline">
              {DRILL[step.key].label} →
            </Link>
          )}
        </div>
      )}
    </li>
  );
}

// Judge drivers stay visible: source → statement → direction, the "why" of the recommendation.
function Drivers({ drivers }: { drivers: TraceDriver[] }) {
  return (
    <ul className="flex max-w-3xl flex-col gap-1 text-[13px]">
      {drivers.slice(0, 6).map((d, i) => {
        const Icon = EFFECT[d.effect]?.icon ?? ArrowRight;
        return (
          <li key={i} className="grid grid-cols-[88px_minmax(0,1fr)_20px] items-baseline gap-2">
            <span className="text-xs text-muted-foreground">{SOURCE_LABEL[d.source] ?? humanize(d.source)}</span>
            <span className={cn(d.weight === "low" && "text-foreground/70")}>{d.statement}</span>
            <Icon className={cn("size-3.5 self-center", EFFECT[d.effect]?.className)} aria-label={EFFECT[d.effect]?.label} />
          </li>
        );
      })}
    </ul>
  );
}

function StepDetail({ step }: { step: TraceStep }) {
  const out = step.output as Record<string, unknown> | unknown[] | undefined;
  const inputs = step.inputs ?? {};
  const asked = typeof inputs.asked === "string" ? inputs.asked : null;

  switch (step.key) {
    case "not_simulated":
      return (
        <div>
          <RunButton />
        </div>
      );
    case "evidence": {
      const findings = (out as { finding: string; kind: string; reviews: number; share: number }[]) ?? [];
      const channels = Object.entries((inputs.linked_evidence_by_channel as Record<string, number>) ?? {});
      return (
        <div className="flex flex-col gap-3 text-[13px]">
          <p className="text-muted-foreground">
            Signal <span className="text-foreground">{String(inputs.signal ?? "")}</span> · {String(inputs.market ?? "all")} ·{" "}
            {fmtCount(Number(inputs.reviews ?? 0))} reviews: {fmtCount(Number(inputs.complaints ?? 0))} complaints,{" "}
            {fmtCount(Number(inputs.requests ?? 0))} requests, {fmtCount(Number(inputs.praise ?? 0))} praise
          </p>
          {channels.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Linked evidence: {channels.map(([c, n]) => `${humanize(c.split("/").pop())} ${n}`).join(" · ")}
            </p>
          )}
          {findings.length > 0 ? (
            <Table
              head={["Finding", "Kind", "Reviews", "Share"]}
              rows={findings.map((f) => [f.finding, humanize(f.kind), fmtCount(f.reviews), `${Math.round(f.share * 100)} %`])}
              align={["left", "left", "right", "right"]}
            />
          ) : (
            <p className="text-xs text-muted-foreground">No condensed findings for this signal yet.</p>
          )}
        </div>
      );
    }
    case "customers": {
      const rows = (out as MarketRow[]) ?? [];
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {asked && <p className="text-xs text-muted-foreground">Asked: {asked}</p>}
          <div className="grid grid-cols-[48px_56px_minmax(80px,1fr)_120px_minmax(0,1.4fr)_92px] items-center gap-x-3 gap-y-2">
            {["Market", "Owners", "Verdicts", "Budget of 100", "Top concern", ""].map((h) => (
              <span key={h} className="text-xs text-muted-foreground">
                {h}
              </span>
            ))}
            {rows.map((r) => (
              <MarketCells key={r.market} row={r} />
            ))}
          </div>
          <BudgetNote />
        </div>
      );
    }
    case "company": {
      const rows = (out as { department: string; verdict: string | null; main_argument: string | null; cost_view: string | null }[]) ?? [];
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {asked && <p className="text-xs text-muted-foreground">Asked: {asked}</p>}
          <Table
            head={["Department", "Main argument", "Cost view", "Verdict"]}
            rows={rows.map((r) => [r.department, r.main_argument ?? "–", humanize(r.cost_view ?? "unknown"), humanize(r.verdict ?? "–")])}
            muted={[3]}
          />
        </div>
      );
    }
    case "research": {
      const rows = (out as { question: string; verdict: string | null; answer: string | null }[]) ?? [];
      const askedBy = Object.entries((inputs.questions_raised_by as Record<string, number>) ?? {});
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {askedBy.length > 0 && <p className="text-xs text-muted-foreground">Questions raised by {askedBy.map(([a, n]) => `${actorLabel(a)} (${n})`).join(", ")}</p>}
          <Table head={["Question", "Verdict", "Answer"]} rows={rows.map((r) => [r.question, humanize(r.verdict ?? "open"), r.answer ?? "–"])} />
        </div>
      );
    }
    case "scores": {
      const s = out as { score_low: number; score_high: number; rank: number | null; criteria: { criterion: string; weight: number; status: string; points_low: number; points_high: number }[] };
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          <p>
            <span className="font-medium tabular-nums">
              {s.score_low.toFixed(0)}–{s.score_high.toFixed(0)}
            </span>{" "}
            <span className="text-muted-foreground">of 100{s.rank ? ` · rank #${s.rank}` : ""}</span>
          </p>
          <Table
            head={["Criterion", "Weight", "Basis", "Points"]}
            rows={s.criteria.map((c) => [
              humanize(c.criterion),
              `${Math.round(c.weight * 100)} %`,
              humanize(c.status),
              c.points_low === c.points_high ? c.points_low.toFixed(1) : `${c.points_low.toFixed(1)}–${c.points_high.toFixed(1)}`,
            ])}
            align={["left", "right", "left", "right"]}
          />
          {typeof inputs.formula === "string" && <p className="text-xs text-muted-foreground">{inputs.formula}</p>}
        </div>
      );
    }
    case "synthesis": {
      const s = (out as { headline?: string; customer_view?: string; evidence_vs_simulation?: string; clinic_questions?: string[] }) ?? {};
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {s.headline && <p className="font-medium">{s.headline}</p>}
          <Facts
            items={[
              ["Customers", s.customer_view],
              ["Evidence vs simulation", s.evidence_vs_simulation],
            ]}
          />
          <List title="Questions for a clinic" items={s.clinic_questions} />
        </div>
      );
    }
    case "challenger": {
      const c = (out as { counter_position?: string; strongest_arguments?: string[]; evidence_that_would_change_the_call?: string[] }) ?? {};
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {c.counter_position && <p className="font-medium">{c.counter_position}</p>}
          <List title="Strongest arguments" items={c.strongest_arguments} />
          <List title="Evidence that would change the call" items={c.evidence_that_would_change_the_call} />
        </div>
      );
    }
    case "judge": {
      const j = (out as { recommendation?: string | null; gate_cap?: string | null; what_would_change_it?: string | null }) ?? {};
      return (
        <div className="flex flex-col gap-2 text-[13px]">
          {j.recommendation && (
            <p className="flex items-center gap-2">
              <span className="text-muted-foreground">Recommends</span>
              <ToneBadge tone={stanceTone(j.recommendation)}>{humanize(j.recommendation)}</ToneBadge>
              {j.gate_cap && <span className="text-xs text-muted-foreground">capped by gate: {humanize(j.gate_cap)}</span>}
            </p>
          )}
          {j.what_would_change_it && (
            <p>
              <span className="text-muted-foreground">What would change it: </span>
              {j.what_would_change_it}
            </p>
          )}
        </div>
      );
    }
    case "decision": {
      const d = (out as {
        status?: string;
        gates?: Record<string, string>;
        blocking_gates?: string[];
        decisions?: { action: string; by: string; at: string; rationale: string; agreed_with_ai: boolean | null }[];
      }) ?? {};
      return (
        <div className="flex max-w-2xl flex-col gap-4 text-[13px]">
          <p className="flex flex-wrap items-center gap-1.5">
            <span className="text-muted-foreground">Gates</span>
            {Object.entries(d.gates ?? {}).map(([g, v]) => (
              <ToneBadge key={g} tone={gateTone(v)}>
                {humanize(g)}
              </ToneBadge>
            ))}
          </p>
          {(d.decisions ?? []).length > 0 && (
            <ul className="flex flex-col gap-1">
              {d.decisions!.map((x, i) => (
                <li key={i}>
                  <span className="font-medium">{humanize(x.action)}</span>
                  <span className="text-muted-foreground">
                    {" "}
                    · {actorLabel(x.by)} · {fmtDateTime(x.at)}
                    {x.agreed_with_ai != null && (x.agreed_with_ai ? " · agreed with the AI" : " · differed from the AI")}
                  </span>
                  <br />
                  <span className="text-muted-foreground">“{x.rationale}”</span>
                </li>
              ))}
            </ul>
          )}
          <DecisionForm />
        </div>
      );
    }
    default:
      return <Generic inputs={step.inputs} output={step.output} />;
  }
}

// Budget points are relative: each owner splits 100 over every proposal of the run plus "keep the price down".
export function BudgetNote() {
  const { runId } = useRequirementContext();
  const { data } = useRun(runId);
  const n = data?.run.requirement_ids.length;
  return (
    <HoverCard openDelay={100}>
      <HoverCardTrigger asChild>
        <span className="cursor-default self-start text-xs text-muted-foreground underline decoration-dotted underline-offset-2">Budget of 100?</span>
      </HoverCardTrigger>
      <HoverCardContent className="w-72 text-xs">
        Each owner splits 100 points{n ? ` across the ${n} proposal${n === 1 ? "" : "s"} of this run` : " across the proposals of the run"} and
        “keep the price down”, so values compare only within one run.
      </HoverCardContent>
    </HoverCard>
  );
}

function MarketCells({ row: r }: { row: MarketRow }) {
  return (
    <>
      <span className="font-mono text-xs">{r.market}</span>
      <span className="tabular-nums">{r.personas}</span>
      <VerdictBar verdicts={r.verdicts} />
      <BudgetBar points={r.mean_budget_points_of_100} />
      <span className="truncate text-muted-foreground" title={r.top_concern ?? undefined}>
        {r.top_concern ?? "–"}
      </span>
      <span className="text-xs text-muted-foreground">{r.validated ? "validated (US)" : "not validated"}</span>
    </>
  );
}

function Tensions({ tensions }: { tensions: TraceTension[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {tensions.slice(0, 3).map((t, i) => (
        <div key={i} className="flex flex-col gap-1.5 rounded-lg border p-3 text-[13px]">
          {t.topic && <p className="text-xs font-medium">{humanize(t.topic)}</p>}
          <p>
            <span className="text-muted-foreground">Customers say </span>
            {t.customers_say ?? "–"}
          </p>
          <p>
            <span className="text-muted-foreground">Company says </span>
            {t.company_says ?? "–"}
          </p>
        </div>
      ))}
    </div>
  );
}

function Table({
  head,
  rows,
  align,
  muted = [],
}: {
  head: string[];
  rows: (string | number)[][];
  align?: ("left" | "right")[];
  muted?: number[];
}) {
  if (rows.length === 0) return <p className="text-xs text-muted-foreground">Nothing recorded.</p>;
  return (
    <table className="w-full text-[13px]">
      <thead>
        <tr className="text-xs text-muted-foreground">
          {head.map((h, i) => (
            <th key={h} className={cn("pb-1.5 font-normal", align?.[i] === "right" ? "text-right" : "text-left")}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-t border-border/60 align-top">
            {r.map((cell, j) => (
              <td
                key={j}
                className={cn(
                  "py-1.5 pr-3",
                  align?.[j] === "right" && "text-right tabular-nums",
                  muted.includes(j) && "text-xs text-muted-foreground",
                )}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Facts({ items }: { items: [string, string | null | undefined][] }) {
  const shown = items.filter(([, v]) => v);
  if (shown.length === 0) return null;
  return (
    <dl className="grid grid-cols-[160px_minmax(0,1fr)] gap-x-3 gap-y-1">
      {shown.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted-foreground">{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function List({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="text-xs text-muted-foreground">{title}</p>
      <ul className="mt-0.5 flex list-disc flex-col gap-0.5 pl-4">
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

// Any step the frontend does not know yet: show its fields plainly instead of hiding them.
function Generic({ inputs, output }: { inputs?: Record<string, unknown>; output?: unknown }) {
  const flat = (v: unknown) => (typeof v === "string" || typeof v === "number" ? String(v) : JSON.stringify(v));
  const entries = [...Object.entries(inputs ?? {}), ...(output && typeof output === "object" && !Array.isArray(output) ? Object.entries(output) : [])];
  if (entries.length === 0) return null;
  return <Facts items={entries.map(([k, v]) => [humanize(k), flat(v)])} />;
}
