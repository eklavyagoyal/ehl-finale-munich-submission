"use client";

import {
  Building2,
  Calculator,
  FileText,
  GitMerge,
  type LucideIcon,
  Pause,
  Play,
  Scale,
  Search,
  ShieldCheck,
  Swords,
  UserCheck,
  Users,
} from "lucide-react";
import { createElement, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import type { ConversationOwner, LlmCall, Run } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

// The expert pipeline as a fixed flowchart: what each step does, independent of any run. A selected run lays
// its numbers on top (calls per step, the active step, a replay). Research and the verifier sit apart: the
// councils' open questions go out to them and the verified answers come back into the synthesis.

const W = 1000;
const H = 380;
const BOX_W = 152;
const BOX_H = 58;

type NodeKey = "brief" | "customers" | "company" | "research" | "verifier" | "score" | "synthesis" | "challenger" | "judge" | "you";

interface DiagramNode {
  key: NodeKey;
  x: number;
  y: number;
  label: string;
  short: string;
  detail: string;
  icon: LucideIcon;
  stage?: string;
}

const NODES: DiagramNode[] = [
  { key: "brief", x: 90, y: 200, label: "Requirement", short: "What is proposed", icon: FileText,
    detail: "A requirement drafted from a signal: title, customer problem and acceptance criteria. Several requirements can go through one run." },
  { key: "customers", x: 290, y: 115, label: "Customer council", short: "Owners vote and split a budget", icon: Users, stage: "market_and_company_twin",
    detail: "Simulated owners of the market react to each proposal, give a verdict (must have, nice to have, don't care, against) and split 100 points between the proposals and keeping the price down. US owners are moderately validated against the BMW customer study." },
  { key: "company", x: 290, y: 295, label: "Company council", short: "Departments weigh cost and fit", icon: Building2, stage: "market_and_company_twin",
    detail: "Simulated departments (design, engineering, finance, quality, product management, sales per market) take a position with a main argument and a cost view. Their arguments and tensions count more than their verdicts." },
  { key: "research", x: 480, y: 52, label: "Research", short: "Looks up open questions", icon: Search, stage: "research",
    detail: "Questions the councils raise (competitors, regulation, technology) go to web research. Every answer cites its sources." },
  { key: "verifier", x: 670, y: 52, label: "Verifier", short: "Checks every source", icon: ShieldCheck, stage: "research",
    detail: "A second model checks whether each cited source really supports the answer; unsupported answers are marked as such." },
  { key: "score", x: 480, y: 205, label: "Score", short: "Weights, in code", icon: Calculator, stage: "scoring",
    detail: "The weighted criteria (demand, impact, competitive gap, fit, delivery, reuse). Real reviews give point values; simulated and assumed ratings only widen the range." },
  { key: "synthesis", x: 670, y: 205, label: "Synthesis", short: "Puts the picture together", icon: GitMerge, stage: "synthesis_and_vote",
    detail: "Combines evidence, both councils and research into one picture and names the tensions between customers and company." },
  { key: "challenger", x: 760, y: 325, label: "Challenger", short: "Argues the other side", icon: Swords, stage: "synthesis_and_vote",
    detail: "Builds the strongest case against the emerging recommendation and names the evidence that would change it." },
  { key: "judge", x: 850, y: 205, label: "Judge", short: "Recommends, with drivers", icon: Scale, stage: "synthesis_and_vote",
    detail: "One judge recommends approve, reject, investigate or defer and names the inputs that drove the vote. It is advice." },
  { key: "you", x: 962, y: 205, label: "You", short: "Decide", icon: UserCheck,
    detail: "You approve, reject, challenge or defer, with a rationale. Approval needs every gate on pass." },
];

const BY_KEY = new Map(NODES.map((n) => [n.key, n]));

type Side = "l" | "r" | "t" | "b";
const port = (key: NodeKey, side: Side) => {
  const n = BY_KEY.get(key)!;
  const half = key === "you" ? 18 : BOX_W / 2;
  const vhalf = key === "you" ? 18 : BOX_H / 2;
  return { l: { x: n.x - half, y: n.y }, r: { x: n.x + half, y: n.y }, t: { x: n.x, y: n.y - vhalf }, b: { x: n.x, y: n.y + vhalf } }[side];
};

// Rounded connectors: horizontal tangents for side ports, vertical ones for top and bottom ports.
function curve(a: NodeKey, as: Side, b: NodeKey, bs: Side) {
  const p = port(a, as);
  const q = port(b, bs);
  const k = 0.5;
  const c1 = as === "r" || as === "l" ? { x: p.x + (q.x - p.x) * k, y: p.y } : { x: p.x, y: p.y + (q.y - p.y) * k };
  const c2 = bs === "r" || bs === "l" ? { x: q.x - (q.x - p.x) * k, y: q.y } : { x: q.x, y: q.y - (q.y - p.y) * k };
  return `M ${p.x} ${p.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${q.x} ${q.y}`;
}

const EDGES: { from: NodeKey; to: NodeKey; d: string; label?: string; dashed?: boolean }[] = [
  { from: "brief", to: "customers", d: curve("brief", "r", "customers", "l") },
  { from: "brief", to: "company", d: curve("brief", "r", "company", "l") },
  { from: "customers", to: "score", d: curve("customers", "r", "score", "l") },
  { from: "company", to: "score", d: curve("company", "r", "score", "l") },
  // Both councils raise open questions; one line keeps the picture calm.
  { from: "customers", to: "research", d: curve("customers", "t", "research", "l"), label: "open questions", dashed: true },
  { from: "research", to: "verifier", d: curve("research", "r", "verifier", "l") },
  { from: "verifier", to: "synthesis", d: curve("verifier", "b", "synthesis", "t"), label: "verified answers" },
  { from: "score", to: "synthesis", d: curve("score", "r", "synthesis", "l") },
  { from: "synthesis", to: "challenger", d: curve("synthesis", "b", "challenger", "l") },
  { from: "challenger", to: "judge", d: curve("challenger", "r", "judge", "b"), label: "counter-case" },
  { from: "synthesis", to: "judge", d: curve("synthesis", "r", "judge", "l") },
  { from: "judge", to: "you", d: curve("judge", "r", "you", "l") },
];

// Which step a model call belongs to.
export function nodeOfCall(call: LlmCall): NodeKey | null {
  const id = call.agent_id;
  if (id.startsWith("persona:") || id === "tinytroupe" || call.purpose.startsWith("persona") || call.purpose === "ssr_responses") return "customers";
  if (id.startsWith("dept:") || call.purpose === "department_review") return "company";
  if (id === "agent:verifier" || call.purpose === "research_verification") return "verifier";
  if (id === "agent:research" || call.purpose === "web_research") return "research";
  if (id === "agent:synthesizer" || call.purpose === "synthesis") return "synthesis";
  if (id === "agent:challenger" || call.purpose === "challenge") return "challenger";
  if (id.startsWith("judge:") || call.purpose === "vote") return "judge";
  return null;
}

const STAGE_NODES: Record<string, NodeKey[]> = {
  market_and_company_twin: ["customers", "company"],
  research: ["research", "verifier"],
  scoring: ["score"],
  synthesis_and_vote: ["synthesis", "challenger", "judge"],
};

export function PipelineDiagram({
  run,
  calls,
  owners,
}: {
  run?: Run | null;
  calls?: LlmCall[];
  owners?: Map<string, ConversationOwner>;
}) {
  const [open, setOpen] = useState<NodeKey | null>(null);
  const sorted = useMemo(() => [...(calls ?? [])].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id), [calls]);
  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const live = run?.status === "queued" || run?.status === "running";
  const shown = step ?? sorted.length;

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setStep((s) => {
        const next = (s ?? 0) + 1;
        if (next >= sorted.length) {
          setPlaying(false);
          return null;
        }
        return next;
      });
    }, 120);
    return () => clearInterval(timer);
  }, [playing, sorted.length]);

  // Calls and agents per step, up to the replay position.
  const perNode = new Map<NodeKey, { calls: number; agents: Set<string> }>();
  sorted.slice(0, shown).forEach((c) => {
    const key = nodeOfCall(c);
    if (!key) return;
    const entry = perNode.get(key) ?? { calls: 0, agents: new Set<string>() };
    entry.calls += 1;
    entry.agents.add(c.agent_id);
    perNode.set(key, entry);
  });
  const current = step !== null && step > 0 ? nodeOfCall(sorted[step - 1]) : null;
  const liveNodes = new Set(live ? (STAGE_NODES[run?.progress?.stage ?? ""] ?? []) : []);
  const active = (key: NodeKey) => current === key || (step === null && liveNodes.has(key));
  const openNode = open ? BY_KEY.get(open)! : null;

  return (
    <div className="flex flex-col gap-3">
      {run && sorted.length > 0 && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <Button
            size="icon-sm"
            variant="outline"
            onClick={() => {
              if (playing) return setPlaying(false);
              setStep(0);
              setPlaying(true);
            }}
            disabled={live}
            aria-label={playing ? "Pause replay" : "Replay the run"}
            title={live ? "Replay unlocks when the run is complete" : undefined}
          >
            {playing ? <Pause /> : <Play />}
          </Button>
          <span className="tabular-nums">
            {step === null ? (live ? "Live" : "Replay the run") : `${shown} / ${sorted.length} calls`}
          </span>
        </div>
      )}

      <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
          <defs>
            <marker id="pd-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 8 4 L 0 8 z" className="fill-muted-foreground/50" />
            </marker>
          </defs>
          {EDGES.map((e) => {
            const hot = active(e.to);
            return (
              <path
                key={`${e.from}-${e.to}`}
                id={`pd-${e.from}-${e.to}`}
                d={e.d}
                fill="none"
                strokeWidth={hot ? 1.6 : 1.1}
                strokeDasharray={e.dashed ? "4 4" : undefined}
                markerEnd="url(#pd-arrow)"
                className={cn("transition-colors", hot ? "stroke-blue-600" : "stroke-muted-foreground/40")}
              />
            );
          })}
          {EDGES.filter((e) => e.label).map((e) => (
            <text key={`l-${e.from}-${e.to}`} className="fill-muted-foreground" style={{ fontSize: 10 }}>
              <textPath href={`#pd-${e.from}-${e.to}`} startOffset="50%" textAnchor="middle" dy={-4}>
                {e.label}
              </textPath>
            </text>
          ))}
          {/* A dot travels into the step that made the latest call. */}
          {EDGES.filter((e) => current === e.to).map((e) => (
            <circle key={`dot-${e.from}-${e.to}-${shown}`} r={4} className="fill-blue-600">
              <animateMotion dur="0.5s" repeatCount="1" fill="freeze" path={e.d} />
            </circle>
          ))}
        </svg>

        {NODES.map((n) => {
          const stats = perNode.get(n.key);
          const isYou = n.key === "you";
          const style = { left: `${(n.x / W) * 100}%`, top: `${(n.y / H) * 100}%` };
          if (isYou) {
            return (
              <button
                key={n.key}
                type="button"
                onClick={() => setOpen((o) => (o === n.key ? null : n.key))}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1"
                style={style}
              >
                <span className="flex size-9 items-center justify-center rounded-full bg-foreground text-background">
                  {createElement(n.icon, { className: "size-4", strokeWidth: 1.5 })}
                </span>
                <span className="text-xs font-medium">{n.label}</span>
              </button>
            );
          }
          return (
            <button
              key={n.key}
              type="button"
              onClick={() => setOpen((o) => (o === n.key ? null : n.key))}
              aria-expanded={open === n.key}
              className={cn(
                "absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-2.5 rounded-2xl border bg-background px-3 text-left shadow-xs transition-colors hover:border-foreground/30",
                active(n.key) && "border-blue-600 ring-2 ring-blue-600/15",
                open === n.key && "border-foreground/50",
                run && !stats && n.key !== "brief" && n.key !== "score" && "opacity-60",
              )}
              style={{ ...style, width: `${(BOX_W / W) * 100}%`, height: `${(BOX_H / H) * 100}%` }}
            >
              {createElement(n.icon, { className: "size-4 shrink-0 text-muted-foreground", strokeWidth: 1.5 })}
              <span className="flex min-w-0 flex-col leading-tight">
                <span className="truncate text-[13px] font-medium">{n.label}</span>
                <span className="truncate text-[11px] text-muted-foreground">
                  {stats
                    ? `${stats.agents.size > 1 ? `${stats.agents.size} agents · ` : ""}${fmtCount(stats.calls)} call${stats.calls === 1 ? "" : "s"}`
                    : n.short}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {openNode && <NodeDetail node={openNode} stats={perNode.get(openNode.key)} owners={owners} />}
    </div>
  );
}

function NodeDetail({
  node,
  stats,
  owners,
}: {
  node: DiagramNode;
  stats?: { calls: number; agents: Set<string> };
  owners?: Map<string, ConversationOwner>;
}) {
  const names = [...(stats?.agents ?? [])].map((id) => {
    const o = owners?.get(id);
    if (o) return `${o.name ?? o.display_name}${o.market ? ` (${o.market})` : ""}`;
    const [kind, rest = ""] = id.split(":");
    if (kind === "dept") return rest.replace(/-/g, " ");
    if (kind === "judge") return `Judge ${rest}`;
    return id === "tinytroupe" ? "Simulated owners" : rest || id;
  });
  return (
    <div className="flex max-w-3xl flex-col gap-1.5 rounded-xl border p-4 text-[13px]">
      <p className="font-medium">
        {node.label} <span className="font-normal text-muted-foreground">· {node.short}</span>
      </p>
      <p className="text-foreground/80">{node.detail}</p>
      {stats && (
        <p className="text-xs text-muted-foreground">
          In this run: {fmtCount(stats.calls)} model call{stats.calls === 1 ? "" : "s"}
          {names.length ? ` by ${names.slice(0, 12).join(", ")}${names.length > 12 ? ` +${names.length - 12}` : ""}` : ""}.
        </p>
      )}
    </div>
  );
}
