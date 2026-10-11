"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { CondenseButton, DraftSelectedDialog, RebuildSignalsButton } from "@/components/generate-dialog";
import { PageHeader } from "@/components/page-header";
import { SignalChart } from "@/components/signal-chart";
import { ChannelIcon } from "@/components/provenance";
import { ErrorState, LoadingRows } from "@/components/states";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useHash } from "@/hooks/use-hash";
import { useMeta, useRequirements, useSignals } from "@/lib/api/hooks";
import type { Finding, Requirement, Signal, SignalKind } from "@/lib/api/types";
import { fmtCount, humanize } from "@/lib/format";
import { channelLabel } from "@/lib/provenance";
import { cn } from "cn";

const COLUMNS: { kind: SignalKind; title: string }[] = [
  { kind: "pain", title: "Pain points" },
  { kind: "request", title: "Requests" },
  { kind: "strength", title: "Strengths" },
];

// At most this many signals per column and findings per signal on the first level.
const FIRST_LEVEL = 6;
const FINDINGS_SHOWN = 3;

const MIX = [
  { key: "pain", label: "pain", color: "bg-red-400" },
  { key: "requests", label: "request", color: "bg-sky-500" },
  { key: "praise", label: "praise", color: "bg-emerald-500" },
] as const;

export default function SignalsPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <SignalsView />
    </Suspense>
  );
}

// ?market=US|EU|CN|all picks the market; #sig-<feature_key> highlights one signal (links from a requirement's origin).
function SignalsView() {
  const params = useSearchParams();
  const initial = params.get("market");
  const { data: meta } = useMeta();
  const [market, setMarket] = useState<string | null>(initial === "all" ? null : (initial ?? "US"));
  const markets: (string | null)[] = [...(meta?.markets ?? ["US", "EU", "CN"]), null];

  return (
    <>
      <PageHeader crumbs={[{ label: "Signals" }]} market={{ value: market, onChange: setMarket, options: markets }}>
        <RebuildSignalsButton />
        <CondenseButton />
      </PageHeader>
      <p className="mt-1 text-[13px] text-muted-foreground">What do customers tell us?</p>

      {/* Keyed by market so the selection starts empty for every market. */}
      <SignalBoard key={market ?? "all"} market={market} />
    </>
  );
}

function SignalBoard({ market }: { market: string | null }) {
  const [selected, setSelected] = useState<Map<string, Signal>>(new Map());
  const { data: requirements } = useRequirements();
  const mixed = useSignals(market, "mixed", 100);
  const toggle = (s: Signal) =>
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(s.feature_key)) next.delete(s.feature_key);
      else next.set(s.feature_key, s);
      return next;
    });
  // Signals that already became a requirement link to it; pooled signals match requirements without a market.
  const requirementFor = (s: Signal) => requirements?.find((r) => r.feature_key === s.feature_key && (r.market ?? null) === (s.market ?? null));

  return (
    <div className="mt-4 flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="flex max-w-xl flex-col gap-3 text-xs text-muted-foreground">
          {mixed.data?.basis && <span>{mixed.data.basis}</span>}
          <span className="flex items-center gap-3">
            {MIX.map((m) => (
              <span key={m.key} className="flex items-center gap-1">
                <span className={cn("size-2 rounded-sm", m.color)} aria-hidden />
                {m.label}
              </span>
            ))}
          </span>
          <span className="flex items-center gap-3">
            <DraftSelectedDialog market={market} selected={[...selected.values()]} onDone={() => setSelected(new Map())} />
            {selected.size > 0 && (
              <button type="button" className="hover:text-foreground" onClick={() => setSelected(new Map())}>
                Clear selection
              </button>
            )}
          </span>
        </div>
        <SignalChart market={market} />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {COLUMNS.map((c) => (
          <SignalColumn key={c.kind} market={market} kind={c.kind} title={c.title} selected={selected} onToggle={toggle} requirementFor={requirementFor} />
        ))}
      </div>

      {mixed.data && mixed.data.items.length > 0 && (
        <HoverCard openDelay={100}>
          <HoverCardTrigger asChild>
            <button type="button" className="self-start text-xs text-muted-foreground underline decoration-dotted underline-offset-4">
              {mixed.data.items.length} mixed signal{mixed.data.items.length === 1 ? "" : "s"} fit none of the three columns
            </button>
          </HoverCardTrigger>
          <HoverCardContent align="start" className="w-80 text-xs">
            <p className="mb-1.5 text-muted-foreground">Neither clearly pain, praise nor request:</p>
            <ul className="flex flex-col gap-0.5">
              {mixed.data.items.map((s) => (
                <li key={s.feature_key} className="flex justify-between gap-3">
                  <span className="truncate">{s.label}</span>
                  <span className="text-muted-foreground tabular-nums">{s.reviews}</span>
                </li>
              ))}
            </ul>
          </HoverCardContent>
        </HoverCard>
      )}
    </div>
  );
}

function SignalColumn({
  market,
  kind,
  title,
  selected,
  onToggle,
  requirementFor,
}: {
  market: string | null;
  kind: SignalKind;
  title: string;
  selected: Map<string, Signal>;
  onToggle: (s: Signal) => void;
  requirementFor: (s: Signal) => Requirement | undefined;
}) {
  const { data, error, isLoading } = useSignals(market, kind, 15);
  const hash = useHash();
  const found = !!data?.items.some((s) => `sig-${s.feature_key}` === hash);
  const [more, setMore] = useState(false);
  const items = data?.items ?? [];
  // A linked signal beyond the first level opens the column so it can be highlighted.
  const shown = more || items.slice(FIRST_LEVEL).some((s) => `sig-${s.feature_key}` === hash) ? items : items.slice(0, FIRST_LEVEL);
  useEffect(() => {
    if (found) document.getElementById(hash)?.scrollIntoView({ block: "center" });
  }, [found, hash]);
  return (
    <section className="flex min-w-0 flex-col">
      <h2 className="flex items-baseline gap-2 border-b pb-2.5 text-[13px] font-medium">
        {title}
        {data && <span className="font-normal text-muted-foreground/70">{data.items.length}</span>}
      </h2>
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && data.items.length === 0 && <p className="py-3 text-[13px] text-muted-foreground">None in this market.</p>}
      <ul>
        {shown.map((s) => (
          <SignalRow
            key={s.feature_key}
            signal={s}
            checked={selected.has(s.feature_key)}
            onToggle={() => onToggle(s)}
            requirement={requirementFor(s)}
            active={hash === `sig-${s.feature_key}`}
          />
        ))}
      </ul>
      {items.length > shown.length && (
        <button type="button" onClick={() => setMore(true)} className="self-start py-2 text-xs text-muted-foreground hover:text-foreground">
          Show {items.length - shown.length} more
        </button>
      )}
    </section>
  );
}

function SignalRow({
  signal: s,
  checked,
  onToggle,
  requirement,
  active,
}: {
  signal: Signal;
  checked: boolean;
  onToggle: () => void;
  requirement?: Requirement;
  active: boolean;
}) {
  const drafted = s.has_requirement || !!requirement;
  return (
    <li id={`sig-${s.feature_key}`} className={cn("-mx-2 flex scroll-mt-24 gap-2.5 rounded-md border-b border-border/60 px-2 py-3", active && "bg-amber-50/70 dark:bg-amber-950/40")}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        disabled={drafted}
        aria-label={drafted ? `${s.label} already has a requirement` : `Select ${s.label}`}
        className="mt-1 size-3.5 shrink-0 accent-foreground disabled:opacity-30"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-baseline gap-2">
          <HoverCard openDelay={120}>
            <HoverCardTrigger asChild>
              <button type="button" className="min-w-0 truncate text-left text-sm font-medium hover:underline" onClick={drafted ? undefined : onToggle}>
                {s.label}
              </button>
            </HoverCardTrigger>
            <HoverCardContent align="start" className="w-80 text-xs">
              {s.sample_quotes.length === 0 ? (
                <p className="text-muted-foreground">No quote is cleared for display.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {s.sample_quotes.map((q) => (
                    <div key={q.record_id} className="flex flex-col gap-0.5">
                      <p className="line-clamp-4">“{q.text}”</p>
                      <Link href={`/sources?tab=records&ids=${encodeURIComponent(q.record_id)}`} className="font-mono text-muted-foreground hover:underline">
                        {q.record_id}
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </HoverCardContent>
          </HoverCard>
          <span className="ml-auto shrink-0 text-xs text-muted-foreground tabular-nums">{fmtCount(s.reviews)} reviews</span>
        </div>
        <MixBar signal={s} />
        {s.findings && s.findings.length > 0 && <Findings findings={s.findings} reviews={s.reviews} />}
        <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
          <span className="flex min-w-0 items-center gap-1.5 truncate">
            {s.channels.slice(0, 3).map((c) => (
              <span key={c} className="flex items-center gap-1">
                <ChannelIcon channel={c} className="size-3" />
                {channelLabel(c)}
              </span>
            ))}
            {s.channels.length > 3 && <span>+{s.channels.length - 3}</span>}
          </span>
          {requirement ? (
            <Link href={`/requirements/${encodeURIComponent(requirement.id)}`} className="ml-auto shrink-0 text-foreground hover:underline">
              {requirement.id}
            </Link>
          ) : (
            s.has_requirement && <span className="ml-auto shrink-0">has a requirement</span>
          )}
        </div>
      </div>
    </li>
  );
}

// Pain, request and praise reviews as parts of all reviews; the grey rest are plain mentions.
function MixBar({ signal: s }: { signal: Signal }) {
  const total = Math.max(s.reviews, s.pain + s.requests + s.praise, 1);
  return (
    <div
      className="flex h-1.5 overflow-hidden rounded-full bg-muted"
      title={`${s.pain} pain · ${s.requests} request · ${s.praise} praise of ${s.reviews} reviews`}
    >
      {MIX.map((m) => (
        <span key={m.key} className={m.color} style={{ width: `${(s[m.key] / total) * 100}%` }} />
      ))}
    </div>
  );
}

// Concrete findings behind a signal: the model grouped the reviews, the counts come from code.
function Findings({ findings, reviews }: { findings: Finding[]; reviews: number }) {
  const [all, setAll] = useState(false);
  const shown = all ? findings : findings.slice(0, FINDINGS_SHOWN);
  return (
    <ul className="flex flex-col gap-0.5 border-l border-border pl-2.5">
      {shown.map((f) => (
        <li key={f.id}>
          <HoverCard openDelay={120} closeDelay={60}>
            <HoverCardTrigger asChild>
              <button type="button" className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-2 text-left text-xs">
                <span className="truncate">{f.title}</span>
                <span className="text-muted-foreground tabular-nums">{fmtCount(f.reviews)}</span>
                <span className="w-9 text-right text-muted-foreground/70 tabular-nums">{Math.round(f.share_of_theme * 100)} %</span>
              </button>
            </HoverCardTrigger>
            <HoverCardContent align="start" className="w-80 text-xs">
              <p className="font-medium">{f.title}</p>
              {f.description && <p className="mt-0.5 text-muted-foreground">{f.description}</p>}
              <p className="mt-1 text-muted-foreground">
                {fmtCount(f.reviews)} of {fmtCount(reviews)} reviews · {humanize(f.kind)}
              </p>
              <div className="mt-2 flex flex-col gap-2">
                {f.quotes.slice(0, 3).map((q) => (
                  <div key={q.record_id} className="flex flex-col gap-0.5">
                    <p className="line-clamp-3">“{q.text}”</p>
                    <Link href={`/sources?tab=records&ids=${encodeURIComponent(q.record_id)}`} className="font-mono text-muted-foreground hover:underline">
                      {q.record_id}
                    </Link>
                  </div>
                ))}
              </div>
            </HoverCardContent>
          </HoverCard>
        </li>
      ))}
      {findings.length > shown.length && (
        <li>
          <button type="button" onClick={() => setAll(true)} className="text-[11px] text-muted-foreground hover:text-foreground">
            +{findings.length - shown.length} more findings
          </button>
        </li>
      )}
    </ul>
  );
}
