"use client";

import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { usePipeline } from "@/lib/api/hooks";
import type { ProcessingStage } from "@/lib/api/types";
import { fmtCount, humanize } from "@/lib/format";
import { cn } from "cn";

// Producer keys as /pipeline reports them; "unknown" stays unknown, it is never folded into AI.
const PRODUCER: Record<string, { label: string; color: string }> = {
  "BMW labels": { label: "BMW labels", color: "bg-emerald-600" },
  llm: { label: "AI-extracted", color: "bg-sky-600" },
  human: { label: "Human", color: "bg-foreground/70" },
  provided_unknown: { label: "Provided, method unknown", color: "bg-muted-foreground/45" },
  unknown: { label: "Unknown", color: "bg-muted-foreground/25" },
};

const STATUS: Record<string, { label: string; color: string }> = {
  accepted: { label: "Accepted", color: "bg-emerald-600" },
  pending: { label: "Pending", color: "bg-amber-500" },
  rejected: { label: "Rejected", color: "bg-red-500" },
};

type Part = { key: string; label: string; color: string; value: number };

function parts(values: Record<string, number>, styles: Record<string, { label: string; color: string }>): Part[] {
  return Object.entries(values)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({ key, value, label: styles[key]?.label ?? humanize(key), color: styles[key]?.color ?? "bg-muted-foreground/30" }))
    .sort((a, b) => b.value - a.value);
}

export default function ProcessingPage() {
  const { data, error, isLoading } = usePipeline();
  const stage = data?.stages.find((s): s is ProcessingStage => s.key === "processing");

  return (
    <>
      <PageHeader crumbs={[{ label: "Processing" }]} />
      <p className="mt-1 text-[13px] text-muted-foreground">What did we extract from it?</p>
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {stage && <Funnel counts={stage.counts} />}
    </>
  );
}

function Funnel({ counts }: { counts: ProcessingStage["counts"] }) {
  const feedback = counts.feedback_records;
  const share = (n: number) => (feedback ? Math.max(0, Math.min(1, n / feedback)) : 0);
  const byProducer = parts(counts.claims_by_producer ?? {}, PRODUCER);
  const byStatus = parts(counts.claims_by_status ?? {}, STATUS);
  const claims = byStatus.reduce((n, p) => n + p.value, 0);

  return (
    <div className="mt-10 flex max-w-3xl flex-col gap-10">
      <Step label="Feedback records" value={feedback} href="/sources?tab=records" hint="Counts only records of kind feedback, as the backend measures this stage.">
        <Bar parts={[{ key: "all", label: "Feedback records", color: "bg-foreground/80", value: feedback }]} total={feedback} />
      </Step>

      <Step label="Records with claims" value={counts.records_with_claims}>
        <div className="flex h-2 overflow-hidden rounded-full bg-muted">
          <span className="bg-foreground/80" style={{ width: `${share(counts.records_with_claims) * 100}%` }} />
          <span className="bg-amber-400/70" style={{ width: `${share(counts.records_without_claims) * 100}%` }} />
        </div>
        {counts.records_without_claims > 0 && (
          <p className="text-[13px] text-amber-800 dark:text-amber-200">
            Gap: {fmtCount(counts.records_without_claims)} feedback records without any claim. Nothing was extracted from them yet.
          </p>
        )}
      </Step>

      <Step label="Claims" value={claims} hint="One record can carry several claims, so this count is not a share of the records above.">
        <div className="flex flex-col gap-4">
          <Split title="Who extracted them" parts={byProducer} total={claims} />
          <Split title="Review state" parts={byStatus} total={claims} />
        </div>
      </Step>
    </div>
  );
}

function Step({ label, value, href, hint, children }: { label: string; value: number; href?: string; hint?: string; children: React.ReactNode }) {
  const number = <span className="text-2xl font-semibold tabular-nums">{fmtCount(value)}</span>;
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex items-baseline gap-2">
        {href ? (
          <Link href={href} className="hover:underline">
            {number}
          </Link>
        ) : (
          number
        )}
        <span className="text-[13px] text-muted-foreground">{label}</span>
      </div>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </section>
  );
}

function Bar({ parts, total }: { parts: Part[]; total: number }) {
  return (
    <div className="flex h-2 overflow-hidden rounded-full bg-muted">
      {parts.map((p) => (
        <span key={p.key} title={`${p.label}: ${fmtCount(p.value)}`} className={p.color} style={{ width: `${total ? (p.value / total) * 100 : 0}%` }} />
      ))}
    </div>
  );
}

function Split({ title, parts, total }: { title: string; parts: Part[]; total: number }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs text-muted-foreground">{title}</p>
      <Bar parts={parts} total={total} />
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {parts.map((p) => (
          <span key={p.key} className="flex items-center gap-1.5">
            <span className={cn("size-2 rounded-sm", p.color)} aria-hidden />
            {p.label}
            <span className="text-muted-foreground tabular-nums">{fmtCount(p.value)}</span>
          </span>
        ))}
        {parts.length === 0 && <span className="text-muted-foreground">No claims yet.</span>}
      </p>
    </div>
  );
}
