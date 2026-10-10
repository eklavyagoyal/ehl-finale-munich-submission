"use client";

import { ScoreBar } from "@/components/score-bar";
import { EmptyState } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { actorLabel, fmtDateTime, fmtRange, fmtScore, gateTone, humanize, isHypothesis } from "@/lib/format";

import { useRequirementContext } from "./context";

export function OverviewTab() {
  const { detail } = useRequirementContext();
  if (!detail) return null;
  const { requirement: r, scores, recommendation, synthesis, gates, decisions } = detail;
  const criteria = Object.values(scores.criteria);
  const challenge = recommendation?.challenge;

  return (
    <div className="grid max-w-6xl gap-x-16 gap-y-10 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,1fr)]">
      <div className="flex min-w-0 flex-col gap-10">
        <div className="flex flex-col gap-4">
          <p className="max-w-2xl text-[17px] leading-relaxed text-foreground/80">{r.description}</p>
          {r.customer_problem && (
            <Field label="Customer problem">
              <p className="max-w-2xl">{r.customer_problem}</p>
            </Field>
          )}
          {r.acceptance_criteria.length > 0 && (
            <Field label="Acceptance criteria">
              <ul className="flex max-w-2xl flex-col gap-1">
                {r.acceptance_criteria.map((c, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-muted-foreground/60">{i + 1}</span>
                    {c}
                  </li>
                ))}
              </ul>
            </Field>
          )}
        </div>

        <Field label={r.priority_rank ? `Why it ranks #${r.priority_rank}` : "Why it ranks here"}>
          {r.prioritization_rationale && <p className="max-w-2xl">{r.prioritization_rationale}</p>}
          {criteria.length === 0 ? (
            <p className="text-muted-foreground">No ratings yet. Run Parallax to score this requirement.</p>
          ) : (
            <div className="flex max-w-2xl flex-col gap-2.5">
              {criteria.map((c) => {
                const hypothesis = isHypothesis(c.status);
                return (
                  <div key={c.criterion} className="grid grid-cols-[150px_minmax(0,1fr)_56px_92px] items-center gap-3 text-[13px]">
                    <span className="truncate">
                      {humanize(c.criterion)} <span className="text-muted-foreground/60">{Math.round(c.weight * 100)}%</span>
                    </span>
                    <ScoreBar low={c.low ?? c.score} high={c.high ?? c.score} max={5} hypothesis={hypothesis} className="w-full" />
                    <span className="text-right tabular-nums text-muted-foreground">
                      {c.low != null && c.high != null && c.low !== c.high ? fmtRange(c.low, c.high, 1) : fmtScore(c.score ?? c.low, 1)}
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="justify-self-start">
                          <ToneBadge tone={hypothesis ? "amber" : "muted"}>{hypothesis ? "hypothesis" : "evidence"}</ToneBadge>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        {humanize(c.status)} · {c.raters.map(actorLabel).join(", ") || "no rater"}
                      </TooltipContent>
                    </Tooltip>
                  </div>
                );
              })}
              {scores.formula && <p className="mt-1 text-xs text-muted-foreground">{scores.formula}</p>}
            </div>
          )}
        </Field>

        {(r.assumptions.length > 0 || r.uncertainties.length > 0) && (
          <Field label="Assumptions and uncertainties">
            <ul className="flex max-w-2xl flex-col gap-1.5">
              {r.assumptions.map((a, i) => (
                <li key={`a${i}`} className="flex items-baseline gap-2.5">
                  <ToneBadge tone="neutral">assumption</ToneBadge>
                  {a}
                </li>
              ))}
              {r.uncertainties.map((u, i) => (
                <li key={`u${i}`} className="flex items-baseline gap-2.5">
                  <ToneBadge tone="amber">uncertain</ToneBadge>
                  {u}
                </li>
              ))}
            </ul>
          </Field>
        )}

        {(r.kano_class || r.benchmark_target) && (
          <Field label="Structure · AI proposal">
            <div className="flex max-w-2xl flex-col gap-1.5">
              {r.kano_class && (
                <p>
                  <span className="font-medium">Kano: {humanize(r.kano_class)}</span>
                  {r.kano_rationale && <span className="text-muted-foreground"> · {r.kano_rationale}</span>}
                </p>
              )}
              {r.benchmark_target && <p>Benchmark target: {r.benchmark_target}</p>}
            </div>
          </Field>
        )}

        {synthesis?.content.clinic_questions?.length ? (
          <Field label="Questions for a customer clinic">
            <ul className="flex max-w-2xl list-inside list-disc flex-col gap-1">
              {synthesis.content.clinic_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </Field>
        ) : null}
      </div>

      <aside className="flex flex-col text-sm">
        <Section label="Score">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tracking-tight tabular-nums">{fmtScore(scores.score_midpoint ?? r.score)}</span>
            <span className="text-muted-foreground tabular-nums">range {fmtRange(scores.score_low, scores.score_high)}</span>
            {r.priority_rank && <span className="ml-auto text-muted-foreground tabular-nums">rank #{r.priority_rank}</span>}
          </div>
          <p className="mt-1 text-muted-foreground">
            Evidence {humanize(r.evidence_level).toLowerCase()}
            {r.evidence_level_explanation && ` · ${r.evidence_level_explanation}`}
          </p>
        </Section>

        <Section label="Recommendation · a proposal, you decide">
          {recommendation ? (
            <>
              <p className="font-medium">{humanize(recommendation.recommendation)}</p>
              <p className="mt-0.5 text-muted-foreground">
                {Object.entries(recommendation.tally.counts)
                  .map(([vote, n]) => `${n} ${humanize(vote).toLowerCase()}`)
                  .join(" · ")}
                {recommendation.tally.gate_cap && ` · capped: ${recommendation.tally.gate_cap}`}
              </p>
              {recommendation.minority_report.length > 0 && (
                <div className="mt-2 flex flex-col gap-1">
                  <p className="text-[13px] text-muted-foreground">Dissent</p>
                  {recommendation.minority_report.map((m, i) => (
                    <p key={i} className="text-[13px]">
                      <span className="font-medium">{actorLabel(m.judge ?? m.agent_id ?? "judge:?")}</span> · {humanize(m.vote ?? "")}
                      {m.rationale && <span className="text-muted-foreground"> · {m.rationale}</span>}
                    </p>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">No run yet.</p>
          )}
        </Section>

        {challenge?.counter_position && (
          <div className="my-5 rounded-lg border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900 dark:bg-amber-950/60">
            <p className="text-[13px] font-medium text-amber-900 dark:text-amber-100">Counter-argument</p>
            <p className="mt-1 text-amber-950 dark:text-amber-50">{challenge.counter_position}</p>
            {challenge.strongest_arguments?.length ? (
              <ul className="mt-2 list-inside list-disc text-amber-900/90 dark:text-amber-100/90">
                {challenge.strongest_arguments.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            ) : null}
            {challenge.evidence_that_would_change_the_call?.length ? (
              <p className="mt-2 text-[13px] text-amber-900/80 dark:text-amber-100/80">
                Would change the call: {challenge.evidence_that_would_change_the_call.join("; ")}
              </p>
            ) : null}
            {challenge.risk_if_outcome_is_wrong && (
              <p className="mt-1 text-[13px] text-amber-900/80 dark:text-amber-100/80">Risk if wrong: {challenge.risk_if_outcome_is_wrong}</p>
            )}
          </div>
        )}

        <Section label="Gates">
          <div className="flex flex-col gap-1.5">
            {Object.entries(gates).map(([gate, g]) => (
              <Tooltip key={gate}>
                <TooltipTrigger asChild>
                  <div className="flex items-center justify-between gap-3">
                    <span>{humanize(gate)}</span>
                    <ToneBadge tone={gateTone(g.value)}>{g.value}</ToneBadge>
                  </div>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  {g.reason} · {actorLabel(g.owner)}
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </Section>

        {synthesis?.content.headline && (
          <Section label="Synthesis">
            <p>{synthesis.content.headline}</p>
            {synthesis.content.conflicts?.map((c, i) => (
              <p key={i} className="mt-1 text-muted-foreground">
                {c.between}: {c.description}
              </p>
            ))}
          </Section>
        )}

        {decisions.length > 0 && (
          <Section label="Decisions">
            {decisions.map((d) => (
              <p key={d.id} className="mb-1.5">
                <span className="font-medium">{humanize(d.action)}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · {actorLabel(d.actor_id)} · {fmtDateTime(d.created_at)}
                </span>
                <br />
                <span className="text-muted-foreground">“{d.rationale}”</span>
              </p>
            ))}
          </Section>
        )}
      </aside>

      {criteria.length === 0 && !recommendation && (
        <div className="lg:col-span-2">
          <EmptyState title="Not simulated yet">Start a Parallax run to get persona reactions, department memos and a recommendation.</EmptyState>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 text-sm">
      <h2 className="text-[13px] font-normal text-muted-foreground">{label}</h2>
      {children}
    </section>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-border/60 py-5 first:pt-0">
      <h2 className="mb-1.5 text-[13px] font-normal text-muted-foreground">{label}</h2>
      {children}
    </section>
  );
}
