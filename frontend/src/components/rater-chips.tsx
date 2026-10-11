"use client";

import { ToneBadge } from "@/components/tone-badge";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { Rating } from "@/lib/api/types";
import { actorLabel, fmtRange, fmtScore, humanize, type Tone } from "@/lib/format";
import { RATER_KINDS, type RaterKind, raterKind } from "@/lib/provenance";

const KIND_TONE: Record<RaterKind, Tone> = {
  code: "green",
  research: "green",
  persona: "blue",
  department: "amber",
  pm: "neutral",
};

export function RaterLegend() {
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      {RATER_KINDS.map((k) => (
        <span key={k.kind} className="flex items-center gap-1">
          <ToneBadge tone={KIND_TONE[k.kind]}>{k.label}</ToneBadge>
          {k.meaning}
        </span>
      ))}
    </p>
  );
}

function value(r: Rating): string {
  return r.low != null && r.high != null && r.low !== r.high ? fmtRange(r.low, r.high, 1) : fmtScore(r.score ?? r.low, 1);
}

// One chip per kind of rater behind a criterion; the hover lists every rating with its rationale.
// `counted` are the rating ids the backend used for the score: observed data outranks simulations
// and assumptions, so a kind whose ratings were all left out is shown faded and labelled.
export function RaterChips({ ratings, counted }: { ratings: Rating[]; counted?: number[] }) {
  const used = counted ? new Set(counted) : null;
  const byKind = new Map<RaterKind, Rating[]>();
  for (const r of ratings) {
    const kind = raterKind(r.rater_type);
    byKind.set(kind, [...(byKind.get(kind) ?? []), r]);
  }
  if (byKind.size === 0) return <span className="text-xs text-muted-foreground">no rating</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {RATER_KINDS.filter((k) => byKind.has(k.kind)).map((k) => {
        const items = byKind.get(k.kind)!;
        const ignored = used !== null && items.every((r) => !used.has(r.id));
        return (
          <HoverCard key={k.kind} openDelay={100} closeDelay={60}>
            <HoverCardTrigger asChild>
              <button type="button" className={ignored ? "opacity-45" : undefined}>
                <ToneBadge tone={KIND_TONE[k.kind]}>
                  {k.label}
                  {items.length > 1 && <span className="ml-1 opacity-70">{items.length}</span>}
                </ToneBadge>
              </button>
            </HoverCardTrigger>
            <HoverCardContent align="end" className="w-80 text-xs">
              <p className="mb-2 text-muted-foreground">
                {k.label} · {k.meaning}
                {ignored && " · not counted in this score, stronger data was available"}
              </p>
              <div className="flex flex-col gap-2">
                {items.map((r) => (
                  <div key={r.id} className="flex flex-col gap-0.5">
                    <p>
                      <span className="font-medium">{actorLabel(r.rater_id)}</span>
                      <span className="text-muted-foreground">
                        {" "}
                        · {value(r)} / 5 · {humanize(r.status)}
                        {used !== null && !used.has(r.id) && " · not counted"}
                      </span>
                    </p>
                    {r.rationale && <p className="line-clamp-3 text-foreground/80">{r.rationale}</p>}
                  </div>
                ))}
              </div>
            </HoverCardContent>
          </HoverCard>
        );
      })}
    </span>
  );
}
