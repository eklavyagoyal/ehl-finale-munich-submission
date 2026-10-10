"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { DraftDialog, RebuildSignalsButton } from "@/components/generate-dialog";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { refreshAll, reviewSource, useCoverage, useMeta, useRecords, useSources, useThemes } from "@/lib/api/hooks";
import type { Source } from "@/lib/api/types";
import { fmtDateTime, humanize, type Tone } from "@/lib/format";
import { cn } from "cn";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "sources", label: "Sources" },
  { key: "records", label: "Records" },
  { key: "signals", label: "Signals" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

const REVIEW_TONE: Record<string, Tone> = { accepted: "green", rejected: "red", pending: "amber" };

export default function DataPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <DataView />
    </Suspense>
  );
}

function DataView() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "overview") as TabKey;
  const sources = useSources();
  const coverage = useCoverage();
  const records = coverage.data?.records_by_channel.reduce((n, r) => n + r.records, 0);
  const counts: Partial<Record<TabKey, number | undefined>> = { sources: sources.data?.length, records };

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "Data" }]}>
        {tab === "signals" && (
          <>
            <RebuildSignalsButton />
            <DraftDialog />
          </>
        )}
      </PageHeader>

      <nav aria-label="Data views" className="-ml-2.5 mt-2 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => router.replace(t.key === "overview" ? "/data" : `/data?tab=${t.key}`)}
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
        {tab === "sources" && <Sources />}
        {tab === "records" && <Records />}
        {tab === "signals" && <Signals />}
      </div>
    </>
  );
}

function Overview() {
  const { data, error, isLoading } = useCoverage();
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
  const maxMarket = Math.max(1, ...data.records_by_market.map((m) => m.records));
  const claims = data.claims.reduce((n, c) => n + c.claims, 0);

  return (
    <div className="flex flex-col gap-10">
      <p className="text-sm text-muted-foreground">
        <span className="text-foreground tabular-nums">{total}</span> records ·{" "}
        <span className="text-foreground tabular-nums">{claims}</span> extracted claims · {data.llm_rule}
      </p>

      <section>
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">By channel</h2>
        {data.records_by_channel.map((r, i) => (
          <div key={i} className="grid grid-cols-[minmax(0,1fr)_110px_110px_70px] items-center gap-4 border-b border-border/60 px-2 py-2.5 text-sm">
            <span>
              {humanize(r.channel)} <span className="text-muted-foreground">· {r.stream}</span>
            </span>
            <span>
              <ToneBadge tone={REVIEW_TONE[r.review_status] ?? "muted"}>{r.review_status}</ToneBadge>
            </span>
            <span className="text-xs text-muted-foreground">{r.external_llm ? "LLM allowed" : "no external LLM"}</span>
            <span className="text-right tabular-nums">{r.records}</span>
          </div>
        ))}
      </section>

      <section className="max-w-xl">
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">By market</h2>
        {data.records_by_market.map((m) => (
          <div key={m.market ?? "none"} className="grid grid-cols-[60px_minmax(0,1fr)_50px] items-center gap-4 border-b border-border/60 px-2 py-2.5 text-sm">
            <span className="font-mono text-xs">{m.market ?? "–"}</span>
            <span className="relative h-1 rounded-full bg-muted" aria-hidden>
              <span className="absolute inset-y-0 left-0 rounded-full bg-foreground" style={{ width: `${(m.records / maxMarket) * 100}%` }} />
            </span>
            <span className="text-right tabular-nums">{m.records}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

function Sources() {
  const { data, error, isLoading } = useSources();
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  if (data.length === 0) return <EmptyState title="No sources yet">Sources appear once the backend has ingested research batches.</EmptyState>;
  return (
    <section>
      <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_100px_150px] gap-4 px-2 py-2.5 text-xs text-muted-foreground">
        <span>Source</span>
        <span>Channel</span>
        <span className="text-right">Records</span>
        <span>Review</span>
        <span />
      </div>
      {data.map((s) => (
        <SourceRow key={s.source_id} source={s} />
      ))}
    </section>
  );
}

function SourceRow({ source }: { source: Source }) {
  const [deciding, setDeciding] = useState<"accepted" | "rejected" | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    if (!deciding) return;
    if (!note.trim()) {
      toast.error("Add a short note why.");
      return;
    }
    setBusy(true);
    try {
      await reviewSource(source.source_id, deciding, note.trim());
      toast.success(`${source.title}: ${deciding}`);
      await refreshAll();
      setDeciding(null);
      setNote("");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-border/60 px-2 py-3 text-sm">
      <div className="grid grid-cols-[minmax(0,1fr)_170px_70px_100px_150px] items-center gap-4">
        <span className="min-w-0">
          <span className="block truncate font-medium">{source.title}</span>
          <span className="block truncate font-mono text-xs text-muted-foreground">
            {source.source_id}
            {source.collected_at && ` · ${fmtDateTime(source.collected_at)}`}
          </span>
        </span>
        <span className="truncate text-[13px] text-muted-foreground">
          {humanize(source.channel)} · {source.stream}
          {source.is_example && " · example"}
        </span>
        <span className="text-right tabular-nums">{source.normalized_record_count}</span>
        <span>
          <ToneBadge tone={REVIEW_TONE[source.review_status] ?? "muted"}>{source.review_status}</ToneBadge>
        </span>
        <span className="flex justify-end gap-1">
          {source.review_status !== "accepted" && (
            <Button size="xs" variant="outline" onClick={() => setDeciding("accepted")}>
              Accept
            </Button>
          )}
          {source.review_status !== "rejected" && (
            <Button size="xs" variant="ghost" onClick={() => setDeciding("rejected")}>
              Reject
            </Button>
          )}
        </span>
      </div>
      {deciding && (
        <div className="mt-2 flex items-center gap-2">
          <Input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={deciding === "accepted" ? "Why can this evidence be used?" : "Why is this evidence rejected?"}
            aria-label="Review note"
            className="h-8 max-w-md"
          />
          <Button size="sm" onClick={save} disabled={busy}>
            {busy ? "Saving…" : deciding === "accepted" ? "Accept" : "Reject"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setDeciding(null)}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}

function Records() {
  const [q, setQ] = useState("");
  const [market, setMarket] = useState<string | undefined>();
  const [offset, setOffset] = useState(0);
  const { data: meta } = useMeta();
  const { data, error, isLoading } = useRecords({ q, market, offset });

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
            {(meta?.markets ?? ["US", "EU", "CN"]).map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data && <span className="ml-auto text-xs text-muted-foreground tabular-nums">{data.total} records</span>}
      </div>

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && data.items.length === 0 && <EmptyState title="No records match" />}
      <div>
        {data?.items.map((r) => (
          <div key={r.record_id} className="grid grid-cols-[minmax(0,1fr)_200px] gap-6 border-t border-border/60 px-2 py-3 text-sm">
            <p className="line-clamp-2">{r.translation_en ?? r.text_original ?? "–"}</p>
            <span className="flex min-w-0 flex-col gap-0.5 text-xs text-muted-foreground">
              <span className="truncate font-mono">{r.record_id}</span>
              <span className="truncate">
                {humanize(r.channel)} · {humanize(r.record_kind)}
                {r.markets.length ? ` · ${r.markets.join(", ")}` : ""}
              </span>
            </span>
          </div>
        ))}
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
        Signals are counted by code, not by a model: distinct reviews per feature and market. The drafter only uses signals that have no
        requirement yet. <Link href="/requirements" className="text-foreground underline-offset-4 hover:underline">See requirements</Link>
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
      {data && data.items.length === 0 && (
        <EmptyState title="No signals for this market">Rebuild signals after new evidence has been accepted.</EmptyState>
      )}
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
                <span className="block truncate text-xs text-muted-foreground">{t.channels.map(humanize).join(", ")}</span>
              </span>
              <span className="truncate text-[13px] text-muted-foreground">{humanize(t.area)}</span>
              <span className="text-right tabular-nums">{t.mention_review_count}</span>
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
