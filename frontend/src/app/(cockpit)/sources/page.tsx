"use client";

import { Plus } from "lucide-react";
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
import type { Coverage, Source, SourcesStage } from "@/lib/api/types";
import { fmtCount, fmtDateTime, humanize } from "@/lib/format";
import { channelLabel, isSynthetic, STREAM_ORDER, streamLabel, toSummary } from "@/lib/provenance";
import { cn } from "cn";

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
  if (params.get("tab") === "signals") redirect("/signals");
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "overview") as TabKey;
  const sources = useSources();
  const coverage = useCoverage();
  const records = coverage.data?.records_by_channel.reduce((n, r) => n + r.records, 0);
  const counts: Partial<Record<TabKey, number | undefined>> = { list: sources.data?.length, records };

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "Sources" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">Where does the data come from?</p>

      <nav aria-label="Source views" className="-ml-2.5 mt-4 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => router.replace(t.key === "overview" ? "/sources" : `/sources?tab=${t.key}`)}
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
              channel: params.get("channel") ?? undefined,
              ids: params.getAll("ids").flatMap((v) => v.split(",")).filter(Boolean),
            }}
          />
        )}
      </div>
    </>
  );
}

function recordsHref(filter: { channel?: string; market?: string }) {
  const q = new URLSearchParams({ tab: "records", ...Object.fromEntries(Object.entries(filter).filter(([, v]) => v)) });
  return `/sources?${q.toString()}`;
}

function Overview() {
  const { data, error, isLoading } = useCoverage();
  const { data: meta } = useMeta();
  const { data: sources } = useSources();
  const { data: pipeline } = usePipeline();
  const lastImport = pipeline?.stages.find((s): s is SourcesStage => s.key === "sources")?.last_import;

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  const total = data.records_by_channel.reduce((n, r) => n + r.records, 0);
  const streams = [...new Set(["bmw", "social", "competitors", ...data.records_by_channel.map((r) => r.stream)])].sort(
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
        <MarketMatrix coverage={data} targetMarkets={meta?.markets ?? []} />
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
      href={`/sources?tab=list&stream=${encodeURIComponent(stream)}`}
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

// Channel x market from coverage.records_by_channel_market: one request for the whole matrix.
function MarketMatrix({ coverage, targetMarkets }: { coverage: Coverage; targetMarkets: string[] }) {
  const cells = coverage.records_by_channel_market;
  const matrix = new Map((cells ?? []).map((c) => [`${c.channel}|${c.market}`, c.records]));
  const channels = [...new Set([...coverage.records_by_channel.map((r) => r.channel), ...(cells ?? []).map((c) => c.channel)])];
  const tagged = coverage.records_by_market.map((m) => m.market).filter((m): m is string => !!m);
  const markets = [...new Set([...targetMarkets, ...tagged])];
  const streamOf = new Map([...(cells ?? []), ...coverage.records_by_channel].map((r) => [r.channel, r.stream]));
  const streams = [...new Set(streamOf.values())].sort((a, b) => streamOrder(a) - streamOrder(b));
  const missing =
    cells &&
    streams.flatMap((stream) =>
      targetMarkets
        .filter((market) => channels.filter((c) => streamOf.get(c) === stream).every((c) => (matrix.get(`${c}|${market}`) ?? 0) === 0))
        .map((market) => `No ${streamLabel(stream)} records tagged ${market}`),
    );
  const CHANNEL_COL = 240;
  const MARKET_COL = 76;

  return (
    <>
      <section>
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Records by channel and market</h2>
        <div className="overflow-x-auto">
          <table className="table-fixed text-sm" style={{ width: CHANNEL_COL + markets.length * MARKET_COL }}>
            <colgroup>
              <col style={{ width: CHANNEL_COL }} />
              {markets.map((m) => (
                <col key={m} style={{ width: MARKET_COL }} />
              ))}
            </colgroup>
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th scope="col" className="px-2 py-2.5 text-left font-normal">
                  Channel
                </th>
                {markets.map((m) => (
                  <th key={m} scope="col" className="px-2 py-2.5 text-right font-mono font-normal">
                    {m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {streams.map((stream) => (
                <Fragment key={stream}>
                  <tr>
                    <th scope="colgroup" colSpan={markets.length + 1} className="px-2 pt-4 pb-1 text-left text-xs font-medium">
                      {streamLabel(stream)}
                    </th>
                  </tr>
                  {channels
                    .filter((c) => streamOf.get(c) === stream)
                    .map((channel) => (
                      <tr key={channel} className="border-t border-border/60">
                        <th scope="row" className="px-2 py-2 text-left font-normal">
                          <Link href={recordsHref({ channel })} title={channelLabel(channel)} className="flex min-w-0 items-center gap-1.5 hover:underline">
                            <ChannelIcon channel={channel} />
                            <span className="truncate">{channelLabel(channel)}</span>
                          </Link>
                        </th>
                        {markets.map((market) => {
                          const n = cells ? (matrix.get(`${channel}|${market}`) ?? 0) : undefined;
                          return (
                            <td key={market} className="px-2 py-2 text-right tabular-nums">
                              {n === undefined ? (
                                <span className="text-muted-foreground/50">·</span>
                              ) : n === 0 ? (
                                <span className="text-muted-foreground/60" title={`No records tagged ${market} in ${channelLabel(channel)}`}>
                                  –
                                </span>
                              ) : (
                                <Link href={recordsHref({ channel, market })} className="hover:underline">
                                  {fmtCount(n)}
                                </Link>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 px-2 text-xs text-muted-foreground">
          {cells
            ? "Counted exactly as tagged: a record tagged DE is not counted under EU, a record with two markets counts in both. Click a number to see the records."
            : "This API version does not return the market matrix yet."}{" "}
          {coverage.llm_rule}
        </p>
      </section>

      {missing && missing.length > 0 && (
        <section className="max-w-xl">
          <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Gaps in the target markets</h2>
          <ul className="flex flex-col">
            {missing.map((m) => (
              <li key={m} className="border-b border-border/60 px-2 py-2 text-sm text-amber-800 dark:text-amber-200">
                {m}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
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
          <Link href="/sources?tab=list" className="text-foreground hover:underline">
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
              <Link href={`/sources/${encodeURIComponent(source.source_id)}`} className="truncate font-medium hover:underline">
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

function Records({ initial }: { initial: { market?: string; channel?: string; ids: string[] } }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [market, setMarket] = useState<string | undefined>(initial.market);
  const [offset, setOffset] = useState(0);
  const channel = initial.channel;
  const ids = initial.ids;
  const { data: meta } = useMeta();
  const { data: sources } = useSources();
  const { data, error, isLoading } = useRecords({ q, market, channel, ids, offset });
  const bySource = new Map((sources ?? []).map((s) => [s.source_id, s]));
  const filtered = !!channel || ids.length > 0;

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
            {ids.length > 0 ? `${ids.length} selected record${ids.length === 1 ? "" : "s"}` : channelLabel(channel)}
            <Button size="xs" variant="ghost" onClick={() => router.replace("/sources?tab=records")}>
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
