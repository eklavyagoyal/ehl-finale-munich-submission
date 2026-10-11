"use client";

import Link from "next/link";

import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { useDecisionsOverview } from "@/lib/api/hooks";
import type { DecisionsOverview } from "@/lib/api/types";
import { actorLabel, fmtCount, fmtDateTime, fmtRange, humanize, statusTone } from "@/lib/format";
import { V } from "@/lib/routes";
import { cn } from "cn";

// The start page is about decisions: how far each vehicle got, what waits for the PM, what was decided.
export default function OverviewPage() {
  const { data, error, isLoading } = useDecisionsOverview();
  return (
    <div className="flex max-w-6xl flex-col gap-10 py-8">
      <h1 className="text-[13px] font-medium text-muted-foreground">Overview</h1>
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && (
        <>
          <Vehicles vehicles={data.vehicles} />
          <div className="grid gap-10 lg:grid-cols-2">
            <NeedsDecision items={data.needs_decision} />
            <RecentDecisions items={data.recent_decisions} agreement={data.agreement_with_ai} />
          </div>
        </>
      )}
    </div>
  );
}

const GRID = "grid-cols-[minmax(0,1.4fr)_72px_96px_80px_minmax(0,1fr)_minmax(0,1.3fr)_120px]";

function Vehicles({ vehicles }: { vehicles: DecisionsOverview["vehicles"] }) {
  return (
    <section className="overflow-x-auto">
      <div className="min-w-[820px]">
        <div className={cn("grid gap-4 border-b px-2 pb-2.5 text-xs text-muted-foreground", GRID)}>
          <span>Vehicle</span>
          <span className="text-right">Signals</span>
          <span className="text-right">Requirements</span>
          <span className="text-right">Councils</span>
          <span>AI suggests</span>
          <span>Decisions</span>
          <span>Last activity</span>
        </div>
        {vehicles.map((v) => {
          const active = v.status === "active";
          const row = (
            <>
              <span className="truncate">
                <span className="font-medium">{v.code}</span> <span className="text-muted-foreground">· {v.name.replace(/^BMW /, "")}</span>
              </span>
              <span className="text-right tabular-nums">{active ? fmtCount(v.signals) : "–"}</span>
              <span className="text-right tabular-nums">{active ? fmtCount(v.requirements) : "–"}</span>
              <span className="text-right tabular-nums">{active ? fmtCount(v.councils_run) : "–"}</span>
              {/* Advice, not a decision: muted text. */}
              <span className="truncate text-[13px] text-muted-foreground">
                {active
                  ? Object.entries(v.ai_suggests)
                      .map(([k, n]) => `${n} ${humanize(k).toLowerCase()}`)
                      .join(" · ") || "–"
                  : "coming"}
              </span>
              <span className="flex flex-wrap gap-x-3 text-[13px]">
                {active ? (
                  <>
                    <span>
                      <span className="tabular-nums">{v.decisions.change_coming}</span> <span className="text-muted-foreground">change coming</span>
                    </span>
                    <span>
                      <span className="tabular-nums">{v.decisions.declined}</span> <span className="text-muted-foreground">declined</span>
                    </span>
                    <span>
                      <span className="tabular-nums">{v.decisions.open}</span> <span className="text-muted-foreground">open</span>
                    </span>
                  </>
                ) : null}
              </span>
              <span className="text-xs text-muted-foreground">{v.last_activity ? fmtDateTime(v.last_activity) : "–"}</span>
            </>
          );
          const cls = cn("grid items-center gap-4 border-b border-border/60 px-2 py-3 text-sm", GRID);
          return active ? (
            <Link key={v.entity_id} href={V} className={cn(cls, "hover:bg-muted/40")}>
              {row}
            </Link>
          ) : (
            <div key={v.entity_id} className={cn(cls, "opacity-50")}>
              {row}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function NeedsDecision({ items }: { items: DecisionsOverview["needs_decision"] }) {
  return (
    <section className="flex flex-col">
      <h2 className="flex items-baseline gap-2 border-b px-2 pb-2.5 text-[13px] font-medium">
        Needs your decision <span className="font-normal text-muted-foreground tabular-nums">{items.length}</span>
      </h2>
      {items.length === 0 && <p className="px-2 py-3 text-[13px] text-muted-foreground">Nothing waits for you.</p>}
      {items.map((r) => (
        <Link
          key={r.requirement_id}
          href={`${V}/decision/${encodeURIComponent(r.requirement_id)}`}
          className="grid grid-cols-[minmax(0,1fr)_auto_72px] items-baseline gap-3 border-b border-border/60 px-2 py-2.5 text-sm hover:bg-muted/40"
        >
          <span className="truncate">
            {r.priority_rank && <span className="mr-1.5 text-xs text-muted-foreground tabular-nums">#{r.priority_rank}</span>}
            {r.title}
            {r.market && <span className="ml-1.5 font-mono text-[11px] text-muted-foreground">{r.market}</span>}
          </span>
          <span className="text-xs text-muted-foreground">{r.ai_suggests ? `AI: ${humanize(r.ai_suggests).toLowerCase()}` : "not run"}</span>
          <span className="text-right text-xs text-muted-foreground tabular-nums">{fmtRange(r.score_low, r.score_high)}</span>
        </Link>
      ))}
    </section>
  );
}

function RecentDecisions({ items, agreement }: { items: DecisionsOverview["recent_decisions"]; agreement: DecisionsOverview["agreement_with_ai"] }) {
  return (
    <section className="flex flex-col">
      <h2 className="flex items-baseline gap-2 border-b px-2 pb-2.5 text-[13px] font-medium">
        Recent decisions
        {agreement.decisions > 0 && (
          <span className="ml-auto text-xs font-normal text-muted-foreground tabular-nums">
            agreed with the AI {agreement.agreed} of {agreement.decisions}
          </span>
        )}
      </h2>
      {items.length === 0 && <p className="px-2 py-3 text-[13px] text-muted-foreground">No decisions yet.</p>}
      {items.map((d, i) => (
        <Link
          key={`${d.requirement_id}-${i}`}
          href={`${V}/decision/${encodeURIComponent(d.requirement_id)}`}
          className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-border/60 px-2 py-2.5 text-sm hover:bg-muted/40"
        >
          <ToneBadge tone={statusTone({ approve: "approved", reject: "rejected", defer: "deferred", challenge: "challenged" }[d.action] ?? d.action)}>
            {humanize(d.action)}
          </ToneBadge>
          <span className="truncate">{d.title ?? d.requirement_id}</span>
          <span className="text-xs text-muted-foreground">
            {actorLabel(d.by)} · {fmtDateTime(d.at)}
            {d.agreed_with_ai != null && (d.agreed_with_ai ? " · as AI" : " · against AI")}
          </span>
        </Link>
      ))}
    </section>
  );
}
