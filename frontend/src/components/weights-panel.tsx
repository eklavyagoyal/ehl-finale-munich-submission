"use client";

import { ErrorState, LoadingRows } from "@/components/states";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useWeights } from "@/lib/api/hooks";
import type { Weights } from "@/lib/api/types";
import { fmtCount, humanize } from "@/lib/format";

// A quiet "Weights" link that opens every weight Parallax uses in one panel.
export function WeightsLink() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <button type="button" className="self-start text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
          Weights
        </button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Weights</SheetTitle>
          <SheetDescription>Every weight Parallax uses, in one place.</SheetDescription>
        </SheetHeader>
        <WeightsBody />
      </SheetContent>
    </Sheet>
  );
}

function WeightsBody() {
  const { data, error, isLoading } = useWeights();
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingRows />;
  return (
    <div className="flex flex-col gap-6 px-4 pb-6 text-[13px]">
      <Section title="Evidence" rule={data.evidence.rule} note={data.evidence.used_for}>
        <Rows title="Source" rows={data.evidence.source.map((r) => [r.label, r.weight])} />
        <Rows title="Author (online only)" rows={data.evidence.author.map((r) => [r.label, r.weight])} />
        <Rows title="Text" rows={data.evidence.text.map((r) => [r.label, r.weight])} />
      </Section>
      <Section title="Owners" rule={data.owners.rule} note={data.owners.used_for}>
        <Rows
          title={data.owners.basis ?? "Markets"}
          rows={[...data.owners.markets]
            .sort((a, b) => ((["US", "EU", "CN"].indexOf(a.key) + 9) % 9) - ((["US", "EU", "CN"].indexOf(b.key) + 9) % 9))
            .map((m) => [`${m.key} · ${fmtCount(m.volume_2030)} planned 2030`, m.weight])}
        />
        <Rows title="Validation" rows={Object.entries(data.owners.validation).map(([k, v]) => [humanize(k), v])} />
      </Section>
      <Section title="Decision criteria" note={data.criteria_used_for}>
        <Rows rows={data.criteria.map((c) => [humanize(c.key), c.weight, c.meaning ?? undefined])} />
      </Section>
      <Section title="Company council" note={data.company_council} />
      <p className="text-xs text-muted-foreground">Policy version {String(data.policy_version)}</p>
    </div>
  );
}

function Section({ title, rule, note, children }: { title: string; rule?: string; note?: string; children?: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-medium">{title}</h3>
      {rule && <p className="text-xs text-muted-foreground">{rule}</p>}
      {children}
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
    </section>
  );
}

function Rows({ title, rows }: { title?: string; rows: [string, number, string?][] }) {
  return (
    <div className="flex flex-col">
      {title && <p className="pb-1 text-xs text-muted-foreground">{title}</p>}
      {rows.map(([label, weight, meaning]) => (
        <div key={label} className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1" title={meaning}>
          <span className="truncate">{label}</span>
          <span className="tabular-nums">{weight}</span>
        </div>
      ))}
    </div>
  );
}

// Short line for the evidence factors of one node, e.g. "Owner 1 · Not stated 0.8 · …".
export function evidenceFactors(weights: Weights | undefined, key: string): string | null {
  if (!weights) return null;
  if (key === "online") {
    const author = weights.evidence.author.map((a) => `${a.label} ${a.weight}`).join(" · ");
    const text = weights.evidence.text.map((t) => `${t.label.toLowerCase()} ${t.weight}`).join(" · ");
    return `Author: ${author}. Text: ${text}.`;
  }
  const source = weights.evidence.source.find((s) => s.key === key);
  return source ? `Source weight ${source.weight}.` : null;
}
