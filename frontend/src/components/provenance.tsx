"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { createElement } from "react";

import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { ClaimSummary, SourceSummary } from "@/lib/api/types";
import { fmtDateTime, humanize } from "@/lib/format";
import {
  channelIcon,
  channelLabel,
  interpretation,
  isSynthetic,
  llmPermission,
  locateQuote,
  producerText,
  streamLabel,
} from "@/lib/provenance";
import { cn } from "cn";

export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 shrink-0 items-center rounded-md border border-dashed border-fuchsia-300 bg-fuchsia-50 px-1.5 text-xs text-fuchsia-800 dark:border-fuchsia-800 dark:bg-fuchsia-950 dark:text-fuchsia-200",
        className,
      )}
      title="Invented test data, not a real finding"
    >
      synthetic
    </span>
  );
}

export function ChannelIcon({ channel, className }: { channel: string | null | undefined; className?: string }) {
  return createElement(channelIcon(channel), {
    className: cn("size-3.5 shrink-0 text-muted-foreground", className),
    strokeWidth: 1.5,
    "aria-label": channelLabel(channel),
  });
}

export function StreamBadge({ stream, channel }: { stream: string | null | undefined; channel: string | null | undefined }) {
  return (
    <span className="inline-flex h-5 shrink-0 items-center gap-1 rounded-md border px-1.5 text-xs text-foreground/80">
      <ChannelIcon channel={channel} className="size-3" />
      {streamLabel(stream)}
    </span>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0">{children}</dd>
    </>
  );
}

export function SourceFacts({ source }: { source: SourceSummary }) {
  return (
    <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-1">
      <Fact label="Channel">
        {streamLabel(source.stream)} · {channelLabel(source.channel)}
      </Fact>
      <Fact label="Collected by">{source.collector || "unknown"}</Fact>
      <Fact label="Collected">{source.collected_at ? fmtDateTime(source.collected_at) : "unknown"}</Fact>
      <Fact label="Origin">
        {humanize(source.origin ?? "unknown")}
        {source.verification && ` · ${humanize(source.verification)}`}
      </Fact>
      <Fact label="Sampling">
        {source.sampling_method ?? "unknown"}
        {source.sampling_complete === false && " · incomplete"}
      </Fact>
      {source.limitations.length > 0 && (
        <Fact label="Limitations">
          <ul className="flex flex-col gap-0.5">
            {source.limitations.map((l, i) => (
              <li key={i}>{String(l)}</li>
            ))}
          </ul>
        </Fact>
      )}
      <Fact label="Review">{source.review_status}</Fact>
      <Fact label="May go to OpenAI">{llmPermission(source.external_llm, source.review_status)}</Fact>
    </dl>
  );
}

// Hover on a source name: everything about where a record comes from, plus a link to the source page.
export function SourceHoverCard({ source, children }: { source: SourceSummary | null | undefined; children: React.ReactNode }) {
  if (!source) return <span className="text-muted-foreground">source unknown</span>;
  return (
    <HoverCard openDelay={120} closeDelay={80}>
      <HoverCardTrigger asChild>{children}</HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <div className="mb-2 flex items-start gap-2">
          <p className="font-medium">{source.title}</p>
          {isSynthetic(source) && <SyntheticBadge className="ml-auto" />}
        </div>
        <SourceFacts source={source} />
        <Link href={`/sources/${encodeURIComponent(source.source_id)}`} className="mt-2 inline-block text-foreground underline-offset-4 hover:underline">
          Open source
        </Link>
      </HoverCardContent>
    </HoverCard>
  );
}

// Who read meaning into a record: BMW's own label, a model, or a person.
export function InterpretationBadge({ claims }: { claims: ClaimSummary[] }) {
  const info = interpretation(claims);
  const badge = (
    <span className="inline-flex items-center gap-1">
      <ToneBadge tone={info.tone}>{info.label}</ToneBadge>
      {info.review && <ToneBadge tone={info.review === "accepted" ? "green" : info.review === "rejected" ? "red" : "amber"}>{info.review}</ToneBadge>}
    </span>
  );
  if (claims.length === 0) return badge;
  return (
    <HoverCard openDelay={120} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button type="button" className="text-left">
          {badge}
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 text-xs">
        <div className="flex flex-col gap-2.5">
          {claims.map((c) => (
            <div key={c.claim_id} className="flex flex-col gap-0.5">
              <p className="font-medium">
                {c.feature_label} · {humanize(c.claim_type)}
              </p>
              <p className="text-foreground/80">{c.summary}</p>
              <p className="text-muted-foreground">
                {producerText(c)} · {c.review_status}
              </p>
            </div>
          ))}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

// The record's full text with the cited quote marked. If the quote is not found in the text it is
// shown separately; the check mark comes only from the backend's quote_verified.
export function QuoteText({ text, quote, verified }: { text: string | null; quote: string | null; verified: boolean }) {
  const body = text ?? "";
  const range = quote ? locateQuote(body, quote) : null;
  const mark = verified ? (
    <Check className="ml-1 inline size-3.5 align-[-2px] text-emerald-600" aria-label="Quote verified against the record" />
  ) : null;
  if (range) {
    return (
      <p className="leading-relaxed">
        {body.slice(0, range[0])}
        <mark className="rounded-sm bg-amber-100 px-0.5 text-foreground dark:bg-amber-900/60">{body.slice(range[0], range[1])}</mark>
        {mark}
        {body.slice(range[1])}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      {quote && (
        <p className="leading-relaxed">
          “{quote}”{mark}
        </p>
      )}
      {body && body !== quote && <p className={cn("leading-relaxed", quote && "line-clamp-3 text-[13px] text-muted-foreground")}>{body}</p>}
    </div>
  );
}
