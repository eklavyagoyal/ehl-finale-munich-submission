"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { SourceFacts, StreamBadge, SyntheticBadge } from "@/components/provenance";
import { REVIEW_TONE, SourceReview } from "@/components/source-review";
import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { useSource } from "@/lib/api/hooks";
import { fmtDateTime, humanize } from "@/lib/format";
import { isSynthetic } from "@/lib/provenance";

export default function SourceDetailPage() {
  const id = decodeURIComponent(useParams<{ id: string }>().id);
  const { data, error, isLoading } = useSource(id);
  const s = data?.source;

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "Sources", href: "/sources?tab=list" }, { label: s?.title ?? id }]} />
      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && s && (
        <>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-[22px] font-semibold tracking-tight">{s.title}</h1>
            <StreamBadge stream={s.stream} channel={s.channel} />
            {isSynthetic(data.summary) && <SyntheticBadge />}
            <ToneBadge tone={REVIEW_TONE[s.review_status] ?? "muted"}>{s.review_status}</ToneBadge>
            <span className="ml-auto">
              <SourceReview sourceId={s.source_id} title={s.title} status={s.review_status} />
            </span>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{s.source_id}</p>

          <div className="mt-8 grid max-w-5xl gap-x-16 gap-y-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,1fr)]">
            <section className="flex flex-col gap-4 text-sm">
              <h2 className="text-[13px] font-normal text-muted-foreground">Provenance</h2>
              <div className="text-[13px]">
                <SourceFacts source={data.summary} />
              </div>
              <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-1 text-[13px]">
                <dt className="text-muted-foreground">Dataset</dt>
                <dd className="font-mono text-xs">{s.dataset_key}</dd>
                {s.locator && (
                  <>
                    <dt className="text-muted-foreground">Location</dt>
                    <dd className="font-mono text-xs break-all">{s.locator}</dd>
                  </>
                )}
                {s.sampling?.query && (
                  <>
                    <dt className="text-muted-foreground">Query</dt>
                    <dd>{s.sampling.query}</dd>
                  </>
                )}
                {(s.sampling?.date_start || s.sampling?.date_end) && (
                  <>
                    <dt className="text-muted-foreground">Period</dt>
                    <dd>
                      {s.sampling?.date_start ?? "?"} – {s.sampling?.date_end ?? "?"}
                    </dd>
                  </>
                )}
                {s.sampling?.retrieved_count != null && (
                  <>
                    <dt className="text-muted-foreground">Retrieved</dt>
                    <dd>{s.sampling.retrieved_count} items</dd>
                  </>
                )}
                {s.provenance?.notes && (
                  <>
                    <dt className="text-muted-foreground">Notes</dt>
                    <dd>{s.provenance.notes}</dd>
                  </>
                )}
                {s.export_permissions?.notes && (
                  <>
                    <dt className="text-muted-foreground">Permissions</dt>
                    <dd>{s.export_permissions.notes}</dd>
                  </>
                )}
                {s.updated_at && (
                  <>
                    <dt className="text-muted-foreground">Updated</dt>
                    <dd>{fmtDateTime(s.updated_at)}</dd>
                  </>
                )}
              </dl>
            </section>

            <aside className="flex flex-col text-sm">
              <section className="border-b border-border/60 pb-5">
                <h2 className="mb-1 text-[13px] font-normal text-muted-foreground">Records</h2>
                <Link href={`/sources?tab=records&channel=${encodeURIComponent(s.channel)}`} className="text-2xl font-semibold tabular-nums hover:underline">
                  {data.records}
                </Link>
                <p className="text-xs text-muted-foreground">Opens all records of this channel.</p>
              </section>
              <section className="border-b border-border/60 py-5">
                <h2 className="mb-1.5 text-[13px] font-normal text-muted-foreground">Interpretations (claims)</h2>
                {data.claims.length === 0 && <p className="text-muted-foreground">None extracted from this source.</p>}
                {data.claims.map((c, i) => (
                  <p key={i} className="flex items-center justify-between gap-3">
                    <span>
                      {c.derived_from_bmw_labels ? "BMW label" : "Other"} · {c.review_status}
                    </span>
                    <span className="tabular-nums">{c.count}</span>
                  </p>
                ))}
              </section>
              <section className="py-5">
                <h2 className="mb-1.5 text-[13px] font-normal text-muted-foreground">Who interpreted it</h2>
                {data.claim_producers.length === 0 && <p className="text-muted-foreground">No producer recorded.</p>}
                {data.claim_producers.map((p, i) => (
                  <p key={i} className="flex items-center justify-between gap-3">
                    <span>
                      {p.method === "llm" ? "AI" : p.method === "human" ? "Human" : humanize(p.method ?? "unknown")}
                      {p.name && <span className="text-muted-foreground"> · {p.name}</span>}
                    </span>
                    <span className="tabular-nums">{p.count}</span>
                  </p>
                ))}
              </section>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
