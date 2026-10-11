"use client";

import { useState } from "react";

import { ErrorState, LoadingRows } from "@/components/states";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useSignalMap } from "@/lib/api/hooks";
import type { MapItem, Quadrant, SignalKind } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

const W = 1000;
const H = 460;
// Symmetric padding: the cross sits exactly in the middle of the figure.
const PAD = 24;
const JITTER_PX = 3;
const LABELS_PER_QUADRANT = 5;

export const KIND_DOT: Record<SignalKind, string> = {
  pain: "bg-red-500",
  request: "bg-sky-500",
  strength: "bg-emerald-500",
  mixed: "bg-zinc-400",
};

const KIND_LABEL: Record<SignalKind, string> = { pain: "Pain", request: "Wish", strength: "Strength", mixed: "Mixed" };


// Every signal of the market on one 2×2 map, like a consulting slide: a cross exactly in the middle, what low
// and high mean at the four arm ends, the field names inside the fields. No ticks, no percentages; numbers on
// hover. The piecewise scale (center_on_threshold) puts the API's thresholds on the cross.
export function SignalMap({
  market,
  selected,
  onSelect,
  showAll = false,
}: {
  market: string | null;
  selected: Set<string>;
  onSelect: (item: MapItem) => void;
  showAll?: boolean;
}) {
  const { data, error, isLoading } = useSignalMap(market, showAll ? 1 : undefined);
  const [hover, setHover] = useState<MapItem | null>(null);

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows rows={4} />;

  const { x: ax, y: ay } = data.axes;
  const reviews = data.items.map((i) => i.reviews);
  const xmin = Math.max(1, Math.min(ax.threshold / 4, ...reviews) / 1.2);
  const xmax = Math.max(ax.threshold * 4, ...reviews) * 1.2;
  const lx = (v: number) => Math.log10(Math.max(v, xmin));
  const left = PAD;
  const right = W - PAD;
  const top = PAD;
  const bottom = H - PAD;
  const midX = W / 2;
  const midY = H / 2;
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
    <figure className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }}>
      <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 size-full" aria-hidden>
        <g className="stroke-foreground/25" strokeWidth={1} shapeRendering="crispEdges">
          <line x1={left} y1={midY} x2={right} y2={midY} />
          <line x1={midX} y1={top} x2={midX} y2={bottom} />
        </g>
      </svg>

      {/* What low and high mean, at the four ends of the cross. */}
      <ArmLabel style={{ right: pct(PAD, W), top: pct(midY, H), transform: "translateY(-120%)" }}>{ax.high_label ?? "Many reviews"} →</ArmLabel>
      <ArmLabel style={{ left: pct(PAD, W), top: pct(midY, H), transform: "translateY(-120%)" }}>← {ax.low_label ?? "Few reviews"}</ArmLabel>
      <ArmLabel style={{ left: pct(midX, W), top: pct(PAD, H), transform: "translateX(8px)" }}>↑ {ay.high_label ?? "Mostly problems & wishes"}</ArmLabel>
      <ArmLabel style={{ left: pct(midX, W), bottom: pct(PAD, H), transform: "translateX(8px)" }}>↓ {ay.low_label ?? "Mostly praise"}</ArmLabel>

      {/* Field names inside the fields, in their outer corners: act top right, watch top left, protect bottom right, background bottom left. */}
      {data.quadrants.map((q) => {
        const isRight = q.key === "act" || q.key === "protect";
        const isTop = q.key === "act" || q.key === "watch";
        return (
          <HoverCard key={q.key} openDelay={100} closeDelay={60}>
            <HoverCardTrigger asChild>
              <span
                className={cn("absolute flex cursor-default flex-col leading-tight", isRight && "items-end text-right")}
                style={{
                  ...(isRight ? { right: pct(PAD + 18, W) } : { left: pct(PAD + 18, W) }),
                  ...(isTop ? { top: pct(PAD + 34, H) } : { bottom: pct(PAD + 34, H) }),
                }}
              >
                <span className="text-lg font-semibold tracking-tight text-foreground/25">{q.label}</span>
                <span className="text-xs text-muted-foreground/70 tabular-nums">{q.signals} signals</span>
              </span>
            </HoverCardTrigger>
            <HoverCardContent className="w-60 text-xs">{q.hint}</HoverCardContent>
          </HoverCard>
        );
      })}

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
          </p>
        </div>
      )}
    </figure>
  );
}

function ArmLabel({ style, children }: { style: React.CSSProperties; children: React.ReactNode }) {
  return (
    <span className="absolute text-[11px] whitespace-nowrap text-muted-foreground" style={style}>
      {children}
    </span>
  );
}

// How many signals the map hides under 5 reviews, with a switch; shown small at the bottom of the page.
export function HiddenSignalsNote({ market, showAll, onToggle }: { market: string | null; showAll: boolean; onToggle: () => void }) {
  const { data } = useSignalMap(market, showAll ? 1 : undefined);
  if (!data || (!data.hidden_below_min_reviews && !showAll)) return null;
  return (
    <span>
      {showAll ? "The map shows every signal, also those under 5 reviews. " : `${data.hidden_below_min_reviews} signals under 5 reviews are hidden on the map. `}
      <button type="button" onClick={onToggle} className="underline-offset-2 hover:text-foreground hover:underline">
        {showAll ? "Hide them" : "Show them"}
      </button>
    </span>
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
