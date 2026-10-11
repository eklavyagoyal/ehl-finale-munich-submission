"use client";

import { Layers } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorState, LoadingRows } from "@/components/states";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useCoverage, useTriageSample, useTriageSummary, useVehicles } from "@/lib/api/hooks";
import type { Coverage, TriageSummary, Vehicle } from "@/lib/api/types";
import { STREAM_ORDER, streamLabel } from "@/lib/provenance";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";
import { V } from "@/lib/routes";

// Side views as hairlines: a sedan, the long-wheelbase sedan, the larger 7 Series and the 1 Series hatch.
const SILHOUETTE: Record<string, string> = {
  G60: "M8 44 L14 34 Q40 30 58 22 Q74 14 100 14 Q122 14 140 26 L172 30 Q184 32 186 40 L186 44",
  G68: "M4 44 L10 34 Q36 30 54 22 Q72 14 104 14 Q130 14 148 26 L180 30 Q192 32 194 40 L194 44",
  G70: "M6 44 L10 32 Q36 28 56 20 Q74 12 104 12 Q130 12 150 24 L182 28 Q194 30 196 40 L196 44",
  F70: "M22 44 L26 34 Q44 30 60 22 Q74 14 98 14 Q122 14 134 22 Q146 30 158 32 Q170 34 172 44",
};
const WHEELS: Record<string, number[]> = { G60: [46, 150], G68: [44, 160], G70: [46, 160], F70: [52, 140] };

function Silhouette({ code, muted }: { code: string; muted: boolean }) {
  const body = SILHOUETTE[code];
  if (!body) return <Layers className="size-10 text-muted-foreground/60" strokeWidth={1} aria-hidden />;
  return (
    <svg viewBox="0 0 200 56" className={cn("h-12 w-full", muted ? "text-muted-foreground/40" : "text-foreground/70")} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round">
        <path d={body} />
        <line x1={4} y1={44} x2={196} y2={44} strokeOpacity={0.3} />
        {(WHEELS[code] ?? []).map((x) => (
          <circle key={x} cx={x} cy={44} r={8} fill="var(--background)" />
        ))}
      </g>
    </svg>
  );
}

export default function OverviewPage() {
  const { data, error, isLoading } = useVehicles();
  const coverage = useCoverage("all");
  const triage = useTriageSummary();

  return (
    <main className="mx-auto flex min-h-svh max-w-5xl flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <span className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">P</span>
          <span className="font-semibold">Parallax</span>
        </span>
        <p className="max-w-2xl text-[17px] leading-relaxed text-foreground/80">
          Parallax turns what owners really say into requirements for the next BMW, lets simulated owners and departments argue about them,
          and shows you why every agent decided what it did, so you can decide with confidence.
        </p>
      </header>

      {coverage.data && <DataOverview coverage={coverage.data} active={data?.active} />}
      {triage.data && <TriageOverview triage={triage.data} />}

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((v) => (
            <VehicleCard key={v.entity_id} vehicle={v} />
          ))}
        </section>
      )}
    </main>
  );
}

// What data exists across all vehicles: by stream and by what it is about. Labels and numbers only.
function DataOverview({ coverage, active }: { coverage: Coverage; active?: string }) {
  const byStream = new Map<string, number>();
  for (const r of coverage.records_by_channel) byStream.set(r.stream, (byStream.get(r.stream) ?? 0) + r.records);
  const streams = [...byStream.entries()].sort(([a], [b]) => (STREAM_ORDER.indexOf(a) + 9) % 9 - ((STREAM_ORDER.indexOf(b) + 9) % 9));
  const code = (active ?? "bmw:G60").split(":").pop();
  const scopes = (coverage.scopes ?? []).filter((s) => s.scope !== "all");
  const scopeLabel = (scope: string, label: string) => (scope === "target" ? code : label.replace(/ \(.*\)$/, ""));

  return (
    <section className="grid gap-x-16 gap-y-6 sm:grid-cols-2">
      <StatRow title="By stream" items={streams.map(([stream, n]) => ({ key: stream, label: streamLabel(stream), value: n }))} />
      <StatRow title="About" items={scopes.map((s) => ({ key: s.scope, label: scopeLabel(s.scope, s.label) ?? s.label, value: s.records }))} />
    </section>
  );
}

// Online reviews after triage: was the vehicle checked, is the author an owner, is it relevant. Not validated yet.
function TriageOverview({ triage: t }: { triage: TriageSummary }) {
  const [open, setOpen] = useState(false);
  const sum = (o: Record<string, number> | undefined) => Object.values(o ?? {}).reduce((n, v) => n + v, 0);
  const vehicleChecked = sum(t.overall.vehicle) - (t.overall.vehicle?.unclear ?? 0);
  const items = [
    { key: "triaged", label: `triaged of ${fmtCount(t.online_records)} online`, value: t.triaged },
    { key: "vehicle", label: "vehicle identified", value: vehicleChecked },
    { key: "owner", label: "written by an owner", value: t.overall.author?.owner ?? 0 },
    { key: "relevant", label: "relevant", value: t.overall.relevant?.true ?? 0 },
  ];
  return (
    <section className="flex flex-col gap-2">
      <StatRow title="Online reviews, triage" items={items} />
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <HoverCard openDelay={100}>
          <HoverCardTrigger asChild>
            <span className="cursor-default rounded-full border px-2 py-0.5">{t.validated ? "validated" : "not validated"}</span>
          </HoverCardTrigger>
          <HoverCardContent className="w-72 text-xs">{t.note}</HoverCardContent>
        </HoverCard>
        {t.last_run && <span>last run {t.last_run.status === "queued" ? "waiting" : t.last_run.status}</span>}
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button type="button" className="underline-offset-2 hover:text-foreground hover:underline">
              Spot check
            </button>
          </DialogTrigger>
          <DialogContent className="max-h-[80svh] overflow-y-auto sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Spot check: triaged reviews</DialogTitle>
              <DialogDescription>{t.note}</DialogDescription>
            </DialogHeader>
            <SpotCheck open={open} />
          </DialogContent>
        </Dialog>
      </div>
    </section>
  );
}

function SpotCheck({ open }: { open: boolean }) {
  const { data, error, isLoading } = useTriageSample(open);
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  return (
    <ul className="flex flex-col">
      {data.items.map((i) => (
        <li key={i.record_id} className="grid grid-cols-[minmax(0,1fr)_200px] gap-4 border-b border-border/60 py-2 text-[13px]">
          <span className="line-clamp-3">{i.text}</span>
          <span className="flex flex-col gap-0.5 text-xs text-muted-foreground">
            <span>
              {i.vehicle} · {i.engine} · {i.author} · {i.relevant ? "relevant" : "not relevant"}
            </span>
            {i.reason && <span className="line-clamp-2">{i.reason}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function StatRow({ title, items }: { title: string; items: { key: string; label: string; value: number }[] }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-x-8 gap-y-3">
        {items.map((i) => (
          <span key={i.key} className="flex flex-col">
            <span className="text-xl font-semibold tabular-nums">{fmtCount(i.value)}</span>
            <span className="text-xs text-muted-foreground">{i.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function VehicleCard({ vehicle: v }: { vehicle: Vehicle }) {
  const active = v.status === "active";
  const inner = (
    <>
      <Silhouette code={v.code} muted={!active} />
      <span className="flex flex-col gap-0.5">
        <span className="flex items-baseline gap-2">
          <span className={cn("font-medium", !active && "text-muted-foreground")}>{v.name}</span>
          {!active && <span className="ml-auto text-xs text-muted-foreground">coming</span>}
        </span>
        <span className="text-xs text-muted-foreground">{v.detail}</span>
      </span>
      <span className="text-xs text-muted-foreground tabular-nums">
        {v.records ? `${fmtCount(v.records)} records` : "no data imported"}
        {v.status === "data_available" && " · not analysed yet"}
      </span>
    </>
  );
  const box = "flex flex-col gap-4 rounded-xl border p-5";
  if (!active) return <div className={cn(box, "border-dashed opacity-80")}>{inner}</div>;
  return (
    <Link href={V} className={cn(box, "transition-colors hover:border-foreground/30")}>
      {inner}
    </Link>
  );
}
