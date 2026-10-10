"use client";

import {
  BadgeCheck,
  Banknote,
  Building2,
  FileText,
  GitMerge,
  type LucideIcon,
  Pause,
  PenTool,
  Play,
  Scale,
  Search,
  ShieldCheck,
  Swords,
  Target,
  TrendingUp,
  User,
  UserCheck,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { Decision, LlmCall } from "@/lib/api/types";
import { actorLabel, fmtDateTime, humanize } from "@/lib/format";
import { cn } from "cn";

import { type Lane, LaneDetail } from "./lane-detail";

const W = 1000;
const ROW = 30;
const AGENT_X = 300;
const SYNTH = { x: 660, label: "Synthesis" };
const JUDGE_X = 810;
const PM_X = 955;

type Point = { x: number; y: number };
type Track = { from: Point; to: Point; c1: Point; c2: Point };

interface FlowNode {
  id: string;
  x: number;
  y: number;
  icon: LucideIcon;
  lane?: Lane;
  tone?: "dark";
  track?: Track;
}

const DEPT_ICON: Record<string, LucideIcon> = {
  design: PenTool,
  engineering: Wrench,
  sales: TrendingUp,
  finance: Banknote,
  quality: BadgeCheck,
  "product-management": Target,
};

const STANCE_DOT: Record<string, string> = {
  green: "bg-emerald-500",
  red: "bg-red-500",
  amber: "bg-amber-500",
  muted: "bg-zinc-300 dark:bg-zinc-600",
};

function curve(from: Point, to: Point): Track {
  const mid = (from.x + to.x) / 2;
  return { from, to, c1: { x: mid, y: from.y }, c2: { x: mid, y: to.y } };
}

function line(from: Point, to: Point): Track {
  return { from, to, c1: from, c2: to };
}

function at(track: Track, t: number): Point {
  const u = 1 - t;
  const k = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t];
  const pts = [track.from, track.c1, track.c2, track.to];
  return { x: pts.reduce((s, p, i) => s + p.x * k[i], 0), y: pts.reduce((s, p, i) => s + p.y * k[i], 0) };
}

function d(track: Track): string {
  const { from, c1, c2, to } = track;
  return `M ${from.x} ${from.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${to.x} ${to.y}`;
}

function iconFor(agentId: string): LucideIcon {
  const [kind, rest = ""] = agentId.split(":");
  if (kind === "persona") return User;
  if (kind === "dept") return DEPT_ICON[rest.replace(/-(us|eu|cn)$/, "")] ?? Building2;
  if (kind === "judge") return Scale;
  if (agentId === "agent:research") return Search;
  if (agentId === "agent:verifier") return ShieldCheck;
  if (agentId === "agent:synthesizer") return GitMerge;
  if (agentId === "agent:challenger") return Swords;
  return Building2;
}

// Agents as faces: brief → market and company twin in parallel → research and verification →
// synthesis → judges and challenger → PM. Each LLM call is a dot on the line into its agent;
// the replay reveals calls in the order the backend made them.
export function FlowView({
  lanes,
  calls,
  decisions,
  title,
  live,
}: {
  lanes: Lane[];
  calls: LlmCall[];
  decisions: Decision[];
  title: string;
  live: boolean;
}) {
  const layout = useMemo(() => buildLayout(lanes), [lanes]);
  const sorted = useMemo(() => [...calls].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id), [calls]);
  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
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
    }, 140);
    return () => clearInterval(timer);
  }, [playing, sorted.length]);

  const dots = useMemo(() => {
    const perAgent = new Map<string, LlmCall[]>();
    for (const c of sorted) perAgent.set(c.agent_id, [...(perAgent.get(c.agent_id) ?? []), c]);
    const out: { call: LlmCall; p: Point; index: number }[] = [];
    sorted.forEach((call, index) => {
      const node = layout.byId.get(call.agent_id);
      if (!node?.track) return;
      const mine = perAgent.get(call.agent_id)!;
      const k = mine.indexOf(call);
      const t = 0.58 + (0.34 * (k + 0.5)) / mine.length;
      out.push({ call, p: at(node.track, t), index });
    });
    return out;
  }, [sorted, layout]);

  const latest = shown > 0 ? sorted[shown - 1] : undefined;
  const H = layout.height;

  function togglePlay() {
    if (playing) {
      setPlaying(false);
      return;
    }
    setStep(0);
    setPlaying(true);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <Button size="icon-sm" variant="outline" onClick={togglePlay} aria-label={playing ? "Pause replay" : "Replay the run"} disabled={sorted.length === 0}>
          {playing ? <Pause /> : <Play />}
        </Button>
        <input
          type="range"
          min={0}
          max={sorted.length}
          step={1}
          value={shown}
          onChange={(e) => {
            setPlaying(false);
            const v = Number(e.target.value);
            setStep(v >= sorted.length ? null : v);
          }}
          aria-label="Calls shown"
          className="w-56 accent-blue-600"
        />
        <span className="tabular-nums">
          {shown} / {sorted.length} calls{live && step === null ? " · live" : ""}
        </span>
        {latest && (
          <span className="truncate">
            <span className="text-foreground">{actorLabel(latest.agent_id)}</span> · {humanize(latest.purpose)} · {latest.model} ·{" "}
            {latest.input_tokens + latest.output_tokens} tokens · {fmtDateTime(latest.created_at)}
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <div className="relative min-w-[820px]" style={{ aspectRatio: `${W} / ${H}` }}>
          <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
            <g fill="none" stroke="var(--border)" strokeWidth={1}>
              {layout.edges.map((e, i) => (
                <path key={i} d={d(e)} />
              ))}
              {layout.nodes
                .filter((n) => n.track)
                .map((n) => (
                  <path
                    key={n.id}
                    d={d(n.track!)}
                    stroke={latest?.agent_id === n.id ? "#2563eb" : "var(--border)"}
                    strokeOpacity={latest?.agent_id === n.id ? 0.6 : 1}
                  />
                ))}
            </g>
            {dots.map(({ call, p, index }) => {
              if (index >= shown) return null;
              const verify = call.purpose === "research_verification" || call.agent_id === "agent:verifier";
              const current = index === shown - 1 && step !== null;
              return (
                <g key={call.id}>
                  {current && <circle cx={p.x} cy={p.y} r={8} fill="#2563eb" opacity={0.15} />}
                  {verify ? (
                    <circle cx={p.x} cy={p.y} r={4} fill="var(--background)" stroke="#2563eb" strokeWidth={1.5} />
                  ) : (
                    <circle cx={p.x} cy={p.y} r={current ? 4 : 3} fill={call.status === "ok" ? "#2563eb" : "#ef4444"} />
                  )}
                </g>
              );
            })}
          </svg>

          {layout.labels.map((label) => (
            <span
              key={label.text}
              className="absolute -translate-y-1/2 text-[11px] text-muted-foreground"
              style={{ left: `${(label.x / W) * 100}%`, top: `${(label.y / H) * 100}%` }}
            >
              {label.text}
            </span>
          ))}

          {layout.nodes.map((node) => (
            <Node key={node.id} node={node} H={H} active={latest?.agent_id === node.id} title={title} decisions={decisions} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Node({ node, H, active, title, decisions }: { node: FlowNode; H: number; active: boolean; title: string; decisions: Decision[] }) {
  const Icon = node.icon;
  const style = { left: `${(node.x / W) * 100}%`, top: `${(node.y / H) * 100}%` };
  const region = node.lane?.region;
  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2" style={style}>
      {region && node.x === AGENT_X && (
        <span className="absolute top-1/2 right-full mr-1.5 -translate-y-1/2 font-mono text-[10px] text-muted-foreground/70">{region}</span>
      )}
      <HoverCard openDelay={100} closeDelay={60}>
        <HoverCardTrigger asChild>
          <button
            type="button"
            aria-label={node.lane ? actorLabel(node.id) : node.id === "brief" ? "Requirement brief" : "Product manager"}
            className={cn(
              "relative flex size-7 items-center justify-center rounded-full border bg-background text-muted-foreground transition-colors hover:border-foreground hover:text-foreground",
              node.tone === "dark" && "border-foreground bg-foreground text-background hover:text-background",
              active && "border-blue-600 text-blue-700 dark:text-blue-300",
            )}
          >
            <Icon className="size-3.5" strokeWidth={1.5} />
            {node.lane?.voteTone && (
              <span className={cn("absolute -right-0.5 -bottom-0.5 size-2 rounded-full ring-2 ring-background", STANCE_DOT[node.lane.voteTone] ?? STANCE_DOT.muted)} />
            )}
          </button>
        </HoverCardTrigger>
        <HoverCardContent side="right" align="start" className="w-80 text-xs">
          {node.lane ? (
            <LaneDetail lane={node.lane} />
          ) : node.id === "brief" ? (
            <p>
              <span className="font-medium">Requirement brief</span>
              <br />
              <span className="text-muted-foreground">{title}</span>
            </p>
          ) : (
            <div className="flex flex-col gap-1.5">
              <p className="font-medium">Product manager</p>
              {decisions.length === 0 && <p className="text-muted-foreground">No decision yet. The recommendation is only a proposal.</p>}
              {decisions.map((dec) => (
                <p key={dec.id}>
                  {humanize(dec.action)} · {actorLabel(dec.actor_id)} · {fmtDateTime(dec.created_at)}
                  <br />
                  <span className="text-muted-foreground">“{dec.rationale}”</span>
                </p>
              ))}
            </div>
          )}
        </HoverCardContent>
      </HoverCard>
    </div>
  );
}

function buildLayout(lanes: Lane[]) {
  const pick = (prefix: string) => lanes.filter((l) => l.id.startsWith(prefix));
  const personas = pick("persona:");
  const depts = pick("dept:");
  const judges = pick("judge:");
  const byLane = new Map(lanes.map((l) => [l.id, l]));
  const others = lanes.filter(
    (l) =>
      !l.id.startsWith("persona:") &&
      !l.id.startsWith("dept:") &&
      !l.id.startsWith("judge:") &&
      !["agent:research", "agent:verifier", "agent:synthesizer", "agent:challenger"].includes(l.id),
  );

  const top = 44;
  const personaY = personas.map((_, i) => top + i * ROW);
  const deptTop = personas.length ? top + personas.length * ROW + 30 : top;
  const deptY = depts.map((_, i) => deptTop + i * ROW);
  const lastY = Math.max(top, ...personaY, ...deptY);
  const c = (top + lastY) / 2;
  const height = Math.max(lastY + 40, 320);

  const brief: Point = { x: 40, y: c };
  const synth: Point = { x: SYNTH.x, y: c };
  const pm: Point = { x: PM_X, y: c };
  const nodes: FlowNode[] = [{ id: "brief", x: brief.x, y: brief.y, icon: FileText }];
  const edges: Track[] = [];
  const labels: { text: string; x: number; y: number }[] = [];

  if (personas.length) labels.push({ text: `Public panel · ${personas.length}`, x: AGENT_X - 14, y: top - 26 });
  if (depts.length) labels.push({ text: `Company · ${depts.length}`, x: AGENT_X - 14, y: deptTop - 26 });

  [...personas.map((l, i) => [l, personaY[i]] as const), ...depts.map((l, i) => [l, deptY[i]] as const)].forEach(([lane, y]) => {
    const p = { x: AGENT_X, y };
    nodes.push({ id: lane.id, x: p.x, y: p.y, icon: iconFor(lane.id), lane, track: curve({ x: brief.x + 16, y: brief.y }, { x: p.x - 16, y: p.y }) });
    edges.push(curve({ x: p.x + 16, y: p.y }, { x: synth.x - 16, y: synth.y }));
  });

  const research = byLane.get("agent:research");
  const verifier = byLane.get("agent:verifier");
  const researchP = { x: 530, y: top };
  const verifierP = { x: 530, y: top + 64 };
  if (research) {
    nodes.push({ id: research.id, ...researchP, icon: Search, lane: research, track: line({ x: researchP.x - 70, y: researchP.y }, { x: researchP.x - 16, y: researchP.y }) });
    labels.push({ text: "Research", x: researchP.x + 20, y: researchP.y });
  }
  if (verifier) {
    nodes.push({
      id: verifier.id,
      ...verifierP,
      icon: ShieldCheck,
      lane: verifier,
      track: line({ x: verifierP.x, y: research ? researchP.y + 16 : verifierP.y - 50 }, { x: verifierP.x, y: verifierP.y - 16 }),
    });
    edges.push(curve({ x: verifierP.x + 16, y: verifierP.y }, { x: synth.x - 16, y: synth.y }));
  } else if (research) {
    edges.push(curve({ x: researchP.x + 16, y: researchP.y }, { x: synth.x - 16, y: synth.y }));
  }

  const synthLane = byLane.get("agent:synthesizer");
  nodes.push({
    id: synthLane?.id ?? "agent:synthesizer",
    ...synth,
    icon: GitMerge,
    lane: synthLane,
    track: line({ x: synth.x - 70, y: synth.y + 26 }, { x: synth.x - 12, y: synth.y + 12 }),
  });
  labels.push({ text: SYNTH.label, x: synth.x - 30, y: synth.y + 30 });

  const judgeSpan = 46;
  judges.forEach((lane, i) => {
    const y = c + (i - (judges.length - 1) / 2) * judgeSpan;
    nodes.push({ id: lane.id, x: JUDGE_X, y, icon: Scale, lane, track: curve({ x: synth.x + 16, y: synth.y }, { x: JUDGE_X - 16, y }) });
    edges.push(curve({ x: JUDGE_X + 16, y }, { x: pm.x - 16, y: pm.y }));
  });
  if (judges.length) labels.push({ text: "Judges", x: JUDGE_X - 18, y: c - ((judges.length - 1) / 2) * judgeSpan - 30 });

  const challenger = byLane.get("agent:challenger");
  const extra = [...(challenger ? [challenger] : []), ...others];
  extra.forEach((lane, i) => {
    const y = c + ((judges.length - 1) / 2) * judgeSpan + 70 + i * 46;
    nodes.push({ id: lane.id, x: JUDGE_X, y, icon: iconFor(lane.id), lane, track: curve({ x: synth.x + 16, y: synth.y }, { x: JUDGE_X - 16, y }) });
    edges.push(curve({ x: JUDGE_X + 16, y }, { x: pm.x - 16, y: pm.y }));
  });

  nodes.push({ id: "pm", ...pm, icon: UserCheck, tone: "dark" });
  labels.push({ text: "You", x: pm.x - 10, y: pm.y + 30 });

  const byId = new Map(nodes.map((n) => [n.id, n]));
  return { nodes, edges, labels, byId, height };
}
