"use client";

import { Check, CircleDashed } from "lucide-react";

import { EmptyState } from "@/components/states";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { EvidenceLink } from "@/lib/api/types";
import { actorLabel, humanize } from "@/lib/format";

import { useRequirementContext } from "./context";

const RELATIONS = [
  { key: "supporting", title: "Supporting" },
  { key: "contradicting", title: "Contradicting" },
  { key: "context", title: "Context" },
];

export function EvidenceTab() {
  const { detail } = useRequirementContext();
  if (!detail) return null;
  const evidence = detail.evidence;

  if (evidence.length === 0) {
    return (
      <EmptyState title="No linked evidence">
        This requirement has no linked reviews or study records yet. Without evidence the traceability gate cannot pass.
      </EmptyState>
    );
  }

  const known = new Set(RELATIONS.map((r) => r.key));
  const groups = [
    ...RELATIONS.map((r) => ({ ...r, items: evidence.filter((e) => e.relation === r.key) })),
    { key: "other", title: "Other", items: evidence.filter((e) => !known.has(e.relation)) },
  ].filter((g) => g.items.length > 0);

  return (
    <div className="flex max-w-5xl flex-col gap-9">
      {groups.map((group) => (
        <section key={group.key}>
          <h2 className="flex items-baseline gap-2 border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">
            <span className={group.key === "contradicting" ? "text-red-700 dark:text-red-300" : undefined}>{group.title}</span>
            <span className="text-muted-foreground/60">{group.items.length}</span>
          </h2>
          {group.items.map((item) => (
            <EvidenceRow key={item.id} item={item} />
          ))}
        </section>
      ))}
    </div>
  );
}

function EvidenceRow({ item }: { item: EvidenceLink }) {
  const text = item.quote || item.record?.text || "";
  const locator = item.record?.locator as { kind?: string; rows?: number[]; sheet?: string } | undefined;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_220px] gap-6 border-b border-border/60 px-2 py-3 text-sm">
      <div className="flex min-w-0 gap-2.5">
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="mt-0.5 shrink-0 text-muted-foreground">
              {item.quote_verified ? <Check className="size-4 text-emerald-600" aria-label="Quote verified" /> : <CircleDashed className="size-4" aria-label="Quote not verified" />}
            </span>
          </TooltipTrigger>
          <TooltipContent>{item.quote_verified ? "Quote matches the original record" : "Quote not verified against the record"}</TooltipContent>
        </Tooltip>
        <div className="min-w-0">
          <p>“{text}”</p>
          {item.quote && item.record?.text && item.record.text !== item.quote && (
            <p className="mt-1 line-clamp-2 text-[13px] text-muted-foreground">{item.record.text}</p>
          )}
          {item.record?.translation_en && <p className="mt-1 text-[13px] text-muted-foreground">EN: {item.record.translation_en}</p>}
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-0.5 text-xs text-muted-foreground">
        <span className="truncate font-mono">{item.record_id}</span>
        <span className="truncate">
          {item.record?.source_id}
          {item.record?.markets?.length ? ` · ${item.record.markets.join(", ")}` : ""}
        </span>
        {locator?.kind && (
          <span className="truncate">
            {humanize(locator.kind)}
            {locator.sheet ? ` · ${locator.sheet}` : ""}
            {locator.rows?.length ? ` · row ${locator.rows.join(", ")}` : ""}
          </span>
        )}
        <span>linked by {actorLabel(item.added_by)}</span>
      </div>
    </div>
  );
}
