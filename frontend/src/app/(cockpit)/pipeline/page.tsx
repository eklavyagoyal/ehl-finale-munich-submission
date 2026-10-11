"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { StageStatusDot } from "@/components/stage-status";
import { Button } from "@/components/ui/button";
import { usePipeline } from "@/lib/api/hooks";
import type { PipelineStage } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { STAGE_HREF, STATUS_LABEL } from "@/lib/stages";
import { cn } from "cn";

const sum = (values: Record<string, number>) => Object.values(values).reduce((n, v) => n + v, 0);

// One or two numbers per stage, straight from /pipeline counts.
function metrics(stage: PipelineStage): { value: number; label: string }[] {
  switch (stage.key) {
    case "sources":
      return [
        { value: stage.counts.records, label: "records" },
        {
          value: stage.counts.sources,
          label: stage.counts.pending_review ? `sources · ${stage.counts.pending_review} pending review` : "sources",
        },
      ];
    case "processing":
      return [
        { value: sum(stage.counts.claims_by_status), label: "claims" },
        { value: stage.counts.records_without_claims, label: "feedback records without claims" },
      ];
    case "signals":
      return [
        { value: stage.counts.features_with_evidence, label: "signals" },
        { value: stage.counts.by_kind.pain ?? 0, label: "pain points" },
      ];
    case "experts": {
      const running = (stage.counts.runs_by_status.running ?? 0) + (stage.counts.runs_by_status.queued ?? 0);
      return [
        running
          ? { value: running, label: running === 1 ? "run in progress" : "runs in progress" }
          : { value: stage.counts.runs_by_status.completed ?? 0, label: "runs completed" },
        { value: stage.counts.requirements, label: "requirements" },
      ];
    }
    case "decision":
      return [
        { value: stage.counts.by_status.in_review ?? 0, label: "to decide" },
        { value: stage.counts.by_status.approved ?? 0, label: "approved" },
      ];
  }
}

export default function PipelinePage() {
  const { data, error, isLoading } = usePipeline();
  const next = data?.next_action;

  return (
    <>
      <PageHeader crumbs={[{ label: "Vehicles", href: "/" }, { label: data?.target_model.split(":").pop() ?? "G60" }]} />
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && (
        <div className="mt-8 flex max-w-6xl flex-col gap-10">
          {next && (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-[13px] text-muted-foreground">Next</span>
              <Button asChild>
                <Link href={STAGE_HREF[next.stage]}>
                  {next.label}
                  <ArrowRight />
                </Link>
              </Button>
            </div>
          )}

          <ol className="relative grid gap-3 lg:grid-cols-5 lg:gap-6">
            {/* The thin line that ties the stages together; it shows in the gaps between cards. */}
            <span aria-hidden className="absolute inset-x-4 top-[27px] hidden h-px bg-foreground/20 lg:block" />
            {data.stages.map((stage) => (
              <li key={stage.key} className="relative">
                <Link
                  href={STAGE_HREF[stage.key]}
                  className={cn(
                    "flex h-full flex-col gap-3 rounded-xl border bg-background p-4 transition-colors hover:border-foreground/25",
                    next?.stage === stage.key && "border-foreground/40",
                  )}
                >
                  <span className="flex items-center gap-2 text-[13px]">
                    <StageStatusDot status={stage.status} />
                    <span className="font-medium">{stage.title}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{STATUS_LABEL[stage.status]}</span>
                  </span>
                  <span className="text-[13px] text-muted-foreground">{stage.question}</span>
                  <span className="mt-auto flex flex-col gap-1.5 pt-2">
                    {metrics(stage).map((m, i) => (
                      <span key={m.label} className="flex items-baseline gap-1.5">
                        <span className={cn("tabular-nums", i === 0 ? "text-2xl font-semibold" : "text-sm")}>{fmtCount(m.value)}</span>
                        <span className="text-xs text-muted-foreground">{m.label}</span>
                      </span>
                    ))}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}
