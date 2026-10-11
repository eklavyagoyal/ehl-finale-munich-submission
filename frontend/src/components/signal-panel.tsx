"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DraftSelectedDialog } from "@/components/generate-dialog";
import { KIND_DOT } from "@/components/signal-map";
import { ErrorState, LoadingRows } from "@/components/states";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useSignalDetail } from "@/lib/api/hooks";
import type { Finding, Signal, SignalDetail } from "@/lib/api/types";
import { fmtCount, humanize } from "@/lib/format";
import { cn } from "cn";

// One signal opened up: how it was pre-sorted (six steps), then its findings, then the draft action.
export function SignalPanel({ featureKey, market, onClose }: { featureKey: string | null; market: string | null; onClose: () => void }) {
  const { data, error, isLoading } = useSignalDetail(featureKey, market);
  return (
    <Sheet open={!!featureKey} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
        {error && <ErrorState error={error} />}
        {isLoading && <LoadingRows />}
        {data && <PanelBody data={data} market={market} onDrafted={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function PanelBody({ data, market, onDrafted }: { data: SignalDetail; market: string | null; onDrafted: () => void }) {
  const matching = data.findings.filter((f) => f.matches_signal !== false);
  const others = data.findings.filter((f) => f.matches_signal === false);
  const [showOthers, setShowOthers] = useState(false);
  const asSignal = { feature_key: data.feature_key, label: data.label, reviews: data.reviews } as Signal;

  return (
    <div className="flex flex-col gap-6 px-4 pb-6">
      <SheetHeader className="px-0">
        <SheetTitle className="flex items-center gap-2">
          <span className={cn("size-2.5 rounded-full", KIND_DOT[data.kind])} aria-hidden />
          {data.label}
        </SheetTitle>
        <SheetDescription className="tabular-nums">
          {humanize(data.quadrant)} · {fmtCount(data.reviews)} reviews · {Math.round(data.need_share * 100)} % problems or wishes · {market ?? "All markets"}
        </SheetDescription>
      </SheetHeader>

      <section className="flex flex-col">
        <h3 className="pb-2 text-xs text-muted-foreground">How it was sorted</h3>
        <ol className="relative">
          <span aria-hidden className="absolute top-3 bottom-3 left-[5px] w-px bg-border" />
          {data.how_sorted.map((step) => (
            <SortStep key={step.key} label={step.label} short={step.short} detail={step.detail} />
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-1">
        <h3 className="pb-1 text-xs text-muted-foreground">Findings</h3>
        {data.findings.length === 0 && <p className="text-[13px] text-muted-foreground">Not grouped into findings yet.</p>}
        {matching.map((f) => (
          <FindingRow key={f.id} finding={f} />
        ))}
        {others.length > 0 &&
          (showOthers ? (
            others.map((f) => <FindingRow key={f.id} finding={f} />)
          ) : (
            <button type="button" onClick={() => setShowOthers(true)} className="self-start py-1 text-xs text-muted-foreground hover:text-foreground">
              +{others.length} other finding{others.length === 1 ? "" : "s"}
            </button>
          ))}
      </section>

      <section className="flex flex-wrap items-center gap-3">
        {data.requirement_ids.length > 0 ? (
          data.requirement_ids.map((id) => (
            <Link key={id} href={`/requirements/${encodeURIComponent(id)}`} className="text-[13px] hover:underline">
              {id} →
            </Link>
          ))
        ) : (
          <DraftSelectedDialog market={market} selected={[asSignal]} onDone={onDrafted} />
        )}
      </section>
    </div>
  );
}

function SortStep({ label, short, detail }: { label: string; short: string; detail: string }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="relative pl-5">
      <span aria-hidden className="absolute top-[9px] left-[2px] size-[7px] rounded-full bg-muted-foreground/50 ring-2 ring-background" />
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-baseline gap-2 py-1.5 text-left">
        <span className="w-20 shrink-0 text-[13px] font-medium">{label}</span>
        <span className="min-w-0 flex-1 text-xs text-muted-foreground">{short}</span>
        <ChevronDown className={cn("size-3 shrink-0 self-center text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && <p className="pb-2 pl-[88px] text-xs text-foreground/80">{detail}</p>}
    </li>
  );
}

function FindingRow({ finding: f }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-border/60">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-2 py-1.5 text-left text-[13px]">
        <span className={cn("truncate", f.matches_signal === false && "text-muted-foreground")}>{f.title}</span>
        <span className="text-xs text-muted-foreground tabular-nums">{fmtCount(f.reviews)}</span>
        <span className="w-9 text-right text-xs text-muted-foreground/70 tabular-nums">{Math.round(f.share_of_theme * 100)} %</span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 pb-3 text-xs">
          {f.description && <p className="text-foreground/80">{f.description}</p>}
          {f.quotes.slice(0, 3).map((q) => (
            <div key={q.record_id} className="flex flex-col gap-0.5">
              <p className="line-clamp-3">“{q.text}”</p>
              <Link href={`/sources?tab=records&ids=${encodeURIComponent(q.record_id)}`} className="font-mono text-muted-foreground hover:underline">
                {q.record_id}
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
