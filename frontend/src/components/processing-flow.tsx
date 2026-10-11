"use client";

import { useState } from "react";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { evidenceFactors } from "@/components/weights-panel";
import { useWeights } from "@/lib/api/hooks";
import type { FlowNode, ProcessingFlow } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

const W = 1000;
const H = 360;
const NODE_W = 8;
const GAP = 10;
// Every node keeps room for its two-line label, also when its band is thin or empty.
const MIN_SLOT = 34;
const PAD_Y = 12;
const X0 = 30;
const X1 = 880;
// Column of a node without incoming links (sources, and empty end points such as "Change coming" before
// anything is approved). Linked nodes sit one column right of their furthest source.
const COLUMN_HINT: Record<string, number> = {
  bmw: 0, online: 0, social: 0, competitors: 0,
  excluded: 1, not_relevant: 1, bmw_labels: 1, ai_labeler: 1, no_topic: 1, target: 1, other_models: 1, competitor: 1, brand: 1,
  signals: 2, findings: 3, requirements: 4, change_coming: 5, declined: 5, open: 5,
};

const NODE_COLOR: Record<string, string> = {
  bmw: "fill-foreground/70",
  online: "fill-foreground/70",
  social: "fill-foreground/70",
  competitors: "fill-foreground/70",
  not_relevant: "fill-red-400",
  target: "fill-foreground/80",
  requirements: "fill-foreground/80",
  change_coming: "fill-emerald-600",
  declined: "fill-red-400",
  open: "fill-muted-foreground/60",
  bmw_labels: "fill-emerald-600",
  ai_labeler: "fill-sky-600",
  no_topic: "fill-amber-500",
  excluded: "fill-red-400",
  signals: "fill-foreground/80",
  findings: "fill-foreground/80",
};

type Placed = FlowNode & { col: number; x: number; y: number; h: number; value: number };

// Processing as one flow: sources split into BMW labels, our AI labeler and "no topic"; the labelled reviews
// flow into signals and part of them into findings. Band width = reviews. Hint on hover, detail on click.
export function ProcessingFlowChart({ flow }: { flow: ProcessingFlow }) {
  const [open, setOpen] = useState<string | null>(null);
  const [hoverLink, setHoverLink] = useState<number | null>(null);
  const { nodes, links, scale, columnCount } = layout(flow);
  const { data: weights } = useWeights();
  const openNode = nodes.find((n) => n.key === open);

  return (
    <div className="flex flex-col gap-4">
      <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full">
          <g>
            {links.map((l, i) => (
              <path
                key={i}
                d={l.d}
                className={cn("fill-foreground/[0.07] transition-colors", hoverLink === i && "fill-foreground/[0.16]")}
                onMouseEnter={() => setHoverLink(i)}
                onMouseLeave={() => setHoverLink(null)}
              >
                <title>{`${l.sourceLabel} → ${l.targetLabel}: ${fmtCount(l.value)} ${flow.link_unit ?? "reviews"}`}</title>
              </path>
            ))}
          </g>
          {nodes.map((n) =>
            n.value === 0 ? (
              // Nothing has flowed here yet: an empty end point, still labelled.
              <circle key={n.key} cx={n.x + NODE_W / 2} cy={n.y} r={4} className="fill-background stroke-muted-foreground/60" strokeWidth={1.2} />
            ) : (
              <rect key={n.key} x={n.x} y={n.y} width={NODE_W} height={Math.max(n.h, 2)} rx={1.5} className={NODE_COLOR[n.key] ?? "fill-foreground/60"} />
            ),
          )}
        </svg>

        {nodes.map((n) => {
          const last = n.col === columnCount - 1;
          return (
            <HoverCard key={n.key} openDelay={100} closeDelay={60}>
              <HoverCardTrigger asChild>
                <button
                  type="button"
                  onClick={() => setOpen((o) => (o === n.key ? null : n.key))}
                  aria-expanded={open === n.key}
                  className={cn(
                    "absolute flex -translate-y-1/2 flex-col text-left leading-tight",
                    last ? "-translate-x-full items-end pr-2 text-right" : "pl-3",
                  )}
                  style={{ left: `${((last ? n.x : n.x + NODE_W) / W) * 100}%`, top: `${((n.y + Math.max(n.h, 2) / 2) / H) * 100}%` }}
                >
                  <span className={cn("text-[13px] font-medium tabular-nums", open === n.key && "underline underline-offset-4")}>{fmtCount(n.count)}</span>
                  <span className="text-xs text-muted-foreground">{n.label}</span>
                  {n.weight && <span className="text-[10px] text-muted-foreground/70 tabular-nums">{n.weight}</span>}
                </button>
              </HoverCardTrigger>
              <HoverCardContent className="w-64 text-xs">
                <p>{n.hint}</p>
                {n.weight && evidenceFactors(weights, n.key) && <p className="mt-1.5 text-muted-foreground">{evidenceFactors(weights, n.key)}</p>}
              </HoverCardContent>
            </HoverCard>
          );
        })}
      </div>
      <p className="text-[11px] text-muted-foreground">
        Band width = {flow.link_unit ?? "reviews"}
        {1 / scale >= 2 ? ` (1 px ≈ ${fmtCount(Math.round(1 / scale))})` : ""}.
        {flow.triage &&
          ` Triage: ${fmtCount(flow.triage.triaged)} online reviews checked, ${fmtCount(flow.triage.flagged)} flagged, filter ${flow.triage.filter_enabled ? "on" : "off"}.`}
      </p>
      {openNode && <p className="max-w-2xl text-[13px] text-foreground/80">{openNode.detail}</p>}
    </div>
  );
}

function layout(flow: ProcessingFlow) {
  const keys = new Set(flow.nodes.map((n) => n.key));
  const incoming = new Map<string, string[]>();
  for (const l of flow.links) if (keys.has(l.source) && keys.has(l.target)) incoming.set(l.target, [...(incoming.get(l.target) ?? []), l.source]);
  const colOf = new Map<string, number>();
  const column = (key: string, seen = new Set<string>()): number => {
    if (colOf.has(key)) return colOf.get(key)!;
    const sources = (incoming.get(key) ?? []).filter((k) => !seen.has(k));
    const col = sources.length ? Math.max(...sources.map((k) => column(k, new Set([...seen, key])))) + 1 : (COLUMN_HINT[key] ?? 0);
    colOf.set(key, col);
    return col;
  };
  // The backend's explicit column wins; the longest-path depth is the fallback.
  flow.nodes.forEach((n) => (typeof n.column === "number" ? colOf.set(n.key, n.column) : column(n.key)));
  const columnCount = Math.max(1, ...colOf.values()) + 1;
  const columnX = (i: number) => (columnCount === 1 ? X0 : X0 + (i * (X1 - X0)) / (columnCount - 1));
  const columns = Array.from({ length: columnCount }, (_, i) => flow.nodes.filter((n) => colOf.get(n.key) === i));
  const inSum = new Map<string, number>();
  const outSum = new Map<string, number>();
  for (const l of flow.links) {
    outSum.set(l.source, (outSum.get(l.source) ?? 0) + l.value);
    inSum.set(l.target, (inSum.get(l.target) ?? 0) + l.value);
  }
  // A node is as tall as the reviews that pass through it; source nodes without links fall back to their count.
  const value = (n: FlowNode) => Math.max(inSum.get(n.key) ?? 0, outSum.get(n.key) ?? 0, n.unit === (flow.link_unit ?? "reviews") ? n.count : 0);
  // Largest scale at which every column fits, counting the minimum slot of thin nodes.
  const fits = (k: number) =>
    columns.every((col) => col.reduce((t, n) => t + Math.max(value(n) * k, MIN_SLOT), 0) + Math.max(0, col.length - 1) * GAP <= H - 2 * PAD_Y);
  let scale = Math.min(...columns.filter((c) => c.length).map((c) => (H - 2 * PAD_Y) / Math.max(1, c.reduce((t, n) => t + value(n), 0))));
  for (let i = 0; i < 40 && !fits(scale); i++) scale *= 0.9;

  const placed = new Map<string, Placed>();
  columns.forEach((col, ci) => {
    const slots = col.map((n) => Math.max(value(n) * scale, MIN_SLOT));
    const total = slots.reduce((t, h) => t + h, 0) + Math.max(0, col.length - 1) * GAP;
    let y = Math.max(PAD_Y, (H - total) / 2);
    col.forEach((n, i) => {
      const h = value(n) * scale;
      // A thin node sits in the middle of its slot; an empty one is a point there.
      const top = y + (slots[i] - h) / 2;
      placed.set(n.key, { ...n, col: ci, x: columnX(ci), y: value(n) === 0 ? y + slots[i] / 2 : top, h, value: value(n) });
      y += slots[i] + GAP;
    });
  });

  // Stack bands at both ends in the order of the opposite node, so they do not cross more than needed.
  const outOffset = new Map<string, number>();
  const inOffset = new Map<string, number>();
  const sorted = [...flow.links].filter((l) => placed.has(l.source) && placed.has(l.target))
    .sort((a, b) => placed.get(a.source)!.y - placed.get(b.source)!.y || placed.get(a.target)!.y - placed.get(b.target)!.y);
  const links = sorted.map((l) => {
    const s = placed.get(l.source)!;
    const t = placed.get(l.target)!;
    const w = l.value * scale;
    const sy = s.y + (outOffset.get(s.key) ?? 0);
    const ty = t.y + (inOffset.get(t.key) ?? 0);
    outOffset.set(s.key, (outOffset.get(s.key) ?? 0) + w);
    inOffset.set(t.key, (inOffset.get(t.key) ?? 0) + w);
    const x0 = s.x + NODE_W;
    const x1 = t.x;
    const mx = (x0 + x1) / 2;
    const d = `M ${x0} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${x1} ${ty} L ${x1} ${ty + w} C ${mx} ${ty + w}, ${mx} ${sy + w}, ${x0} ${sy + w} Z`;
    return { d, value: l.value, sourceLabel: s.label, targetLabel: t.label };
  });
  return { nodes: [...placed.values()], links, scale, columnCount };
}
