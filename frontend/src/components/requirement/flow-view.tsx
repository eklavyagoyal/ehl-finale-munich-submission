"use client";

import { FileText, Pause, Play, UserCheck } from "lucide-react";
import Link from "next/link";
import { createElement, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { Decision, LlmCall } from "@/lib/api/types";
import { actorLabel, fmtDateTime, humanize } from "@/lib/format";
import { cn } from "cn";

import { agentIcon } from "./agent-icon";
import { allRecordsHref, recordHref } from "./call-records";
import { type Lane, LaneDetail } from "./lane-detail";

// Fixed columns in a 1000-unit wide canvas: brief | council members with names | the chain to the PM.
const W = 1000;
const ROW = 28;
const BRIEF_X = 24;
const TRUNK_IN = 92;
const AGENT_X = 170;
const NAME_X = 188;
const TRUNK_OUT = 336;
const CHAIN: { id: string; x: number; label: string }[] = [
  { id: "agent:research", x: 410, label: "Research" },
  { id: "agent:verifier", x: 490, label: "Verifier" },
  { id: "agent:synthesizer", x: 580, label: "Synthesis" },
  { id: "agent:challenger", x: 680, label: "Challenger" },
];
const JUDGE_X = 785;
const PM_X = 940;

type Point = { x: number; y: number };

interface FlowNode {
  id: string;
  x: number;
  y: number;
  lane?: Lane;
  kind: "brief" | "member" | "chain" | "pm";
  // The straight segment that carries this agent's call dots, ending just before the node.
  track?: { from: Point; to: Point };
}

const STANCE_DOT: Record<string, string> = {
  green: "bg-emerald-500",
  red: "bg-red-500",
  amber: "bg-amber-500",
  muted: "bg-zinc-300 dark:bg-zinc-600",
};

const pct = (v: number, of: number) => `${(v / of) * 100}%`;

// The run as a chain: brief → customer and company council (parallel) → research → verifier →
// synthesis → challenger → judge → you. Every LLM call is a dot on the straight line into its agent;
// the replay reveals the calls in the order the backend made them, once the run is complete.
export function FlowView({
  lanes,
  calls,
  decisions,
  title,
  live,
  requirementId,
  linked,
}: {
  lanes: Lane[];
  calls: LlmCall[];
  decisions: Decision[];
  title: string;
  live: boolean;
  requirementId: string;
  linked: Set<string>;
}) {
  const layout = useMemo(() => buildLayout(lanes), [lanes]);
  const sorted = useMemo(() => [...calls].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id), [calls]);
  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const shown = live ? sorted.length : (step ?? sorted.length);

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
      const t = (mine.indexOf(call) + 0.5) / mine.length;
      const { from, to } = node.track;
      out.push({ call, p: { x: from.x + (to.x - from.x) * t, y: from.y }, index });
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
        <Button
          size="icon-sm"
          variant="outline"
          onClick={togglePlay}
          aria-label={playing ? "Pause replay" : "Replay the run"}
          disabled={live || sorted.length === 0}
          title={live ? "Replay unlocks when the run is complete" : undefined}
        >
          {playing ? <Pause /> : <Play />}
        </Button>
        <input
          type="range"
          min={0}
          max={sorted.length}
          step={1}
          value={shown}
          disabled={live}
          onChange={(e) => {
            setPlaying(false);
            const v = Number(e.target.value);
            setStep(v >= sorted.length ? null : v);
          }}
          aria-label="Calls shown"
          className="w-56 accent-blue-600 disabled:opacity-40"
        />
        <span className="tabular-nums">
          {shown} / {sorted.length} calls
        </span>
        {live && (
          <span className="flex items-center gap-1.5 text-foreground">
            <span className="size-1.5 animate-pulse rounded-full bg-blue-600" aria-hidden />
            Live · replay unlocks when the run is complete
          </span>
        )}
        {!live && latest && (
          <span className="truncate">
            <span className="text-foreground">{layout.byId.get(latest.agent_id)?.lane?.name ?? actorLabel(latest.agent_id)}</span> ·{" "}
            {humanize(latest.purpose)} · {latest.model} · {fmtDateTime(latest.created_at)} ·{" "}
            {latest.input_record_ids.length > 0 ? (
              <Link
                href={
                  latest.input_record_ids.length === 1
                    ? recordHref(requirementId, latest.input_record_ids[0], linked)
                    : allRecordsHref(latest.input_record_ids)
                }
                className="text-foreground underline-offset-4 hover:underline"
              >
                saw {latest.input_record_ids.length} record{latest.input_record_ids.length === 1 ? "" : "s"}
              </Link>
            ) : (
              "saw no records"
            )}
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <div className="relative min-w-[880px]" style={{ aspectRatio: `${W} / ${H}` }}>
          <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
            <g fill="none" stroke="var(--border)" strokeWidth={1} shapeRendering="crispEdges">
              {layout.paths.map((d, i) => (
                <path key={i} d={d} />
              ))}
              {layout.nodes
                .filter((n) => n.track)
                .map((n) => (
                  <line
                    key={n.id}
                    x1={n.track!.from.x}
                    y1={n.track!.from.y}
                    x2={n.track!.to.x}
                    y2={n.track!.to.y}
                    stroke={latest?.agent_id === n.id && !live ? "#2563eb" : "var(--border)"}
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
              className={cn("absolute -translate-y-1/2 text-[11px] whitespace-nowrap text-muted-foreground", label.center && "-translate-x-1/2")}
              style={{ left: pct(label.x, W), top: pct(label.y, H) }}
            >
              {label.text}
            </span>
          ))}

          {layout.nodes
            .filter((n) => n.kind === "member" && n.lane)
            .map((n) => (
              <span
                key={`name-${n.id}`}
                className="absolute flex -translate-y-1/2 items-baseline gap-1.5 truncate text-[11px]"
                style={{ left: pct(NAME_X, W), top: pct(n.y, H), maxWidth: pct(TRUNK_OUT - 18 - NAME_X, W) }}
                title={n.lane!.detail ?? n.lane!.name}
              >
                {n.lane!.region && <span className="font-mono text-[10px] text-muted-foreground/70">{n.lane!.region}</span>}
                <span className="truncate">{n.lane!.name}</span>
              </span>
            ))}

          {layout.nodes.map((node) => (
            <Node key={node.id} node={node} H={H} active={!live && latest?.agent_id === node.id} title={title} decisions={decisions} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Node({ node, H, active, title, decisions }: { node: FlowNode; H: number; active: boolean; title: string; decisions: Decision[] }) {
  const icon = node.kind === "brief" ? FileText : node.kind === "pm" ? UserCheck : agentIcon(node.id);
  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: pct(node.x, W), top: pct(node.y, H) }}>
      <HoverCard openDelay={100} closeDelay={60}>
        <HoverCardTrigger asChild>
          <button
            type="button"
            aria-label={node.lane ? node.lane.name : node.kind === "brief" ? "Requirement brief" : "Product manager"}
            className={cn(
              "relative flex size-7 items-center justify-center rounded-full border bg-background text-muted-foreground transition-colors hover:border-foreground hover:text-foreground",
              node.kind === "pm" && "border-foreground bg-foreground text-background hover:text-background",
              active && "border-blue-600 text-blue-700 dark:text-blue-300",
            )}
          >
            {createElement(icon, { className: "size-3.5", strokeWidth: 1.5 })}
            {node.lane?.voteTone && (
              <span className={cn("absolute -right-0.5 -bottom-0.5 size-2 rounded-full ring-2 ring-background", STANCE_DOT[node.lane.voteTone] ?? STANCE_DOT.muted)} />
            )}
          </button>
        </HoverCardTrigger>
        <HoverCardContent side="right" align="start" className="w-80 text-xs">
          {node.lane ? (
            <LaneDetail lane={node.lane} />
          ) : node.kind === "brief" ? (
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
  const chainIds = new Set(CHAIN.map((c) => c.id));
  const byLane = new Map(lanes.map((l) => [l.id, l]));
  const customers = lanes.filter((l) => l.group === "Customer council");
  const company = lanes.filter((l) => l.group === "Company council");
  const judges = lanes.filter((l) => l.id.startsWith("judge:"));
  const others = lanes.filter((l) => l.group === "Agents" && !chainIds.has(l.id) && !l.id.startsWith("judge:"));

  // Council rows: customers, then company, then anything unexpected, each block with a header.
  const blocks = [
    { title: "Customer council", lanes: customers },
    { title: "Company council", lanes: company },
    { title: "Other agents", lanes: others },
  ].filter((b) => b.lanes.length > 0);
  const rows: { lane: Lane; y: number }[] = [];
  const labels: { text: string; x: number; y: number; center?: boolean }[] = [];
  let y = 40;
  for (const block of blocks) {
    labels.push({ text: `${block.title} · ${block.lanes.length}`, x: AGENT_X - 14, y: y - 20 });
    for (const lane of block.lanes) {
      rows.push({ lane, y });
      y += ROW;
    }
    y += 30;
  }
  const firstY = rows[0]?.y ?? 40;
  const lastY = rows[rows.length - 1]?.y ?? 40;
  const c = Math.round((firstY + lastY) / 2);
  const height = Math.max(lastY + 50, 300);

  const nodes: FlowNode[] = [{ id: "brief", kind: "brief", x: BRIEF_X, y: c }];
  const paths: string[] = [];

  // Brief → trunk → every council member, all straight.
  if (rows.length) {
    paths.push(`M ${BRIEF_X + 14} ${c} H ${TRUNK_IN}`);
    paths.push(`M ${TRUNK_IN} ${firstY} V ${lastY}`);
    paths.push(`M ${TRUNK_OUT} ${firstY} V ${lastY}`);
  }
  for (const { lane, y: rowY } of rows) {
    nodes.push({ id: lane.id, kind: "member", x: AGENT_X, y: rowY, lane, track: { from: { x: TRUNK_IN, y: rowY }, to: { x: AGENT_X - 14, y: rowY } } });
    paths.push(`M ${TRUNK_OUT - 14} ${rowY} H ${TRUNK_OUT}`);
  }

  // The chain on the centre line: each agent's calls sit on the segment that leads into it.
  let prevX = TRUNK_OUT;
  for (const step of CHAIN) {
    const lane = byLane.get(step.id);
    if (!lane) continue;
    nodes.push({ id: step.id, kind: "chain", x: step.x, y: c, lane, track: { from: { x: prevX, y: c }, to: { x: step.x - 14, y: c } } });
    labels.push({ text: step.label, x: step.x, y: c + 26, center: true });
    prevX = step.x + 14;
  }

  // One judge now; older runs had three, stacked with straight elbows.
  const span = 44;
  judges.forEach((lane, i) => {
    const jy = c + (i - (judges.length - 1) / 2) * span;
    const elbow = JUDGE_X - 40;
    if (jy !== c) paths.push(`M ${elbow} ${c} V ${jy}`);
    paths.push(`M ${prevX} ${c} H ${elbow}`);
    nodes.push({ id: lane.id, kind: "chain", x: JUDGE_X, y: jy, lane, track: { from: { x: elbow, y: jy }, to: { x: JUDGE_X - 14, y: jy } } });
    paths.push(`M ${JUDGE_X + 14} ${jy} H ${JUDGE_X + 40} V ${c}`);
  });
  if (judges.length) {
    labels.push({ text: judges.length === 1 ? "Judge" : `Judges · ${judges.length}`, x: JUDGE_X, y: c + (judges.length > 1 ? span + 26 : 26), center: true });
    prevX = JUDGE_X + 40;
  }

  paths.push(`M ${prevX} ${c} H ${PM_X - 14}`);
  nodes.push({ id: "pm", kind: "pm", x: PM_X, y: c });
  labels.push({ text: "You", x: PM_X, y: c + 26, center: true });

  const byId = new Map(nodes.map((n) => [n.id, n]));
  return { nodes, paths, labels, byId, height };
}
