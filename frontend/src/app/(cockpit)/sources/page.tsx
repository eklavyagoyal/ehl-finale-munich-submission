"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { DraftDialog, RebuildSignalsButton } from "@/components/generate-dialog";
import { PageHeader } from "@/components/page-header";
import { ChannelIcon, SourceHoverCard, SyntheticBadge } from "@/components/provenance";
import { REVIEW_TONE, SourceReview } from "@/components/source-review";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCoverage, useMeta, useRecords, useSources, useThemes } from "@/lib/api/hooks";
import type { Source, Theme } from "@/lib/api/types";
import { fmtDateTime, humanize } from "@/lib/format";
import { channelLabel, isSynthetic, llmPermission, STREAM_ORDER, streamLabel, toSummary } from "@/lib/provenance";
import { cn } from "cn";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "list", label: "Sources" },
  { key: "records", label: "Records" },
  { key: "signals", label: "Signals" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

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
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "overview") as TabKey;
  const sources = useSources();
  const coverage = useCoverage();
  const records = coverage.data?.records_by_channel.reduce((n, r) => n + r.records, 0);
  const counts: Partial<Record<TabKey, number | undefined>> = { list: sources.data?.length, records };

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "Sources" }]}>
        {tab === "signals" && (
          <>
            <RebuildSignalsButton />
            <DraftDialog />
          </>
        )}
      </PageHeader>

      <nav aria-label="Source views" className="-ml-2.5 mt-2 flex flex-wrap gap-1">
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
            {counts[t.key] !== undefined && <span className="font-normal text-muted-foreground/70">{counts[t.key]}</span>}
          </button>
        ))}
      </nav>

      <div className="mt-6 max-w-5xl">
        {tab === "overview" && <Overview />}
        {tab === "list" && <SourceList />}
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
        {tab === "signals" && <Signals />}
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

  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  const total = data.records_by_channel.reduce((n, r) => n + r.records, 0);
  if (total === 0) {
    return (
      <EmptyState title="No evidence imported yet">
        Requirements appear once research batches are ingested and accepted. The import itself runs in the backend.
      </EmptyState>
    );
  }

  // One request for the whole matrix: records_by_channel_market from /coverage.
  const cells = data.records_by_channel_market;
  const matrix = new Map((cells ?? []).map((c) => [`${c.channel}|${c.market}`, c.records]));
  const channels = [...new Set([...data.records_by_channel.map((r) => r.channel), ...(cells ?? []).map((c) => c.channel)])];
  const tagged = data.records_by_market.map((m) => m.market).filter((m): m is string => !!m);
  const markets = [...new Set([...(meta?.markets ?? []), ...tagged])];
  const streamOf = new Map([...(cells ?? []), ...data.records_by_channel].map((r) => [r.channel, r.stream]));
  const streams = [...new Set(streamOf.values())].sort(
    (a, b) => (STREAM_ORDER.indexOf(a) + 99) % 99 - (STREAM_ORDER.indexOf(b) + 99) % 99,
  );
  const claims = data.claims.reduce((n, c) => n + c.claims, 0);
  const syntheticCount = (sources ?? []).filter(isSynthetic).length;
  const targetMarkets = meta?.markets ?? [];
  const missing =
    cells &&
    streams.flatMap((stream) =>
      targetMarkets
        .filter((market) => channels.filter((c) => streamOf.get(c) === stream).every((c) => (matrix.get(`${c}|${market}`) ?? 0) === 0))
        .map((market) => `No ${streamLabel(stream)} records tagged ${market}`),
    );

  return (
    <div className="flex flex-col gap-10">
      <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Link href="/sources?tab=records" className="text-foreground tabular-nums hover:underline">
          {total}
        </Link>{" "}
        records ·
        <HoverCard openDelay={100} closeDelay={60}>
          <HoverCardTrigger asChild>
            <button type="button" className="text-foreground tabular-nums underline decoration-dotted underline-offset-4">
              {claims}
            </button>
          </HoverCardTrigger>
          <HoverCardContent align="start" className="w-64 text-xs">
            <p className="mb-1.5 text-muted-foreground">Interpretations of records, by origin and review:</p>
            {data.claims.map((c, i) => (
              <p key={i} className="flex justify-between gap-3">
                <span>
                  {c.derived_from_bmw_labels ? "From BMW labels" : "Not from BMW labels"} · {c.review_status}
                </span>
                <span className="tabular-nums">{c.claims}</span>
              </p>
            ))}
          </HoverCardContent>
        </HoverCard>
        interpretations (claims) ·
        <Link href="/sources?tab=list" className="text-foreground tabular-nums hover:underline">
          {sources?.length ?? "–"}
        </Link>{" "}
        sources
        {sources && syntheticCount > 0 && (
          <span className="flex items-center gap-1.5">
            ·<SyntheticBadge />
            {syntheticCount === sources.length ? "all of them invented test data" : `${syntheticCount} invented`}
          </span>
        )}
      </p>

      <section>
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Records by channel and market</h2>
        <div className="overflow-x-auto">
          <div className="min-w-[640px]">
            <div className="grid gap-4 px-2 py-2.5 text-xs text-muted-foreground" style={{ gridTemplateColumns: `minmax(0,1fr) repeat(${markets.length}, 64px)` }}>
              <span>Channel</span>
              {markets.map((m) => (
                <span key={m} className="text-right font-mono">
                  {m}
                </span>
              ))}
            </div>
            {streams.map((stream) => (
              <div key={stream}>
                <p className="px-2 pt-3 pb-1 text-xs font-medium">{streamLabel(stream)}</p>
                {channels
                  .filter((c) => streamOf.get(c) === stream)
                  .map((channel) => (
                    <div
                      key={channel}
                      className="grid items-center gap-4 border-t border-border/60 px-2 py-2 text-sm"
                      style={{ gridTemplateColumns: `minmax(0,1fr) repeat(${markets.length}, 64px)` }}
                    >
                      <Link href={recordsHref({ channel })} className="flex items-center gap-1.5 hover:underline">
                        <ChannelIcon channel={channel} />
                        {channelLabel(channel)}
                      </Link>
                      {markets.map((market) => {
                        const n = cells ? (matrix.get(`${channel}|${market}`) ?? 0) : undefined;
                        return (
                          <span key={market} className="text-right tabular-nums">
                            {n === undefined ? (
                              <span className="text-muted-foreground/50">·</span>
                            ) : n === 0 ? (
                              <span className="text-muted-foreground/60" title={`No records tagged ${market} in ${channelLabel(channel)}`}>
                                –
                              </span>
                            ) : (
                              <Link href={recordsHref({ channel, market })} className="hover:underline">
                                {n}
                              </Link>
                            )}
                          </span>
                        );
                      })}
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>
        <p className="mt-2 px-2 text-xs text-muted-foreground">
          {cells
            ? "Counted exactly as tagged: a record tagged DE is not counted under EU, a record with two markets counts in both. Click a number to see the records."
            : "This API version does not return the market matrix yet."}
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

      <section className="max-w-2xl">
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Review state and model access</h2>
        {data.records_by_channel.map((r, i) => (
          <div key={i} className="grid grid-cols-[minmax(0,1fr)_100px_120px_50px] items-center gap-4 border-b border-border/60 px-2 py-2 text-sm">
            <span className="flex items-center gap-1.5">
              <ChannelIcon channel={r.channel} />
              {channelLabel(r.channel)}
            </span>
            <span>
              <ToneBadge tone={REVIEW_TONE[r.review_status] ?? "muted"}>{r.review_status}</ToneBadge>
            </span>
            <span className="text-xs text-muted-foreground">to OpenAI: {llmPermission(r.external_llm, r.review_status)}</span>
            <span className="text-right tabular-nums">{r.records}</span>
          </div>
        ))}
        <p className="mt-2 px-2 text-xs text-muted-foreground">{data.llm_rule}</p>
      </section>
    </div>
  );
}

function SourceList() {
  const { data, error, isLoading } = useSources();
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  if (data.length === 0) return <EmptyState title="No sources yet">Sources appear once the backend has ingested research batches.</EmptyState>;
  const order = (s: Source) => (STREAM_ORDER.indexOf(s.stream) + 99) % 99;
  return (
    <section>
      <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_100px_150px] gap-4 px-2 py-2.5 text-xs text-muted-foreground">
        <span>Source</span>
        <span>Channel</span>
        <span className="text-right">Records</span>
        <span>Review</span>
        <span />
      </div>
      {[...data]
        .sort((a, b) => order(a) - order(b))
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

function Signals() {
  const { data: meta } = useMeta();
  const [market, setMarket] = useState<string | undefined>("US");
  const { data, error, isLoading } = useThemes(market);
  const markets = [...(meta?.markets ?? ["US", "EU", "CN"]), undefined];

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Counted by code, not by a model: distinct reviews per feature and market. Hover a count to see the channels behind it.
      </p>
      <div className="-ml-2.5 flex flex-wrap gap-1">
        {markets.map((m) => (
          <button
            key={m ?? "pooled"}
            type="button"
            onClick={() => setMarket(m)}
            className={cn(
              "h-8 rounded-lg px-2.5 text-[13px]",
              market === m ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {m ?? "Pooled"}
          </button>
        ))}
      </div>

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && data.items.length === 0 && <EmptyState title="No signals for this market">Rebuild signals after new evidence has been accepted.</EmptyState>}
      {data && data.items.length > 0 && (
        <div>
          <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_70px_70px_70px] gap-4 px-2 py-2.5 text-xs text-muted-foreground">
            <span>Feature</span>
            <span>Area</span>
            <span className="text-right">Reviews</span>
            <span className="text-right">Requests</span>
            <span className="text-right">Pains</span>
            <span className="text-right">Praise</span>
          </div>
          {data.items.map((t) => (
            <div key={t.id} className="grid grid-cols-[minmax(0,1fr)_170px_70px_70px_70px_70px] items-center gap-4 border-t border-border/60 px-2 py-2.5 text-sm">
              <span className="min-w-0">
                <span className="block truncate font-medium">{t.label}</span>
                <span className="block truncate text-xs text-muted-foreground">{t.channels.map(channelLabel).join(", ")}</span>
              </span>
              <span className="truncate text-[13px] text-muted-foreground">{humanize(t.area)}</span>
              <span className="text-right tabular-nums">
                <Cohorts theme={t} />
              </span>
              <span className="text-right tabular-nums">{t.request_review_count}</span>
              <span className="text-right tabular-nums">{t.pain_review_count}</span>
              <span className="text-right tabular-nums">{t.praise_review_count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Cohorts({ theme }: { theme: Theme }) {
  if (!theme.cohorts?.length) return <>{theme.mention_review_count}</>;
  return (
    <HoverCard openDelay={100}>
      <HoverCardTrigger asChild>
        <button type="button" className="underline decoration-dotted underline-offset-4">
          {theme.mention_review_count}
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="end" className="w-80 text-left text-xs">
        <p className="mb-2 text-muted-foreground">Where the {theme.mention_review_count} reviews come from</p>
        <div className="flex flex-col gap-1.5">
          {theme.cohorts.map((c, i) => (
            <div key={i} className="flex flex-col gap-0.5">
              <p className="flex items-center gap-1.5 font-medium">
                <ChannelIcon channel={c.channel} className="size-3" />
                {channelLabel(c.channel)} · {c.mention_review_count}
                {c.feedback_review_count ? <span className="font-normal text-muted-foreground"> of {c.feedback_review_count}</span> : null}
              </p>
              <p className="text-muted-foreground">
                {c.markets.join(", ") || "no market"} · {c.dataset_key}
                {c.collection_method ? ` · ${c.collection_method}` : ""}
              </p>
            </div>
          ))}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
