"use client";

import { ChannelIcon, InterpretationBadge, QuoteText, SourceHoverCard, StreamBadge, SyntheticBadge } from "@/components/provenance";
import { EmptyState } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useLlmCalls } from "@/lib/api/hooks";
import type { EvidenceLink } from "@/lib/api/types";
import { actorLabel } from "@/lib/format";
import { channelLabel, isSynthetic, STREAM_ORDER, streamLabel } from "@/lib/provenance";

import { useRequirementContext } from "./context";

export function EvidenceTab() {
  const { id, detail, runId } = useRequirementContext();
  const calls = useLlmCalls(runId, id, false);
  if (!detail) return null;
  const evidence = detail.evidence;

  if (evidence.length === 0) {
    return (
      <EmptyState title="No linked evidence">
        This requirement has no linked reviews or study records yet. Without evidence the traceability gate cannot pass.
      </EmptyState>
    );
  }

  // Which agents saw which record, from the latest run's model calls.
  const seenBy = new Map<string, Set<string>>();
  for (const call of calls.data ?? []) {
    for (const record of call.input_record_ids) {
      if (!seenBy.has(record)) seenBy.set(record, new Set());
      seenBy.get(record)!.add(call.agent_id);
    }
  }

  const streams = new Map<string, Map<string, EvidenceLink[]>>();
  for (const item of evidence) {
    const stream = item.source?.stream ?? "unknown";
    const channel = item.source?.channel ?? "unknown";
    if (!streams.has(stream)) streams.set(stream, new Map());
    const channels = streams.get(stream)!;
    channels.set(channel, [...(channels.get(channel) ?? []), item]);
  }
  const order = (s: string) => (STREAM_ORDER.indexOf(s) >= 0 ? STREAM_ORDER.indexOf(s) : 99);
  const synthetic = evidence.filter((e) => isSynthetic(e.source)).length;

  return (
    <div className="flex max-w-5xl flex-col gap-9">
      {synthetic > 0 && (
        <p className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <SyntheticBadge />
          {synthetic === evidence.length ? "All evidence here is invented test data." : `${synthetic} of ${evidence.length} records are invented test data.`}
        </p>
      )}
      {[...streams.entries()]
        .sort(([a], [b]) => order(a) - order(b))
        .map(([stream, channels]) => (
          <section key={stream} className="flex flex-col gap-5">
            <h2 className="flex items-baseline gap-2 border-b px-2 pb-2.5 text-[13px] font-medium">
              {streamLabel(stream)}
              <span className="font-normal text-muted-foreground/70">{[...channels.values()].reduce((n, l) => n + l.length, 0)}</span>
            </h2>
            {[...channels.entries()].map(([channel, items]) => (
              <div key={channel}>
                <h3 className="flex items-center gap-1.5 px-2 pb-1 text-xs text-muted-foreground">
                  <ChannelIcon channel={channel} />
                  {channelLabel(channel)} <span className="text-muted-foreground/60">{items.length}</span>
                </h3>
                {items.map((item) => (
                  <EvidenceRow key={item.id} item={item} seenBy={seenBy.get(item.record_id)} />
                ))}
              </div>
            ))}
          </section>
        ))}
    </div>
  );
}

function EvidenceRow({ item, seenBy }: { item: EvidenceLink; seenBy?: Set<string> }) {
  const record = item.record;
  return (
    <div
      id={`rec-${item.record_id}`}
      className="grid scroll-mt-24 grid-cols-[minmax(0,1fr)_230px] gap-6 rounded-md border-b border-border/60 px-2 py-3 text-sm target:bg-amber-50/70 dark:target:bg-amber-950/40"
    >
      <div className="flex min-w-0 flex-col gap-2">
        <QuoteText text={record.translation_en ?? record.text} quote={item.quote} verified={item.quote_verified} />
        {record.translation_en && record.text && <p className="text-xs text-muted-foreground">Original ({record.language ?? "?"}): {record.text}</p>}
        <div className="flex flex-wrap items-center gap-1.5">
          <StreamBadge stream={item.source?.stream} channel={item.source?.channel} />
          <InterpretationBadge claims={item.claims} />
          {item.relation === "contradicting" && <ToneBadge tone="red">contradicting</ToneBadge>}
          {item.relation === "context" && <ToneBadge tone="muted">context</ToneBadge>}
          {isSynthetic(item.source) && <SyntheticBadge />}
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-0.5 text-xs text-muted-foreground">
        <SourceHoverCard source={item.source}>
          <button type="button" className="truncate text-left text-foreground/80 underline-offset-4 hover:underline">
            {item.source?.title}
          </button>
        </SourceHoverCard>
        <span className="truncate font-mono">{item.record_id}</span>
        <span className="truncate">
          {record.markets.join(", ") || "no market"}
          {record.locator && typeof record.locator === "object" && "content_date" in record.locator && record.locator.content_date
            ? ` · ${String(record.locator.content_date)}`
            : ""}
        </span>
        <span>linked by {actorLabel(item.added_by)}</span>
        {seenBy && seenBy.size > 0 && (
          <HoverCard openDelay={120}>
            <HoverCardTrigger asChild>
              <button type="button" className="flex items-center gap-1.5 text-left">
                <span className="size-1.5 rounded-full bg-blue-600" aria-hidden />
                seen by {seenBy.size} agent{seenBy.size === 1 ? "" : "s"}
              </button>
            </HoverCardTrigger>
            <HoverCardContent align="start" className="w-64 text-xs">
              <p className="mb-1 text-muted-foreground">These agents got this record in a prompt:</p>
              <ul className="flex flex-col gap-0.5">
                {[...seenBy].sort().map((a) => (
                  <li key={a}>{actorLabel(a)}</li>
                ))}
              </ul>
            </HoverCardContent>
          </HoverCard>
        )}
      </div>
    </div>
  );
}
