"use client";

import { ChevronRight, CornerDownRight } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { usePipeline } from "@/lib/api/hooks";
import type { FunnelStep, ProcessingStage } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

export default function ProcessingPage() {
  const { data, error, isLoading } = usePipeline();
  const stage = data?.stages.find((s): s is ProcessingStage => s.key === "processing");

  return (
    <>
      <PageHeader crumbs={[{ label: "Processing" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">What did we extract from it?</p>
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {stage && <Funnel stage={stage} />}
    </>
  );
}

// The funnel in one glance: four steps left to right, the gap as a side branch, the labeler's quality as a badge.
// Every step shows number, label and a one-line hint; the long form opens on click.
function Funnel({ stage }: { stage: ProcessingStage }) {
  const [open, setOpen] = useState<string | null>(null);
  // Older payloads have no funnel; fall back to the two counts they carried.
  const steps: FunnelStep[] = stage.funnel?.length
    ? stage.funnel
    : [
        { key: "reviews", count: stage.counts?.feedback_records ?? 0, label: "Reviews", hint: "Customer feedback", detail: "" },
        { key: "tagged", count: stage.counts?.records_with_claims ?? 0, label: "With a topic", hint: "", detail: "" },
      ];
  const gap = stage.gap ?? (stage.counts ? { count: stage.counts.records_without_claims ?? 0, label: "No topic", hint: "", detail: "" } : null);
  const quality = stage.labeler_quality;
  const detail =
    open === "gap"
      ? gap?.detail
      : open === "quality" && quality
        ? `Blind test of the AI labeler against BMW's own labels${quality.sample ? ` on ${fmtCount(quality.sample)} reviews` : ""}: same area in ${Math.round(quality.area_agreement * 100)} % of cases${quality.exact_recall != null ? `, exact feature in ${Math.round(quality.exact_recall * 100)} %` : ""}.`
        : steps.find((s) => s.key === open)?.detail;
  const toggle = (key: string) => setOpen((o) => (o === key ? null : key));

  return (
    <div className="mt-10 flex max-w-5xl flex-col gap-6">
      <ol className="flex flex-wrap items-stretch gap-y-4">
        {steps.map((step, i) => (
          <li key={step.key} className="flex items-stretch">
            {i > 0 && <ChevronRight className="mx-2 size-4 self-center text-muted-foreground/50" aria-hidden />}
            <button
              type="button"
              onClick={() => toggle(step.key)}
              aria-expanded={open === step.key}
              className={cn(
                "flex w-44 flex-col gap-1 rounded-xl border p-4 text-left transition-colors hover:border-foreground/25",
                open === step.key && "border-foreground/40",
              )}
            >
              <span className="text-2xl font-semibold tabular-nums">{fmtCount(step.count)}</span>
              <span className="text-[13px] font-medium">{step.label}</span>
              {step.hint && <span className="line-clamp-2 text-xs text-muted-foreground">{step.hint}</span>}
            </button>
          </li>
        ))}
      </ol>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        {gap && gap.count > 0 && (
          <button
            type="button"
            onClick={() => toggle("gap")}
            aria-expanded={open === "gap"}
            className="flex items-center gap-1.5 pl-6 text-[13px] text-amber-800 hover:underline dark:text-amber-200"
          >
            <CornerDownRight className="size-3.5" aria-hidden />
            <span className="tabular-nums">{fmtCount(gap.count)}</span> without a topic
          </button>
        )}
        {quality && (
          <button
            type="button"
            onClick={() => toggle("quality")}
            aria-expanded={open === "quality"}
            className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground"
          >
            {Math.round(quality.area_agreement * 100)} % same area as BMW
          </button>
        )}
      </div>

      {open && detail && <p className="max-w-2xl text-[13px] text-foreground/80">{detail}</p>}
    </div>
  );
}
