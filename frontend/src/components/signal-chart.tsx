"use client";

import Link from "next/link";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useCouncils, useRequirements, useSignals } from "@/lib/api/hooks";
import type { Council, Requirement } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";

const W = 360;
const H = 210;
const PAD = { left: 34, right: 12, top: 12, bottom: 30 };

type Point = { requirement: Requirement; label: string; complaints: number; budget: number; owners: number; runId: string | null };

// Mean budget of the owners that count for this view: one market, or every owner for "All".
function budgetOf(council: Council, market: string | null): { budget: number; owners: number } | null {
  const markets = Object.entries(council.customers?.by_market ?? {}).filter(([m]) => !market || m === market);
  let points = 0;
  let owners = 0;
  for (const [, m] of markets) {
    const b = m.summary.mean_budget_points_of_100;
    if (b == null) continue;
    points += b * m.summary.personas;
    owners += m.summary.personas;
  }
  return owners ? { budget: points / owners, owners } : null;
}

// Frequency vs importance: how often customers complain (real reviews) against how much budget the
// simulated owners would spend on it. Only requirements that went through the expert pipeline have a y value.
export function SignalChart({ market }: { market: string | null }) {
  const { data: requirements } = useRequirements();
  const signals = useSignals(market, "all", 100);
  // In a market view a requirement belongs to that market; in "All" every simulated requirement counts.
  const simulated = (requirements ?? []).filter((r) => r.last_run_id && r.feature_key && (!market || r.market === market));
  const councils = useCouncils(simulated.map((r) => r.id));
  const complaintsBy = new Map((signals.data?.items ?? []).map((s) => [s.feature_key, s]));

  const points: Point[] = [];
  for (const r of simulated) {
    const council = councils.data?.byId.get(r.id);
    const signal = complaintsBy.get(r.feature_key!);
    const b = council && budgetOf(council, market);
    if (!signal || !b) continue;
    points.push({ requirement: r, label: signal.label, complaints: signal.pain, budget: b.budget, owners: b.owners, runId: council!.run_id });
  }
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
          <HoverCard key={p.requirement.id} openDelay={80} closeDelay={60}>
            <HoverCardTrigger asChild>
              <Link
                href={`/requirements/${encodeURIComponent(p.requirement.id)}/councils`}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-1"
                style={{ left: x(p.complaints), top: y(p.budget) }}
              >
                <span className="size-2.5 rounded-full bg-foreground ring-2 ring-background" />
                <span className="max-w-24 truncate text-[10px] text-muted-foreground">{p.label}</span>
              </Link>
            </HoverCardTrigger>
            <HoverCardContent className="w-64 text-xs">
              <p className="font-medium">{p.label}</p>
              <p className="text-muted-foreground">{p.requirement.id}</p>
              <p className="mt-1.5">
                {fmtCount(p.complaints)} complaint reviews · {p.budget.toFixed(0)} of 100 budget points ({p.owners} owners)
              </p>
            </HoverCardContent>
          </HoverCard>
        ))}
        {points.length === 0 && (
          <p className="absolute inset-x-10 top-1/2 -translate-y-1/2 text-center text-xs text-muted-foreground">
            {councils.error || signals.error
              ? `Could not load the councils: ${(councils.error ?? signals.error) instanceof Error ? (councils.error ?? signals.error).message : "request failed"}`
              : councils.isLoading || signals.isLoading
                ? "Loading…"
                : simulated.length
                  ? "The simulated requirements have no budget points from owners yet."
                  : "Run the expert pipeline on requirements of this market to see the owners' budget here."}
          </p>
        )}
      </div>
      <p className="max-w-[360px] text-[11px] text-muted-foreground">
        Budget: each owner splits 100 points across the proposals of one run and “keep the price down”
        {runs.size > 1 ? `; these points come from ${runs.size} runs and compare only within a run` : ""}.
        {!market && " All markets: every owner of the requirement counts."}
        {councils.data?.failed ? ` ${councils.data.failed} council${councils.data.failed === 1 ? "" : "s"} could not be loaded.` : ""}
      </p>
    </figure>
  );
}
