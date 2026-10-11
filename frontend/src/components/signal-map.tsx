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
const PAD = { left: 58, right: 16, top: 26, bottom: 34 };
const JITTER_PX = 3;
const LABELS_PER_QUADRANT = 5;

export const KIND_DOT: Record<SignalKind, string> = {
  pain: "bg-red-500",
  request: "bg-sky-500",
  strength: "bg-emerald-500",
  mixed: "bg-zinc-400",
};

const KIND_LABEL: Record<SignalKind, string> = { pain: "Pain", request: "Wish", strength: "Strength", mixed: "Mixed" };


// Every signal of the market on one four-field map: reviews (x, log) against the share of problems and
// wishes (y). Axes, thresholds and quadrants come from the API; clicking a dot opens the signal.
export function SignalMap({ market, selected, onSelect }: { market: string | null; selected: Set<string>; onSelect: (item: MapItem) => void }) {
  const [showAll, setShowAll] = useState(false);
  const { data, error, isLoading } = useSignalMap(market, showAll ? 1 : undefined);
  const [hover, setHover] = useState<MapItem | null>(null);

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows rows={4} />;

  const { x: ax, y: ay } = data.axes;
  const reviews = data.items.map((i) => i.reviews);
  const xmin = Math.max(1, Math.min(ax.threshold / 4, ...reviews) / 1.2);
  const xmax = Math.max(ax.threshold * 4, ...reviews) * 1.2;
  const lx = (v: number) => Math.log10(Math.max(v, xmin));
  const left = PAD.left;
  const right = W - PAD.right;
  const top = PAD.top;
  const bottom = H - PAD.bottom;
  const midX = (left + right) / 2;
  const midY = (top + bottom) / 2;
  // centre_on_threshold: a piecewise scale puts the threshold exactly in the middle, so the cross is centred.
  const x = (v: number) => {
    if (!ax.center_on_threshold) return left + ((lx(v) - lx(xmin)) / (lx(xmax) - lx(xmin))) * (right - left);
    return v <= ax.threshold
      ? left + ((lx(v) - lx(xmin)) / (lx(ax.threshold) - lx(xmin))) * (midX - left)
      : midX + ((lx(Math.min(v, xmax)) - lx(ax.threshold)) / (lx(xmax) - lx(ax.threshold))) * (right - midX);
  };
  const y = (v: number) => {
    const c = Math.min(1, Math.max(0, v));
    if (!ay.center_on_threshold) return top + (1 - c) * (bottom - top);
    return c <= ay.threshold ? bottom - (c / ay.threshold) * (bottom - midY) : midY - ((c - ay.threshold) / (1 - ay.threshold)) * (midY - top);
  };
  const pct = (v: number, of: number) => `${(v / of) * 100}%`;
  // Dots that would sit on top of each other spread by at most 3 px, the same way every time.
  const seen = new Map<string, number>();
  const jitter = new Map(
    data.items.map((i) => {
      const cell = `${Math.round(x(i.reviews) / 4)}|${Math.round(y(i.need_share) / 4)}`;
      const k = seen.get(cell) ?? 0;
      seen.set(cell, k + 1);
      return [i.feature_key, k === 0 ? [0, 0] : [Math.cos(k * 2.4) * JITTER_PX, Math.sin(k * 2.4) * JITTER_PX]] as const;
    }),
  );

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
      <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
          <g stroke="var(--border)" strokeWidth={1} shapeRendering="crispEdges" fill="none">
            <line x1={left} y1={bottom} x2={right} y2={bottom} />
            <line x1={left} y1={top} x2={left} y2={bottom} />
            <line x1={x(ax.threshold)} y1={top} x2={x(ax.threshold)} y2={bottom} />
            <line x1={left} y1={y(ay.threshold)} x2={right} y2={y(ay.threshold)} />
          </g>
          <g className="fill-muted-foreground" style={{ fontSize: 10 }}>
            {[1, 10, 100, 1000, 10000, ax.threshold]
              .filter((t, i, all) => t >= xmin && t <= xmax && all.indexOf(t) === i)
              .filter((t) => x(t) > left + 60 && x(t) < right - 60)
              .map((t) => (
                <text key={t} x={x(t)} y={bottom + 14} textAnchor="middle">
                  {fmtCount(t)}
                </text>
              ))}
            {/* The four sides say what low and high mean. */}
            <text x={left} y={bottom + 14} textAnchor="start">
              {ax.low_label ?? ""}
            </text>
            <text x={right} y={bottom + 14} textAnchor="end">
              {ax.high_label ?? ""}
            </text>
            <text x={12} y={(midY + bottom) / 2} transform={`rotate(-90 12 ${(midY + bottom) / 2})`} textAnchor="middle">
              {ay.low_label ?? ""}
            </text>
            <text x={12} y={(top + midY) / 2} transform={`rotate(-90 12 ${(top + midY) / 2})`} textAnchor="middle">
              {ay.high_label ?? ""}
            </text>
            <text x={left - 6} y={y(1) + 4} textAnchor="end">
              100 %
            </text>
            <text x={left - 6} y={y(ay.threshold) + 4} textAnchor="end">
              {Math.round(ay.threshold * 100)} %
            </text>
            <text x={left - 6} y={y(0) + 4} textAnchor="end">
              0
            </text>
          </g>
        </svg>

        <AxisLabel axis={ax} style={{ left: "50%", bottom: 0, transform: "translateX(-50%)" }} />
        <AxisLabel axis={ay} style={{ left: pct(PAD.left, W), top: 0 }} />

        {data.quadrants.map((q) => (
          <HoverCard key={q.key} openDelay={100} closeDelay={60}>
            <HoverCardTrigger asChild>
              <span
                className={cn("absolute cursor-default text-[11px] text-muted-foreground", (q.key === "act" || q.key === "protect") && "text-right")}
                // Corners as the contract fixes them: act top right, watch top left, protect bottom right, background bottom left.
                style={{
                  ...(q.key === "act" || q.key === "protect" ? { right: pct(PAD.right + 6, W) } : { left: pct(PAD.left + 8, W) }),
                  ...(q.key === "act" || q.key === "watch" ? { top: pct(PAD.top + 4, H) } : { bottom: pct(PAD.bottom + 4, H) }),
                }}
              >
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
            onClick={() => onSelect(item)}
            aria-pressed={selected.has(item.feature_key)}
            onMouseEnter={() => setHover(item)}
            onMouseLeave={() => setHover((h) => (h?.feature_key === item.feature_key ? null : h))}
            onFocus={() => setHover(item)}
            onBlur={() => setHover(null)}
            aria-label={`${item.label}: ${item.reviews} reviews, ${Math.round(item.need_share * 100)} % problems or wishes`}
            className="absolute flex items-center gap-1"
            style={{
              left: pct(x(item.reviews), W),
              top: pct(y(item.need_share), H),
              transform: `translate(calc(-50% + ${jitter.get(item.feature_key)?.[0] ?? 0}px), calc(-50% + ${jitter.get(item.feature_key)?.[1] ?? 0}px))`,
            }}
          >
            <span
              className={cn(
                "size-2.5 rounded-full",
                KIND_DOT[item.kind],
                item.requirement_ids.length > 0 && "outline outline-1 outline-offset-2 outline-foreground/50",
                selected.has(item.feature_key) && "ring-[3px] ring-blue-600/80 ring-offset-1 ring-offset-background",
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
              {fmtCount(hover.reviews)} reviews · {Math.round((hover.need_share_raw ?? hover.need_share) * 100)} % problems or wishes
              {hover.need_share_raw != null && Math.round(hover.need_share_raw * 100) !== Math.round(hover.need_share * 100)
                ? ` (plotted at ${Math.round(hover.need_share * 100)} %)`
                : ""}
            </p>
          </div>
        )}
      </div>
      {data.hidden_below_min_reviews || showAll ? (
        <figcaption className="text-[11px] text-muted-foreground">
          {showAll ? "Showing every signal, also those under 5 reviews. " : `${data.hidden_below_min_reviews} signals under 5 reviews hidden. `}
          <button type="button" onClick={() => setShowAll((v) => !v)} className="underline-offset-2 hover:text-foreground hover:underline">
            {showAll ? "Hide them" : "Show them"}
          </button>
        </figcaption>
      ) : null}
    </figure>
  );
}

// Dot colours and rings, shown small at the bottom of the Signals page.
export function MapLegend() {
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
      Dots:
      {(Object.keys(KIND_DOT) as SignalKind[]).map((k) => (
        <span key={k} className="flex items-center gap-1">
          <span className={cn("size-2 rounded-full", KIND_DOT[k])} aria-hidden />
          {KIND_LABEL[k]}
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span className="size-2 rounded-full outline outline-1 outline-offset-2 outline-foreground/50" aria-hidden />
        has a requirement
      </span>
      <span className="flex items-center gap-1">
        <span className="size-2 rounded-full ring-[3px] ring-blue-600/80" aria-hidden />
        selected
      </span>
    </span>
  );
}

function AxisLabel({ axis, style }: { axis: MapAxis; style: React.CSSProperties }) {
  return (
    <HoverCard openDelay={100} closeDelay={60}>
      <HoverCardTrigger asChild>
        <span className="absolute cursor-default text-[11px] text-muted-foreground underline decoration-dotted underline-offset-2" style={style}>
          {axis.label}
          {axis.scale === "log" ? " (log)" : ""}
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="w-64 text-xs">{axis.hint}</HoverCardContent>
    </HoverCard>
  );
}
