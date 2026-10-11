"use client";

import { useState } from "react";

import { ErrorState, LoadingRows } from "@/components/states";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useTriageSample } from "@/lib/api/hooks";
import type { Coverage, TriageSummary } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { STREAM_ORDER, streamLabel } from "@/lib/provenance";

// What data exists across all vehicles: by stream and by what it is about. Labels and numbers only.
export function DataOverview({ coverage, active }: { coverage: Coverage; active?: string }) {
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
export function TriageOverview({ triage: t }: { triage: TriageSummary }) {
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
