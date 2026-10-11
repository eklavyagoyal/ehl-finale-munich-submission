"use client";

import { Fragment, useState } from "react";

import { ChannelMark } from "@/components/brand-icon";
import { ErrorState, LoadingRows } from "@/components/states";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useTriageSample } from "@/lib/api/hooks";
import type { Coverage, TriageSummary } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { channelLabel } from "@/lib/provenance";
import { cn } from "cn";

// ── Where it comes from: a hairline world map with one circle per market bucket, and the channels as tiles. ──

// Equirectangular, longitude -170..170 and latitude 80..-60, 2 units per degree.
const MAP_W = 680;
const MAP_H = 280;
const project = ([lon, lat]: [number, number]) => [(lon + 170) * 2, (80 - lat) * 2] as const;

// Deliberately coarse continents: enough to place the markets, nothing more.
const CONTINENTS: [number, number][][] = [
  [[-165, 65], [-140, 70], [-95, 72], [-80, 62], [-60, 55], [-55, 48], [-70, 43], [-80, 32], [-82, 25], [-97, 26], [-105, 20], [-95, 16], [-85, 13], [-80, 8], [-90, 15], [-105, 22], [-115, 30], [-124, 40], [-125, 48], [-135, 57], [-155, 58], [-165, 62]],
  [[-55, 80], [-30, 80], [-20, 75], [-40, 62], [-50, 65], [-58, 75]],
  [[-80, 10], [-62, 10], [-50, 0], [-35, -7], [-40, -22], [-55, -35], [-65, -55], [-72, -50], [-75, -35], [-70, -18], [-80, -5]],
  [[-10, 36], [-9, 43], [-2, 44], [-5, 48], [0, 50], [5, 53], [8, 57], [5, 62], [15, 70], [30, 71], [40, 66], [40, 55], [30, 46], [28, 41], [20, 40], [15, 38], [10, 44], [5, 43], [0, 39]],
  [[-17, 21], [-10, 30], [0, 36], [10, 37], [20, 32], [32, 31], [35, 28], [43, 12], [51, 12], [40, -2], [40, -15], [35, -25], [20, -35], [15, -28], [12, -15], [9, 0], [-5, 5], [-15, 10]],
  [[40, 66], [60, 70], [80, 73], [100, 77], [130, 72], [160, 70], [170, 66], [165, 60], [155, 58], [140, 50], [130, 42], [122, 40], [122, 30], [110, 21], [105, 10], [100, 13], [98, 8], [92, 22], [80, 15], [77, 8], [70, 22], [60, 25], [50, 30], [45, 40], [40, 42], [30, 46], [40, 55]],
  [[130, 31], [135, 34], [141, 38], [142, 44], [140, 41], [135, 35]],
  [[114, -22], [122, -18], [131, -12], [137, -12], [142, -11], [146, -19], [153, -27], [150, -37], [140, -38], [130, -32], [115, -34]],
];

const BUCKET_AT: Record<string, [number, number]> = { US: [-98, 39], EU: [12, 50], CN: [104, 34], RoW: [-58, -18] };
const MAX_R = 46;

export function WhereItComesFrom({ coverage }: { coverage: Coverage }) {
  const byBucket = new Map<string, Map<string, number>>();
  for (const c of coverage.records_by_channel_bucket ?? []) {
    const channels = byBucket.get(c.bucket) ?? new Map<string, number>();
    channels.set(c.channel, (channels.get(c.channel) ?? 0) + c.records);
    byBucket.set(c.bucket, channels);
  }
  const totals = Object.keys(BUCKET_AT).map((b) => ({ bucket: b, records: [...(byBucket.get(b)?.values() ?? [])].reduce((n, v) => n + v, 0) }));
  const max = Math.max(1, ...totals.map((t) => t.records));

  const byChannel = new Map<string, number>();
  for (const r of coverage.records_by_channel) byChannel.set(r.channel, (byChannel.get(r.channel) ?? 0) + r.records);
  const channels = [...byChannel.entries()].sort((a, b) => b[1] - a[1]);
  const channelTotal = channels.reduce((n, [, v]) => n + v, 0) || 1;
  const channelMax = Math.max(1, ...channels.map(([, v]) => v));

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-[13px] font-medium">Where it comes from</h2>
      <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="relative w-full" style={{ aspectRatio: `${MAP_W} / ${MAP_H}` }}>
          <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} className="absolute inset-0 size-full" aria-hidden>
            <g className="fill-muted/60 stroke-foreground/20" strokeWidth={1} strokeLinejoin="round">
              {CONTINENTS.map((shape, i) => (
                <path key={i} d={`M ${shape.map((p) => project(p).join(" ")).join(" L ")} Z`} />
              ))}
            </g>
          </svg>
          {totals.map(({ bucket, records }) => {
            const [x, y] = project(BUCKET_AT[bucket]);
            const r = records ? Math.max(6, Math.sqrt(records / max) * MAX_R) : 0;
            const split = [...(byBucket.get(bucket)?.entries() ?? [])].sort((a, b) => b[1] - a[1]);
            return (
              <Fragment key={bucket}>
              <span
                className="pointer-events-none absolute -translate-x-1/2 text-[11px] leading-tight whitespace-nowrap"
                style={{ left: `${(x / MAP_W) * 100}%`, top: `${((y + Math.max(r, 4) + 4) / MAP_H) * 100}%` }}
              >
                <span className="font-medium">{bucket}</span> <span className="text-muted-foreground tabular-nums">{fmtCount(records)}</span>
              </span>
              <HoverCard openDelay={80} closeDelay={60}>
                <HoverCardTrigger asChild>
                  <button
                    type="button"
                    aria-label={`${bucket}: ${records} records`}
                    className="absolute rounded-full bg-foreground/75 ring-4 ring-background/60"
                    style={{
                      left: `${((x - Math.max(r, 4)) / MAP_W) * 100}%`,
                      top: `${((y - Math.max(r, 4)) / MAP_H) * 100}%`,
                      width: `${((2 * Math.max(r, 4)) / MAP_W) * 100}%`,
                      height: `${((2 * Math.max(r, 4)) / MAP_H) * 100}%`,
                      opacity: records ? 1 : 0.3,
                    }}
                  />
                </HoverCardTrigger>
                <HoverCardContent className="w-60 text-xs">
                  <p className="mb-1.5 font-medium">
                    {bucket} · {fmtCount(records)} records
                  </p>
                  {split.length === 0 && <p className="text-muted-foreground">No records tagged here.</p>}
                  {split.map(([channel, n]) => (
                    <p key={channel} className="flex justify-between gap-3">
                      <span>{channelLabel(channel)}</span>
                      <span className="tabular-nums">{fmtCount(n)}</span>
                    </p>
                  ))}
                </HoverCardContent>
              </HoverCard>
              </Fragment>
            );
          })}
        </div>

        <div className="flex flex-wrap items-end gap-3">
          {channels.map(([channel, n]) => {
            const size = Math.max(30, Math.sqrt(n / channelMax) * 96);
            return (
              <HoverCard key={channel} openDelay={80} closeDelay={60}>
                <HoverCardTrigger asChild>
                  <span
                    className="flex cursor-default items-center justify-center rounded-full border bg-background text-foreground/70"
                    style={{ width: size, height: size }}
                  >
                    <ChannelMark channel={channel} className={cn(size > 60 ? "size-6" : "size-4")} />
                  </span>
                </HoverCardTrigger>
                <HoverCardContent className="w-52 text-xs">
                  <p className="font-medium">{channelLabel(channel)}</p>
                  <p className="text-muted-foreground tabular-nums">
                    {fmtCount(n)} records · {Math.round((n / channelTotal) * 100)} %
                  </p>
                </HoverCardContent>
              </HoverCard>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ── About which vehicle: one thin stacked bar over the scopes, labels at the segments, numbers on hover. ──

const SCOPE_COLOR: Record<string, string> = {
  target: "bg-foreground/80",
  competitor: "bg-foreground/45",
  other_models: "bg-foreground/30",
  brand: "bg-foreground/15",
};

export function AboutBar({ coverage, code }: { coverage: Coverage; code: string }) {
  const scopes = (coverage.scopes ?? []).filter((s) => s.scope !== "all" && s.records > 0);
  const total = scopes.reduce((n, s) => n + s.records, 0);
  if (!total) return null;
  const label = (s: { scope: string; label: string }) => (s.scope === "target" ? code : s.label.replace(/ \(.*\)$/, ""));
  return (
    <section className="flex flex-col gap-1.5">
      <p className="text-xs text-muted-foreground">About which vehicle</p>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
        {scopes.map((s) => (
          <HoverCard key={s.scope} openDelay={80} closeDelay={60}>
            <HoverCardTrigger asChild>
              <span className={SCOPE_COLOR[s.scope] ?? "bg-foreground/20"} style={{ width: `${(s.records / total) * 100}%` }} />
            </HoverCardTrigger>
            <HoverCardContent className="w-52 text-xs">
              {label(s)} · <span className="tabular-nums">{fmtCount(s.records)}</span> records ({Math.round((s.records / total) * 100)} %)
            </HoverCardContent>
          </HoverCard>
        ))}
      </div>
      <div className="flex w-full text-[11px] text-muted-foreground">
        {scopes.map((s) => (
          <span key={s.scope} className="truncate" style={{ width: `${(s.records / total) * 100}%`, minWidth: "fit-content" }}>
            {label(s)}
          </span>
        ))}
      </div>
    </section>
  );
}

// ── Triage in one muted line; the note and the spot check open on click. ──

export function TriageLine({ triage: t }: { triage: TriageSummary }) {
  const [open, setOpen] = useState(false);
  const relevant = t.overall.relevant?.true ?? 0;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <p className="text-xs text-muted-foreground">
        Triage: <span className="tabular-nums">{fmtCount(relevant)}</span> of <span className="tabular-nums">{fmtCount(t.online_records)}</span> online
        reviews relevant · {t.validated ? "validated" : "not validated"} ·{" "}
        <DialogTrigger asChild>
          <button type="button" className="underline-offset-2 hover:text-foreground hover:underline">
            Spot check
          </button>
        </DialogTrigger>
      </p>
      <DialogContent className="max-h-[80svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Triage spot check</DialogTitle>
          <DialogDescription>
            {fmtCount(t.triaged)} of {fmtCount(t.online_records)} online reviews triaged. {t.note}
          </DialogDescription>
        </DialogHeader>
        <SpotCheck open={open} />
      </DialogContent>
    </Dialog>
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
