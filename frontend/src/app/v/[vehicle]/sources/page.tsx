"use client";

import { ChevronDown, Plus } from "lucide-react";
import Link from "next/link";
import { redirect, useRouter, useSearchParams } from "next/navigation";
import { Fragment, Suspense, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ChannelIcon, SourceHoverCard, SyntheticBadge } from "@/components/provenance";
import { REVIEW_TONE, SourceReview } from "@/components/source-review";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCoverage, useMeta, usePipeline, useRecords, useSources } from "@/lib/api/hooks";
import type { Coverage, CoverageScope, Source, SourcesStage } from "@/lib/api/types";
import { fmtCount, fmtDateTime, humanize } from "@/lib/format";
import { channelLabel, isSynthetic, STREAM_ORDER, streamLabel, toSummary } from "@/lib/provenance";
import { cn } from "cn";
import { V } from "@/lib/routes";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "list", label: "Sources" },
  { key: "records", label: "Records" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

const streamOrder = (stream: string) => (STREAM_ORDER.indexOf(stream) + 99) % 99;

export default function SourcesPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <SourcesView />
    </Suspense>
  );
}

function SourcesView() {
  const router = useRouter();
  const params = useSearchParams();
  // Signals moved to their own stage page.
  if (params.get("tab") === "signals") redirect(`${V}/signals`);
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "overview") as TabKey;
  const sources = useSources();
  const coverage = useCoverage();
  const records = coverage.data?.records_by_channel.reduce((n, r) => n + r.records, 0);
  const counts: Partial<Record<TabKey, number | undefined>> = { list: sources.data?.length, records };

  return (
    <>
      <PageHeader crumbs={[{ label: "Sources" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">Where does the data come from?</p>

      <nav aria-label="Source views" className="-ml-2.5 mt-4 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => router.replace(t.key === "overview" ? `${V}/sources` : `${V}/sources?tab=${t.key}`)}
            aria-current={tab === t.key ? "page" : undefined}
            className={cn(
              "flex h-8 items-center gap-2 rounded-lg px-2.5 text-[13px]",
              tab === t.key ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
            {counts[t.key] !== undefined && <span className="font-normal text-muted-foreground/70 tabular-nums">{fmtCount(counts[t.key])}</span>}
          </button>
        ))}
      </nav>

      <div className="mt-6 max-w-5xl">
        {tab === "overview" && <Overview />}
        {tab === "list" && <SourceList stream={params.get("stream") ?? undefined} />}
        {tab === "records" && (
          <Records
            key={params.toString()}
            initial={{
              market: params.get("market") ?? undefined,
              bucket: params.get("bucket") ?? undefined,
              scope: params.get("scope") === "target" ? "target" : undefined,
              channel: params.get("channel") ?? undefined,
              ids: params.getAll("ids").flatMap((v) => v.split(",")).filter(Boolean),
            }}
          />
        )}
      </div>
    </>
  );
}

function recordsHref(filter: { channel?: string; market?: string; bucket?: string; scope?: string }) {
  const q = new URLSearchParams({ tab: "records", ...Object.fromEntries(Object.entries(filter).filter(([, v]) => v)) });
  return `${V}/sources?${q.toString()}`;
}

function Overview() {
  const { data, error, isLoading } = useCoverage();
  const { data: sources } = useSources();
  const { data: pipeline } = usePipeline();
  const lastImport = pipeline?.stages.find((s): s is SourcesStage => s.key === "sources")?.last_import;

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  const total = data.records_by_channel.reduce((n, r) => n + r.records, 0);
  // Only streams with records about this vehicle; everything else sits under "Not about the G60".
  const streams = [...new Set(data.records_by_channel.filter((r) => r.records > 0).map((r) => r.stream))].sort(
    (a, b) => streamOrder(a) - streamOrder(b),
  );

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-2">
        <p className="text-xs text-muted-foreground">Last import {lastImport ? fmtDateTime(lastImport) : "–"}</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {streams.map((stream) => (
          <StreamCard key={stream} stream={stream} coverage={data} sources={(sources ?? []).filter((s) => s.stream === stream)} />
        ))}
        <ConnectSourceCard />
        </div>
      </section>

      {total === 0 ? (
        <EmptyState title="No evidence imported yet">
          Requirements appear once research batches are ingested and accepted. The import itself runs in the backend.
        </EmptyState>
      ) : (
        <>
          <MarketMatrix coverage={data} />
          <OutsideScope coverage={data} code={(data.vehicle ?? "bmw:G60").split(":").pop() ?? "G60"} />
        </>
      )}
    </div>
  );
}

// One card per stream: how much, how far reviewed, what may reach OpenAI, when it last arrived.
function StreamCard({ stream, coverage, sources }: { stream: string; coverage: Coverage; sources: Source[] }) {
  const rows = coverage.records_by_channel.filter((r) => r.stream === stream);
  const records = rows.reduce((n, r) => n + r.records, 0);
  const byReview = new Map<string, number>();
  for (const r of rows) byReview.set(r.review_status, (byReview.get(r.review_status) ?? 0) + r.records);
  const toModel = rows.filter((r) => r.external_llm && r.review_status === "accepted").reduce((n, r) => n + r.records, 0);
  // updated_at also moves on a review, so this is the last change, not the last import.
  const lastChange = sources.map((s) => s.updated_at ?? s.collected_at).filter((d): d is string => !!d).sort().pop();
  const synthetic = sources.filter(isSynthetic).length;

  return (
    <Link
      href={`${V}/sources?tab=list&stream=${encodeURIComponent(stream)}`}
      className="flex flex-col gap-3 rounded-xl border p-4 transition-colors hover:border-foreground/25"
    >
      <span className="flex items-center gap-2 text-[13px]">
        <span className="font-medium">{streamLabel(stream)}</span>
        {synthetic > 0 && <SyntheticBadge />}
        <span className="ml-auto text-xs text-muted-foreground">
          {sources.length} source{sources.length === 1 ? "" : "s"}
        </span>
      </span>
      <span className="flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tabular-nums">{fmtCount(records)}</span>
        <span className="text-xs text-muted-foreground">records</span>
      </span>
      {records === 0 ? (
        <span className="text-xs text-muted-foreground">Nothing imported yet.</span>
      ) : (
        <dl className="grid grid-cols-[72px_minmax(0,1fr)] gap-x-2 gap-y-1 text-xs">
          <dt className="text-muted-foreground">Review</dt>
          <dd className="flex flex-wrap gap-x-2">
            {[...byReview.entries()].map(([status, n]) => (
              <span key={status}>
                <span className="tabular-nums">{fmtCount(n)}</span> <span className="text-muted-foreground">{status}</span>
              </span>
            ))}
          </dd>
          <dt className="text-muted-foreground">To OpenAI</dt>
          <dd className="tabular-nums">
            {fmtCount(toModel)} <span className="text-muted-foreground">of {fmtCount(records)}</span>
          </dd>
          <dt className="text-muted-foreground">Last change</dt>
          <dd>{lastChange ? fmtDateTime(lastChange) : "–"}</dd>
        </dl>
      )}
    </Link>
  );
}

// Placeholder for scrapers; today data arrives as a zipped research folder.
function ConnectSourceCard() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className="flex min-h-36 flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed p-4 text-[13px] text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
        >
          <Plus className="size-4" aria-hidden />
          Connect a source
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect a source</DialogTitle>
          <DialogDescription>Scrapers will plug in here. Until then, data reaches Parallax as a research folder.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 text-sm">
          <p>
            Upload a zip with <span className="font-mono text-xs">schema.json</span>, <span className="font-mono text-xs">catalog/</span> and{" "}
            <span className="font-mono text-xs">batches/</span> to <span className="font-mono text-xs">POST /api/ingest/upload</span>, for example:
          </p>
          <p className="rounded-md bg-muted px-3 py-2 font-mono text-xs">python -m parallax.cli push-research ../research</p>
          <p className="text-muted-foreground">New sources arrive as pending and need a review here before any model may use them.</p>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const BUCKETS = ["US", "EU", "CN", "RoW"];

// Channel x market bucket (US / EU / CN / RoW, as the signals count them) from one /coverage response.
// A row expands to the exact country tags behind it.
function MarketMatrix({ coverage }: { coverage: Coverage }) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const cells = coverage.records_by_channel_bucket;
  const matrix = new Map((cells ?? []).map((c) => [`${c.channel}|${c.bucket}`, c.records]));
  const countries = new Map<string, { market: string; records: number }[]>();
  for (const c of coverage.records_by_channel_market ?? []) countries.set(c.channel, [...(countries.get(c.channel) ?? []), { market: c.market, records: c.records }]);
  const streamOf = new Map([...(cells ?? []), ...coverage.records_by_channel].map((r) => [r.channel, r.stream]));
  const channels = [...streamOf.keys()];
  const streams = [...new Set(streamOf.values())].sort((a, b) => streamOrder(a) - streamOrder(b));
  const toggle = (channel: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(channel)) next.delete(channel);
      else next.add(channel);
      return next;
    });
  const CHANNEL_COL = 240;
  const BUCKET_COL = 84;

  return (
    <section>
      <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Records by channel and market</h2>
      <div className="overflow-x-auto">
        <table className="table-fixed text-sm" style={{ width: CHANNEL_COL + BUCKETS.length * BUCKET_COL }}>
          <colgroup>
            <col style={{ width: CHANNEL_COL }} />
            {BUCKETS.map((b) => (
              <col key={b} style={{ width: BUCKET_COL }} />
            ))}
          </colgroup>
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th scope="col" className="px-2 py-2.5 text-left font-normal">
                Channel
              </th>
              {BUCKETS.map((b) => (
                <th key={b} scope="col" className="px-2 py-2.5 text-right font-mono font-normal">
                  {b}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {streams.map((stream) => (
              <Fragment key={stream}>
                <tr>
                  <th scope="colgroup" colSpan={BUCKETS.length + 1} className="px-2 pt-4 pb-1 text-left text-xs font-medium">
                    {streamLabel(stream)}
                  </th>
                </tr>
                {channels
                  .filter((c) => streamOf.get(c) === stream)
                  .map((channel) => (
                    <Fragment key={channel}>
                      <tr className="border-t border-border/60">
                        <th scope="row" className="px-2 py-2 text-left font-normal">
                          <button
                            type="button"
                            onClick={() => toggle(channel)}
                            aria-expanded={open.has(channel)}
                            title={`${channelLabel(channel)}: show countries`}
                            className="flex w-full min-w-0 items-center gap-1.5 text-left hover:underline"
                          >
                            <ChannelIcon channel={channel} />
                            <span className="truncate">{channelLabel(channel)}</span>
                            <ChevronDown className={cn("size-3 shrink-0 text-muted-foreground transition-transform", open.has(channel) && "rotate-180")} aria-hidden />
                          </button>
                        </th>
                        {BUCKETS.map((bucket) => {
                          const n = cells ? (matrix.get(`${channel}|${bucket}`) ?? 0) : undefined;
                          return (
                            <td key={bucket} className="px-2 py-2 text-right tabular-nums">
                              {n === undefined ? (
                                <span className="text-muted-foreground/50">·</span>
                              ) : n === 0 ? (
                                <span className="text-muted-foreground/60">–</span>
                              ) : (
                                <Link href={recordsHref({ channel, bucket, scope: "target" })} className="hover:underline">
                                  {fmtCount(n)}
                                </Link>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                      {open.has(channel) && (
                        <tr>
                          <td colSpan={BUCKETS.length + 1} className="px-2 pb-2.5 pl-8 text-xs text-muted-foreground">
                            {(countries.get(channel) ?? []).length === 0
                              ? "No country tags."
                              : (countries.get(channel) ?? [])
                                  .sort((a, b) => b.records - a.records)
                                  .map((c) => (
                                    <Link key={c.market} href={recordsHref({ channel, market: c.market, scope: "target" })} className="mr-3 inline-block hover:text-foreground hover:underline">
                                      <span className="font-mono">{c.market}</span> {fmtCount(c.records)}
                                    </Link>
                                  ))}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      {!cells && <p className="mt-2 px-2 text-xs text-muted-foreground">This API version does not return the market buckets yet.</p>}
    </section>
  );
}

// Everything in the data set that is not about this vehicle, collapsed; each scope drills into its own matrix.
function OutsideScope({ coverage, code }: { coverage: Coverage; code: string }) {
  const [open, setOpen] = useState(false);
  const outside = (coverage.scopes ?? []).filter((s) => s.scope !== "target" && s.records > 0);
  if (outside.length === 0) return null;
  const total = outside.reduce((n, s) => n + s.records, 0);
  return (
    <section className="flex flex-col gap-2">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex items-center gap-1.5 self-start text-[13px] text-muted-foreground hover:text-foreground">
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
        Not about the {code}
        <span className="tabular-nums">· {fmtCount(total)} records</span>
      </button>
      {open && (
        <div className="flex flex-col gap-1 pl-5">
          {outside.map((s) => (
            <ScopeRow key={s.scope} scope={s.scope} label={s.label} records={s.records} />
          ))}
        </div>
      )}
    </section>
  );
}

function ScopeRow({ scope, label, records }: { scope: CoverageScope; label: string; records: number }) {
  const [open, setOpen] = useState(false);
  const { data } = useCoverage(open ? scope : undefined);
  const rows = open && data?.scope === scope ? data.records_by_channel_bucket ?? [] : [];
  const byChannel = new Map<string, Map<string, number>>();
  for (const r of rows) byChannel.set(r.channel, new Map([...(byChannel.get(r.channel) ?? []), [r.bucket, r.records]]));
  return (
    <div className="text-[13px]">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex items-center gap-2 hover:underline">
        <span>{label}</span>
        <span className="text-muted-foreground tabular-nums">{fmtCount(records)}</span>
      </button>
      {open && (
        <div className="mt-1 mb-2 flex flex-col gap-0.5 pl-3 text-xs text-muted-foreground">
          {!data || data.scope !== scope ? (
            <span>Loading…</span>
          ) : (
            [...byChannel.entries()].map(([channel, buckets]) => (
              <span key={channel} className="flex gap-3">
                <span className="w-44 truncate">{channelLabel(channel)}</span>
                {BUCKETS.map((b) => (
                  <span key={b} className="w-16 text-right tabular-nums">
                    <span className="font-mono">{b}</span> {fmtCount(buckets.get(b) ?? 0)}
                  </span>
                ))}
              </span>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function SourceList({ stream }: { stream?: string }) {
  const { data, error, isLoading } = useSources();
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  if (data.length === 0) return <EmptyState title="No sources yet">Sources appear once the backend has ingested research batches.</EmptyState>;
  const shown = stream ? data.filter((s) => s.stream === stream) : data;
  return (
    <section>
      {stream && (
        <p className="flex items-center gap-2 px-2 pb-2 text-xs text-muted-foreground">
          {streamLabel(stream)} only
          <Link href={`${V}/sources?tab=list`} className="text-foreground hover:underline">
            Show all
          </Link>
        </p>
      )}
      <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_100px_150px] gap-4 px-2 py-2.5 text-xs text-muted-foreground">
        <span>Source</span>
        <span>Channel</span>
        <span className="text-right">Records</span>
        <span>Review</span>
        <span />
      </div>
      {[...shown]
        .sort((a, b) => streamOrder(a.stream) - streamOrder(b.stream))
        .map((s) => (
          <SourceListRow key={s.source_id} source={s} />
        ))}
    </section>
  );
}

function SourceListRow({ source }: { source: Source }) {
  return (
    <div className="border-t border-border/60 px-2 py-3 text-sm">
      <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_100px_150px] items-center gap-4">
        <span className="min-w-0">
          <span className="flex items-center gap-2">
            <SourceHoverCard source={toSummary(source)}>
              <Link href={`${V}/sources/${encodeURIComponent(source.source_id)}`} className="truncate font-medium hover:underline">
                {source.title}
              </Link>
            </SourceHoverCard>
            {isSynthetic(source) && <SyntheticBadge />}
          </span>
          <span className="block truncate font-mono text-xs text-muted-foreground">
            {source.source_id}
            {source.collected_at && ` · ${fmtDateTime(source.collected_at)}`}
          </span>
        </span>
        <span className="flex items-center gap-1.5 truncate text-[13px] text-muted-foreground">
          <ChannelIcon channel={source.channel} />
          {channelLabel(source.channel)} · {streamLabel(source.stream)}
        </span>
        <span className="text-right tabular-nums">{source.normalized_record_count}</span>
        <span>
          <ToneBadge tone={REVIEW_TONE[source.review_status] ?? "muted"}>{source.review_status}</ToneBadge>
        </span>
        <SourceReview sourceId={source.source_id} title={source.title} status={source.review_status} />
      </div>
    </div>
  );
}

function Records({ initial }: { initial: { market?: string; bucket?: string; scope?: "target"; channel?: string; ids: string[] } }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [market, setMarket] = useState<string | undefined>(initial.market);
  const [offset, setOffset] = useState(0);
  const channel = initial.channel;
  const ids = initial.ids;
  const { data: meta } = useMeta();
  const { data: sources } = useSources();
  const bucket = initial.bucket;
  const scope = initial.scope;
  const { data, error, isLoading } = useRecords({ q, market, bucket, scope, channel, ids, offset });
  const bySource = new Map((sources ?? []).map((s) => [s.source_id, s]));
  const filtered = !!channel || !!bucket || ids.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
          placeholder="Search the text"
          aria-label="Search records"
          className="h-8 max-w-xs"
        />
        <Select
          value={market ?? "all"}
          onValueChange={(v) => {
            setMarket(v === "all" ? undefined : v);
            setOffset(0);
          }}
        >
          <SelectTrigger size="sm" className="w-36" aria-label="Market">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All markets</SelectItem>
            {[...new Set([...(meta?.markets ?? ["US", "EU", "CN"]), ...(initial.market ? [initial.market] : [])])].map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {filtered && (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            {ids.length > 0
              ? `${ids.length} selected record${ids.length === 1 ? "" : "s"}`
              : [channel && channelLabel(channel), bucket && `${bucket} market`, scope === "target" && "this vehicle"].filter(Boolean).join(" · ")}
            <Button size="xs" variant="ghost" onClick={() => router.replace(`${V}/sources?tab=records`)}>
              Clear
            </Button>
          </span>
        )}
        {data && <span className="ml-auto text-xs text-muted-foreground tabular-nums">{data.total} records</span>}
      </div>

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && data.items.length === 0 && <EmptyState title="No records match" />}
      <div>
        {data?.items.map((r) => {
          const source = bySource.get(r.source_id);
          return (
            <div key={r.record_id} id={`rec-${r.record_id}`} className="grid grid-cols-[minmax(0,1fr)_230px] gap-6 border-t border-border/60 px-2 py-3 text-sm">
              <div className="flex min-w-0 flex-col gap-1.5">
                <p className="line-clamp-3">{r.translation_en ?? r.text_original ?? "–"}</p>
                {source && isSynthetic(source) && <SyntheticBadge className="self-start" />}
              </div>
              <span className="flex min-w-0 flex-col gap-0.5 text-xs text-muted-foreground">
                {source ? (
                  <SourceHoverCard source={toSummary(source)}>
                    <button type="button" className="truncate text-left text-foreground/80 hover:underline">
                      {source.title}
                    </button>
                  </SourceHoverCard>
                ) : (
                  <span>source unknown</span>
                )}
                <span className="truncate font-mono">{r.record_id}</span>
                <span className="flex items-center gap-1.5 truncate">
                  <ChannelIcon channel={r.channel} className="size-3" />
                  {channelLabel(r.channel)} · {humanize(r.record_kind)}
                  {r.markets.length ? ` · ${r.markets.join(", ")}` : ""}
                </span>
              </span>
            </div>
          );
        })}
      </div>
      {data && data.total > 50 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Button size="xs" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>
            Previous
          </Button>
          <Button size="xs" variant="outline" disabled={offset + 50 >= data.total} onClick={() => setOffset(offset + 50)}>
            Next
          </Button>
          <span className="tabular-nums">
            {offset + 1}–{Math.min(offset + 50, data.total)} of {data.total}
          </span>
        </div>
      )}
    </div>
  );
}
