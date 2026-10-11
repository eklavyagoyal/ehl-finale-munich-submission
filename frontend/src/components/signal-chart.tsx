"use client";

import Link from "next/link";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useBudgets } from "@/lib/api/hooks";
import { fmtCount } from "@/lib/format";
import { V } from "@/lib/routes";

const W = 360;
const H = 210;
const PAD = { left: 34, right: 12, top: 12, bottom: 30 };

type Point = { id: string; label: string; complaints: number; budget: number; runId: string | null };

// Frequency vs importance: how often customers complain (real reviews) against how much budget the
// simulated owners would spend on it. One /budgets call; only simulated requirements have a y value.
export function SignalChart({ market }: { market: string | null }) {
  const budgets = useBudgets(market);
  const items = budgets.data?.items ?? [];
  const points: Point[] = items
    .map((b) => {
      const budget = market ? (b.budget_by_market?.[market] ?? b.mean_budget_points_of_100) : b.mean_budget_points_of_100;
      return b.has_budget && budget != null
        ? { id: b.requirement_id, label: b.title.split(":")[0], complaints: b.complaints, budget, runId: b.run_id }
        : null;
    })
    .filter((p): p is Point => p !== null);
  const withoutBudget = items.length - points.length;
  const runs = new Set(points.map((p) => p.runId));
  const maxX = Math.max(5, ...points.map((p) => p.complaints)) * 1.1;
  const maxY = Math.max(40, ...points.map((p) => p.budget)) * 1.1;
  const x = (v: number) => PAD.left + (v / maxX) * (W - PAD.left - PAD.right);
  const y = (v: number) => H - PAD.bottom - (v / maxY) * (H - PAD.top - PAD.bottom);

  return (
    <figure className="flex flex-col gap-1.5">
      <figcaption className="text-xs">
        <span className="font-medium">Frequency vs importance</span>
        <span className="text-muted-foreground"> · complaints from real reviews, budget from simulated owners</span>
      </figcaption>
      <div className="relative" style={{ width: W, height: H }}>
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="absolute inset-0" aria-hidden>
          <g stroke="var(--border)" strokeWidth={1} shapeRendering="crispEdges">
            <line x1={PAD.left} y1={H - PAD.bottom} x2={W - PAD.right} y2={H - PAD.bottom} />
            <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={H - PAD.bottom} />
          </g>
          <g className="fill-muted-foreground text-[10px]" style={{ fontSize: 10 }}>
            <text x={PAD.left} y={H - 8}>
              0
            </text>
            <text x={W - PAD.right} y={H - 8} textAnchor="end">
              complaints →
            </text>
            <text x={PAD.left - 6} y={PAD.top + 8} textAnchor="end">
              {Math.round(maxY)}
            </text>
            <text x={4} y={(H - PAD.bottom + PAD.top) / 2} transform={`rotate(-90 8 ${(H - PAD.bottom + PAD.top) / 2})`} textAnchor="middle">
              budget ↑
            </text>
            <text x={W - PAD.right} y={H - PAD.bottom - 6} textAnchor="end" opacity={0.7}>
              many complaints, little budget
            </text>
          </g>
        </svg>
        {points.map((p) => (
          <HoverCard key={p.id} openDelay={80} closeDelay={60}>
            <HoverCardTrigger asChild>
              <Link
                href={`${V}/decision/${encodeURIComponent(p.id)}/councils`}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-1"
                style={{ left: x(p.complaints), top: y(p.budget) }}
              >
                <span className="size-2.5 rounded-full bg-foreground ring-2 ring-background" />
                <span className="max-w-24 truncate text-[10px] text-muted-foreground">{p.label}</span>
              </Link>
            </HoverCardTrigger>
            <HoverCardContent className="w-64 text-xs">
              <p className="font-medium">{p.label}</p>
              <p className="text-muted-foreground">{p.id}</p>
              <p className="mt-1.5">
                {fmtCount(p.complaints)} complaint reviews · {p.budget.toFixed(0)} of 100 budget points
              </p>
            </HoverCardContent>
          </HoverCard>
        ))}
        {points.length === 0 && (
          <p className="absolute inset-x-10 top-1/2 -translate-y-1/2 text-center text-xs text-muted-foreground">
            {budgets.error
              ? `Could not load the budgets: ${budgets.error instanceof Error ? budgets.error.message : "request failed"}`
              : budgets.isLoading
                ? "Loading…"
                : items.length
                  ? "The simulated requirements have no budget points from owners yet."
                  : "Run the expert pipeline on requirements of this market to see the owners' budget here."}
          </p>
        )}
      </div>
      <p className="max-w-[360px] text-[11px] text-muted-foreground">
        Budget: each owner splits 100 points across the proposals of one run and “keep the price down”
        {runs.size > 1 ? `; these points come from ${runs.size} runs and compare only within a run` : ""}.
        {!market && " All markets: every owner of the requirement counts."}
        {withoutBudget > 0 ? ` ${withoutBudget} simulated without budget points.` : ""}
      </p>
    </figure>
  );
}
