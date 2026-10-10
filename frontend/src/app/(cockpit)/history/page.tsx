"use client";

import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { useAgreement, useLearningDecisions } from "@/lib/api/hooks";
import { actorLabel, fmtDateTime, humanize, statusTone } from "@/lib/format";

const ACTION_STATUS: Record<string, string> = { approve: "approved", reject: "rejected", challenge: "challenged", defer: "deferred" };

export default function HistoryPage() {
  const decisions = useLearningDecisions();
  const agreement = useAgreement();

  return (
    <>
      <PageHeader crumbs={[{ label: "G60" }, { label: "History" }]} />

      <section className="mt-4 max-w-5xl">
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">
          PM decisions {decisions.data && <span className="ml-1 text-muted-foreground/60">{decisions.data.length}</span>}
        </h2>
        {decisions.error && <ErrorState error={decisions.error} />}
        {decisions.isLoading && <LoadingRows />}
        {decisions.data?.length === 0 && (
          <EmptyState title="No decisions yet">Every approval, rejection, challenge and postponement shows up here with its rationale.</EmptyState>
        )}
        <div className="overflow-x-auto">
          <div className="min-w-[760px]">
            {decisions.data?.map((d) => (
              <div key={d.id} className="grid grid-cols-[110px_130px_110px_minmax(0,1fr)_140px] items-center gap-3 border-b border-border/60 px-2 py-2.5 text-sm">
                <span className="font-mono text-xs text-muted-foreground">{fmtDateTime(d.created_at)}</span>
                <Link href={`/requirements/${d.requirement_id}`} className="font-mono text-xs text-muted-foreground hover:text-foreground">
                  {d.requirement_id}
                </Link>
                <span>
                  <ToneBadge tone={statusTone(ACTION_STATUS[d.action] ?? d.action)}>{humanize(d.action)}</ToneBadge>
                </span>
                <span className="truncate">
                  “{d.rationale}” <span className="text-muted-foreground">· {actorLabel(d.actor_id)}</span>
                </span>
                <span className="text-right text-xs text-muted-foreground">
                  AI {humanize(d.ai_recommendation ?? "none").toLowerCase()}
                  {d.agreed_with_ai === true && " · agreed"}
                  {d.agreed_with_ai === false && " · overruled"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-10 max-w-3xl">
        <h2 className="border-b px-2 pb-2.5 text-[13px] font-normal text-muted-foreground">Agreement of agents with the PM</h2>
        {agreement.data?.length === 0 && <EmptyState title="No agreement data yet">It fills once you have decided on simulated requirements.</EmptyState>}
        {agreement.data?.map((a) => (
          <div key={a.agent_id} className="grid grid-cols-[minmax(0,1fr)_120px_70px] items-center gap-3 border-b border-border/60 px-2 py-2 text-sm">
            <span className="truncate">{a.display_name || actorLabel(a.agent_id)}</span>
            <span className="relative h-1 rounded-full bg-muted" aria-hidden>
              <span className="absolute inset-y-0 left-0 rounded-full bg-foreground" style={{ width: `${(a.agreement_rate ?? 0) * 100}%` }} />
            </span>
            <span className="text-right text-xs text-muted-foreground tabular-nums">
              {a.agreement_rate == null ? "–" : `${Math.round(a.agreement_rate * 100)}%`} · {a.decisions}
            </span>
          </div>
        ))}
      </section>
    </>
  );
}
