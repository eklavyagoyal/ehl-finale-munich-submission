"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useTheme } from "@/lib/api/hooks";
import type { Requirement } from "@/lib/api/types";
import { actorLabel, fmtCount, humanize } from "@/lib/format";
import { channelLabel } from "@/lib/provenance";

// Where a requirement comes from, one step back per link: signal (Signals) -> claims (Processing) -> sources (Sources).
export function OriginTrail({ requirement }: { requirement: Requirement }) {
  const { data: theme, error } = useTheme(requirement.theme_id);

  if (requirement.theme_id == null) {
    return <p className="mt-1.5 text-xs text-muted-foreground">Created manually by {actorLabel(requirement.created_by)}, not drafted from a signal.</p>;
  }
  if (error) return <p className="mt-1.5 text-xs text-muted-foreground">Origin signal {requirement.theme_id} could not be loaded.</p>;
  if (!theme) return <p className="mt-1.5 h-4" aria-hidden />;

  const market = theme.market ?? "all";
  const claimTypes = Object.entries(theme.counts_by_claim_type ?? {}).filter(([, n]) => n > 0);
  const claims = claimTypes.reduce((n, [, v]) => n + v, 0);
  const datasets = new Map<string, { channel: string; reviews: number }>();
  for (const c of theme.cohorts ?? []) {
    const prev = datasets.get(c.dataset_key);
    datasets.set(c.dataset_key, { channel: c.channel, reviews: (prev?.reviews ?? 0) + c.mention_review_count });
  }

  return (
    <nav aria-label="Origin" className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
      <span>From signal</span>
      <Link href={`/signals?market=${encodeURIComponent(market)}#sig-${theme.feature_key}`} className="text-foreground hover:underline">
        {theme.label}
      </Link>
      <Link href={`/signals?market=${encodeURIComponent(market)}#sig-${theme.feature_key}`} className="tabular-nums hover:text-foreground hover:underline">
        {fmtCount(theme.mention_review_count)} reviews
      </Link>
      <ChevronRight className="size-3 text-muted-foreground/60" aria-hidden />
      <HoverCard openDelay={100} closeDelay={60}>
        <HoverCardTrigger asChild>
          <Link href="/processing" className="tabular-nums hover:text-foreground hover:underline">
            {fmtCount(claims)} claims
          </Link>
        </HoverCardTrigger>
        <HoverCardContent align="start" className="w-64 text-xs">
          <p className="mb-1.5 text-muted-foreground">Claims behind this signal, by type</p>
          {claimTypes.map(([type, n]) => (
            <p key={type} className="flex justify-between gap-3">
              <span>{humanize(type)}</span>
              <span className="tabular-nums">{fmtCount(n)}</span>
            </p>
          ))}
          {theme.derived_from_labels ? <p className="mt-1.5 text-muted-foreground">{fmtCount(theme.derived_from_labels)} reviews interpreted from BMW labels</p> : null}
        </HoverCardContent>
      </HoverCard>
      <ChevronRight className="size-3 text-muted-foreground/60" aria-hidden />
      <HoverCard openDelay={100} closeDelay={60}>
        <HoverCardTrigger asChild>
          <Link href="/sources?tab=list" className="tabular-nums hover:text-foreground hover:underline">
            {fmtCount(datasets.size)} source{datasets.size === 1 ? "" : "s"}
          </Link>
        </HoverCardTrigger>
        <HoverCardContent align="start" className="w-72 text-xs">
          <p className="mb-1.5 text-muted-foreground">Datasets the reviews come from</p>
          {[...datasets.entries()].map(([key, d]) => (
            <p key={key} className="flex justify-between gap-3">
              <span className="min-w-0 truncate">
                {channelLabel(d.channel)} <span className="font-mono text-muted-foreground">{key}</span>
              </span>
              <span className="tabular-nums">{fmtCount(d.reviews)}</span>
            </p>
          ))}
        </HoverCardContent>
      </HoverCard>
    </nav>
  );
}
