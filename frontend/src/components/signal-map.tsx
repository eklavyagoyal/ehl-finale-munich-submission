"use client";

import { useState } from "react";

import { ErrorState, LoadingRows } from "@/components/states";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useSignalMap } from "@/lib/api/hooks";
import type { MapAxis, MapItem, Quadrant, SignalKind } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

const W = 760;
const H = 340;
const PAD = { left: 40, right: 16, top: 16, bottom: 34 };
const LABELS_PER_QUADRANT = 5;

export const KIND_DOT: Record<SignalKind, string> = {
  pain: "bg-red-500",
  request: "bg-sky-500",
  strength: "bg-emerald-500",
  mixed: "bg-zinc-400",
};

const KIND_LABEL: Record<SignalKind, string> = { pain: "Pain", request: "Wish", strength: "Strength", mixed: "Mixed" };

// Corners as the contract fixes them: act top right, watch top left, protect bottom right, background bottom left.
const CORNER: Record<Quadrant, string> = {
  act: "top-2 right-3 text-right",
  watch: "top-2 left-[48px]",
  protect: "bottom-10 right-3 text-right",
  background: "bottom-10 left-[48px]",
};

// Every signal of the market on one four-field map: reviews (x, log) against the share of problems and
// wishes (y). Axes, thresholds and quadrants come from the API; clicking a dot opens the signal.
export function SignalMap({ market, onOpen }: { market: string | null; onOpen: (featureKey: string) => void }) {
  const { data, error, isLoading } = useSignalMap(market);
  const [hover, setHover] = useState<MapItem | null>(null);

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows rows={4} />;

  const { x: ax, y: ay } = data.axes;
  const reviews = data.items.map((i) => i.reviews);
  const xmin = Math.max(1, Math.min(ax.threshold, ...reviews) / 1.6);
  const xmax = Math.max(ax.threshold * 2, ...reviews) * 1.25;
  const lx = (v: number) => Math.log10(Math.max(v, xmin));
  const x = (v: number) => PAD.left + ((lx(v) - lx(xmin)) / (lx(xmax) - lx(xmin))) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - Math.min(1, Math.max(0, v))) * (H - PAD.top - PAD.bottom);
  const pct = (v: number, of: number) => `${(v / of) * 100}%`;

  // Only the biggest signals in Act and Protect carry a text label; everything else shows on hover.
  const labelled = new Set(
    (["act", "protect"] as Quadrant[]).flatMap((q) =>
      data.items
        .filter((i) => i.quadrant === q)
        .sort((a, b) => b.reviews - a.reviews)
        .slice(0, LABELS_PER_QUADRANT)
        .map((i) => i.feature_key),
    ),
  );

  return (
    <figure className="flex flex-col gap-2">
      <div className="relative w-full max-w-[760px]" style={{ aspectRatio: `${W} / ${H}` }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
          <g stroke="var(--border)" strokeWidth={1} shapeRendering="crispEdges" fill="none">
            <line x1={PAD.left} y1={H - PAD.bottom} x2={W - PAD.right} y2={H - PAD.bottom} />
            <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={H - PAD.bottom} />
            <line x1={x(ax.threshold)} y1={PAD.top} x2={x(ax.threshold)} y2={H - PAD.bottom} strokeDasharray="3 4" />
            <line x1={PAD.left} y1={y(ay.threshold)} x2={W - PAD.right} y2={y(ay.threshold)} strokeDasharray="3 4" />
          </g>
          <g className="fill-muted-foreground" style={{ fontSize: 10 }}>
            {[1, 10, 100, 1000, 10000].filter((t) => t >= xmin && t <= xmax).map((t) => (
              <text key={t} x={x(t)} y={H - PAD.bottom + 14} textAnchor="middle">
                {fmtCount(t)}
              </text>
            ))}
            <text x={PAD.left - 6} y={y(1) + 4} textAnchor="end">
              100 %
            </text>
            <text x={PAD.left - 6} y={y(0) + 4} textAnchor="end">
              0
            </text>
          </g>
        </svg>

        <AxisLabel axis={ax} className="right-3 bottom-0" />
        <AxisLabel axis={ay} className="top-0 left-0 -translate-y-full" />

        {data.quadrants.map((q) => (
          <HoverCard key={q.key} openDelay={100} closeDelay={60}>
            <HoverCardTrigger asChild>
              <span className={cn("absolute cursor-default text-[11px] text-muted-foreground", CORNER[q.key])}>
                <span className="font-medium text-foreground/80">{q.label}</span> <span className="tabular-nums">{q.signals}</span>
              </span>
            </HoverCardTrigger>
            <HoverCardContent className="w-60 text-xs">{q.hint}</HoverCardContent>
          </HoverCard>
        ))}

        {data.items.map((item) => (
          <button
            key={item.feature_key}
            type="button"
            onClick={() => onOpen(item.feature_key)}
            onMouseEnter={() => setHover(item)}
            onMouseLeave={() => setHover((h) => (h?.feature_key === item.feature_key ? null : h))}
            onFocus={() => setHover(item)}
            onBlur={() => setHover(null)}
            aria-label={`${item.label}: ${item.reviews} reviews, ${Math.round(item.need_share * 100)} % problems or wishes`}
            className="absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-1"
            style={{ left: pct(x(item.reviews), W), top: pct(y(item.need_share), H) }}
          >
            <span
              className={cn(
                "size-2.5 rounded-full",
                KIND_DOT[item.kind],
                item.requirement_ids.length > 0 && "ring-2 ring-foreground/70 ring-offset-1 ring-offset-background",
              )}
            />
            {labelled.has(item.feature_key) && <span className="max-w-28 truncate text-[10px] text-muted-foreground">{item.label}</span>}
          </button>
        ))}

        {hover && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+10px)] rounded-md border bg-popover px-2.5 py-1.5 text-xs shadow-sm"
            style={{ left: pct(x(hover.reviews), W), top: pct(y(hover.need_share), H) }}
          >
            <p className="font-medium whitespace-nowrap">{hover.label}</p>
            <p className="whitespace-nowrap text-muted-foreground tabular-nums">
              {fmtCount(hover.reviews)} reviews · {Math.round(hover.need_share * 100)} % problems or wishes
            </p>
          </div>
        )}
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        {(Object.keys(KIND_DOT) as SignalKind[]).map((k) => (
          <span key={k} className="flex items-center gap-1">
            <span className={cn("size-2 rounded-full", KIND_DOT[k])} aria-hidden />
            {KIND_LABEL[k]}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full ring-2 ring-foreground/70 ring-offset-1 ring-offset-background" aria-hidden />
          has a requirement
        </span>
        {data.hidden_below_min_reviews ? <span>· {data.hidden_below_min_reviews} signals under 5 reviews hidden</span> : null}
      </figcaption>
    </figure>
  );
}

function AxisLabel({ axis, className }: { axis: MapAxis; className?: string }) {
  return (
    <HoverCard openDelay={100} closeDelay={60}>
      <HoverCardTrigger asChild>
        <span className={cn("absolute cursor-default text-[11px] text-muted-foreground underline decoration-dotted underline-offset-2", className)}>
          {axis.label}
          {axis.scale === "log" ? " (log)" : ""}
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="w-64 text-xs">{axis.hint}</HoverCardContent>
    </HoverCard>
  );
}
