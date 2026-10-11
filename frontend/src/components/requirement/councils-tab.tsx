"use client";

import { useState } from "react";

import { ReliabilityInfo } from "@/components/reliability-info";
import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useCouncil } from "@/lib/api/hooks";
import type { CouncilDepartment, CouncilMarket, CouncilPersona, TraceTension } from "@/lib/api/types";
import { actorLabel, humanize } from "@/lib/format";
import { cn } from "cn";

import { BudgetBar, VERDICTS, VerdictBar, verdictColor, verdictLabel } from "./council-bits";
import { useRequirementContext } from "./context";
import { BudgetNote } from "./decision-path";
import { RunButton } from "./shell";

const MARKET_ORDER = ["US", "EU", "CN"];

export function CouncilsTab() {
  const { id } = useRequirementContext();
  const { data, error, isLoading } = useCouncil(id);

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  if (data.status === "not_simulated") {
    return (
      <div className="flex max-w-xl flex-col items-start gap-3 py-6">
        <p className="text-sm font-medium">No councils yet</p>
        <p className="text-[13px] text-muted-foreground">Run Parallax to ask owners in the US, Europe and China and the company departments.</p>
        <RunButton />
      </div>
    );
  }

  // Only markets whose owners answered: a US case is asked to US owners only (like Sales US).
  const markets = Object.entries(data.customers?.by_market ?? {})
    .filter(([, m]) => (m.personas?.length ?? 0) > 0)
    .sort(
    ([a], [b]) => ((MARKET_ORDER.indexOf(a) + 9) % 9) - ((MARKET_ORDER.indexOf(b) + 9) % 9),
  );

  return (
    <div className="flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-start gap-4">
        {data.question_to_owners && <OwnerQuestion text={data.question_to_owners} />}
        <span className="ml-auto flex flex-col items-end gap-1">
          <span className="text-xs text-muted-foreground">Owners and Sales are asked per market; the other departments are global.</span>
          <ReliabilityInfo />
        </span>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <section className="flex flex-col gap-5">
          <h2 className="border-b pb-2.5 text-[13px] font-medium">
            Customer council <span className="font-normal text-muted-foreground">simulated owners</span>
          </h2>
          <p className="-mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {VERDICTS.filter((v) => v.key !== "unknown").map((v) => (
              <span key={v.key} className="flex items-center gap-1">
                <span className={cn("size-2 rounded-sm", v.color)} aria-hidden />
                {v.label}
              </span>
            ))}
          </p>
          {markets.map(([market, m]) => (
            <MarketBlock key={market} market={market} data={m} />
          ))}
          {data.customers?.view && <More text={data.customers.view} />}
          <BudgetNote />
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="border-b pb-2.5 text-[13px] font-medium">Tensions</h2>
          {(data.tensions ?? []).length === 0 && <p className="text-[13px] text-muted-foreground">No tension between customers and company recorded.</p>}
          {(data.tensions ?? []).slice(0, 5).map((t, i) => (
            <TensionCard key={i} tension={t} />
          ))}
          {(data.research ?? []).length > 0 && (
            <div className="mt-3 flex flex-col gap-1.5">
              <h3 className="text-xs text-muted-foreground">Research the councils asked for</h3>
              {data.research!.slice(0, 5).map((r, i) => (
                <p key={i} className="flex items-start gap-2 text-[13px]">
                  <ToneBadge tone={r.verdict === "verified" ? "green" : r.verdict === "partially_verified" ? "amber" : "muted"}>
                    {humanize(r.verdict ?? "open")}
                  </ToneBadge>
                  <span className="min-w-0">
                    {r.question}
                    <span className="text-muted-foreground"> · asked by {actorLabel(r.requested_by)}</span>
                  </span>
                </p>
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="border-b pb-2.5 text-[13px] font-medium">
            Company council <span className="font-normal text-muted-foreground">simulated departments</span>
          </h2>
          {(data.company?.departments ?? []).map((d) => (
            <DepartmentRow key={d.agent_id} dept={d} />
          ))}
          {data.company?.view && <More text={data.company.view} />}
        </section>
      </div>
    </div>
  );
}

function OwnerQuestion({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const first = text.split("\n")[0];
  return (
    <div className="flex max-w-3xl flex-col gap-1 text-[13px]">
      <p className="text-xs text-muted-foreground">Question the owners got</p>
      <p className={cn("whitespace-pre-line", !open && "line-clamp-1")}>{open ? text : first}</p>
      <button type="button" onClick={() => setOpen((o) => !o)} className="self-start text-xs text-muted-foreground hover:text-foreground">
        {open ? "Show less" : "Show the full question"}
      </button>
    </div>
  );
}

function MarketBlock({ market, data }: { market: string; data: CouncilMarket }) {
  const s = data.summary;
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-[40px_minmax(0,1fr)_120px] items-center gap-3 text-[13px]">
        <span className="font-mono text-xs">{market}</span>
        <VerdictBar verdicts={s.verdicts} className="h-2" />
        <BudgetBar points={s.mean_budget_points_of_100} />
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1.5 pl-[52px]">
        {data.personas.map((p) => (
          <PersonaChip key={p.agent_id} persona={p} />
        ))}
      </div>
    </div>
  );
}

function PersonaChip({ persona: p }: { persona: CouncilPersona }) {
  const name = p.name ?? p.display_name;
  return (
    <HoverCard openDelay={100} closeDelay={60}>
      <HoverCardTrigger asChild>
        <button type="button" className="flex items-center gap-1.5 text-left text-xs">
          <span className="relative flex size-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium uppercase">
            {name.slice(0, 2)}
            <span className={cn("absolute -right-0.5 -bottom-0.5 size-2 rounded-full ring-2 ring-background", verdictColor(p.verdict))} aria-hidden />
          </span>
          <span className="flex flex-col leading-tight">
            <span>{name}</span>
            {p.vehicle && <span className="text-[11px] text-muted-foreground">{p.vehicle}</span>}
          </span>
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <p className="font-medium">{name}</p>
        <p className="text-muted-foreground">{[p.display_name, p.vehicle, p.powertrain].filter(Boolean).join(" · ")}</p>
        <p className="mt-2 text-foreground/80">“{p.quote}”</p>
        <p className="mt-2 flex items-center gap-2">
          <span className={cn("size-2 rounded-sm", verdictColor(p.verdict))} aria-hidden />
          {verdictLabel(p.verdict)}
          <span className="text-muted-foreground">· budget {p.budget_points == null ? "not asked" : `${p.budget_points.toFixed(0)} of 100`}</span>
        </p>
        {p.concerns?.length ? <p className="mt-1 text-muted-foreground">Worries: {p.concerns.join(", ")}</p> : null}
        <p className="mt-1 text-muted-foreground">{p.validation_status ? humanize(p.validation_status) : "Not validated"} · simulated</p>
      </HoverCardContent>
    </HoverCard>
  );
}

function TensionCard({ tension: t }: { tension: TraceTension }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3 text-[13px]">
      {t.topic && <p className="text-xs font-medium">{humanize(t.topic)}</p>}
      {t.customers_say || t.company_says ? (
        <>
          <p>
            <span className="text-xs text-muted-foreground">Customers say </span>
            {t.customers_say ?? "–"}
          </p>
          <p>
            <span className="text-xs text-muted-foreground">Company says </span>
            {t.company_says ?? "–"}
          </p>
        </>
      ) : (
        t.description && <p>{t.description}</p>
      )}
      {t.resolution_options?.length ? (
        <div>
          <p className="text-xs text-muted-foreground">Options</p>
          <ul className="mt-0.5 flex list-disc flex-col gap-0.5 pl-4">
            {t.resolution_options.slice(0, 3).map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function DepartmentRow({ dept: d }: { dept: CouncilDepartment }) {
  return (
    <HoverCard openDelay={120} closeDelay={60}>
      <HoverCardTrigger asChild>
        <div className="flex flex-col gap-1 border-b border-border/60 pb-3 text-[13px]">
          <p className="flex items-baseline gap-2">
            <span className="font-medium">{d.display_name}</span>
            {d.cost_view && d.cost_view !== "unknown" && <span className="text-xs text-muted-foreground">cost: {humanize(d.cost_view)}</span>}
            <span className="ml-auto text-[11px] text-muted-foreground/70">{humanize(d.verdict ?? "")}</span>
          </p>
          {d.main_argument && <p className="truncate text-foreground/80">{d.main_argument}</p>}
        </div>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <p className="font-medium">{d.display_name}</p>
        {d.main_argument && <p className="mt-1">{d.main_argument}</p>}
        {d.strongest_counterargument && <p className="mt-2 text-muted-foreground">Strongest counterargument: {d.strongest_counterargument}</p>}
        {d.effort_band && d.effort_band !== "unknown" && <p className="mt-1 text-muted-foreground">Effort: {humanize(d.effort_band)}</p>}
        {d.risks?.length ? <p className="mt-1 text-muted-foreground">Risks: {d.risks.join(", ")}</p> : null}
        <p className="mt-1 text-muted-foreground">Simulated department · assumption</p>
      </HoverCardContent>
    </HoverCard>
  );
}

// Long text stays one click away: a quiet "More" that opens the paragraph in place.
function More({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return open ? (
    <p className="text-[13px] text-foreground/80">{text}</p>
  ) : (
    <button type="button" onClick={() => setOpen(true)} className="self-start text-xs text-muted-foreground hover:text-foreground">
      More
    </button>
  );
}
