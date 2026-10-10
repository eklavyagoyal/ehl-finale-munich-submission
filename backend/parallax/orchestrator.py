"""Parallax run orchestration.

One simulation run handles up to N requirement cases at once:

  A  market twin (all personas, all cases)  ||  company twin (every department x case)   parallel
  B  research loop: info requests -> web research -> verifier (expensive model)          per case
  C  scoring: decision-model MCDA over observed / estimated / simulated / assumed ratings
  D  synthesis: one crystallized brief per case
  E  vote: heterogeneous judge panel -> recommendation (never a decision)

Each stage writes its outputs and a SimStep row, so the frontend can follow progress and the audit
trail can reconstruct who/what produced every number. The PM decides afterwards via the API.
"""

import threading
import traceback
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from statistics import pstdev

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from parallax import requirements as reqs
from parallax import scoring
from parallax.agents import company_twin, research, synthesis, vote
from parallax.agents.grounding import persona_grounding, requirement_evidence_quotes
from parallax.agents.market_twin import FIT_ANCHORS, DirectEngine, PersonaResult, TinyTroupeEngine
from parallax.agents.roster import active_agents
from parallax.agents.validation import validate_persona
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import session_scope
from parallax.learning import relevant_lessons
from parallax.llm import ssr
from parallax.llm.client import get_llm
from parallax.models import (
    Agent,
    CriterionRating,
    DepartmentMemo,
    PersonaResponse,
    Recommendation,
    Requirement,
    RequirementEvidence,
    ResearchRequest,
    SimRun,
    SimStep,
    Synthesis,
    Vote,
)
from parallax.policy import active_policy

def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ run lifecycle


def create_run(session: Session, *, requirement_ids: list[str], actor_id: str, kind: str = "simulation",
               challenge: str | None = None, parent_run_id: uuid.UUID | None = None, options: dict | None = None) -> SimRun:
    settings = get_settings()
    missing = [rid for rid in requirement_ids if session.get(Requirement, rid) is None]
    if missing:
        raise ValueError(f"unknown requirements: {missing}")
    if kind != "validation" and not requirement_ids:
        raise ValueError("a simulation needs at least one requirement")
    policy = active_policy(session)
    agents = session.scalars(select(Agent).where(Agent.active.is_(True))).all()
    options = options or {}
    run = SimRun(
        kind=kind, status="queued", requirement_ids=requirement_ids, requested_by=actor_id, challenge_question=challenge,
        parent_run_id=parent_run_id,
        config={
            "llm_mode": settings.llm_mode, "model_fast": settings.model_fast, "model_strong": settings.model_strong,
            "judge_models": settings.judge_models, "embedding_model": settings.embedding_model,
            "persona_engine": options.get("persona_engine") or settings.persona_engine,
            "policy_version_id": policy.id, "agent_versions": {a.id: a.version for a in agents},
            "max_parallel_cases": settings.max_parallel_cases, "options": options,
        },
        progress={"stage": "queued", "completed_stages": [], "errors": []},
    )
    session.add(run)
    session.flush()
    record_event(session, category="ai", actor_id=actor_id, action=f"{kind}.start", entity_type="sim_run",
                 entity_id=str(run.id), run_id=run.id, after={"requirement_ids": requirement_ids, "challenge": challenge},
                 rationale=challenge)
    return run


def launch(run_id: uuid.UUID) -> threading.Thread:
    target = execute_validation if _run_kind(run_id) == "validation" else execute
    thread = threading.Thread(target=target, args=(run_id,), name=f"parallax-run-{str(run_id)[:8]}", daemon=True)
    thread.start()
    return thread


def _run_kind(run_id: uuid.UUID) -> str:
    with session_scope() as session:
        return session.get(SimRun, run_id).kind


def _progress(run_id: uuid.UUID, **changes) -> None:
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        progress = dict(run.progress or {})
        if "stage_done" in changes:
            progress["completed_stages"] = [*progress.get("completed_stages", []), changes.pop("stage_done")]
        if "error" in changes:
            progress["errors"] = [*progress.get("errors", []), changes.pop("error")]
        progress.update(changes)
        run.progress = progress


@contextmanager
def _step(run_id: uuid.UUID, stage: str, requirement_id: str | None = None, agent_id: str | None = None):
    with session_scope() as session:
        step = SimStep(run_id=run_id, stage=stage, requirement_id=requirement_id, agent_id=agent_id, status="running")
        session.add(step)
        session.flush()
        step_id = step.id
    detail: dict = {}
    try:
        yield detail
    except Exception as error:
        with session_scope() as session:
            session.execute(update(SimStep).where(SimStep.id == step_id).values(
                status="failed", error=repr(error)[:2000], finished_at=_now(), detail=detail))
        _progress(run_id, error={"stage": stage, "requirement_id": requirement_id, "agent_id": agent_id,
                                 "error": repr(error)[:500]})
        raise
    with session_scope() as session:
        session.execute(update(SimStep).where(SimStep.id == step_id).values(status="completed", finished_at=_now(), detail=detail))


def _finish(run_id: uuid.UUID, status: str, error: str | None = None) -> None:
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status = status
        run.error = error
        run.finished_at = _now()
        run.progress = {**(run.progress or {}), "stage": "done" if status != "failed" else "failed"}
        record_event(session, category="ai", actor_id="system:orchestrator", action=f"{run.kind}.{status}",
                     entity_type="sim_run", entity_id=str(run.id), run_id=run.id,
                     after={"status": status, "llm_calls": run.llm_calls, "input_tokens": run.input_tokens,
                            "output_tokens": run.output_tokens}, rationale=error)


# ------------------------------------------------------------------ evidence package per case


def _evidence_package(session: Session, requirement: Requirement) -> tuple[dict, list[str]]:
    themes = reqs.themes_for(session, requirement)
    record_ids: list[str] = []
    theme_rows = []
    for theme in sorted(themes, key=lambda t: (t.market is not None, t.market or "")):
        theme_rows.append({
            "market": theme.market or "all", "distinct_reviews": theme.mention_review_count,
            "direct_target_model_reviews": theme.direct_review_count, "claim_types": theme.counts_by_claim_type,
            "channels": theme.channels, "max_within_cohort_share": round(theme.max_cohort_share, 4),
            "observed_demand_0_5": theme.demand_score, "observed_impact_0_5": theme.impact_score,
            "pending_claim_reviews_not_counted": theme.pending_claim_review_count,
        })
        if (theme.market == requirement.market) or (requirement.market is None and theme.market is None):
            record_ids = theme.record_ids
    cited = [l.record_id for l in session.scalars(select(RequirementEvidence).where(
        RequirementEvidence.requirement_id == requirement.id, RequirementEvidence.relation != "context"))]
    quotes, gate_meta = requirement_evidence_quotes(session, None, cited + record_ids, limit=10)
    package = {"themes_by_market": theme_rows, "owner_quotes": quotes, "quote_gate": gate_meta,
               "units": "distinct collected reviews; shares are within-cohort, not prevalence"}
    return package, [q["record_id"] for q in quotes]


def _requirement_payload(requirement: Requirement) -> dict:
    return {"id": requirement.id, "title": requirement.title, "description": requirement.description,
            "customer_problem": requirement.customer_problem, "market": requirement.market or "all focus markets",
            "target_model": requirement.target_model, "acceptance_criteria": requirement.acceptance_criteria,
            "assumptions": requirement.assumptions, "uncertainties": requirement.uncertainties,
            "evidence_level": requirement.evidence_level, "status": requirement.status}


# ------------------------------------------------------------------ stage A: market twin


def _persona_weights(policy: dict, personas: list[Agent]) -> dict[str, float]:
    weighting = policy["parallax"]["persona_weighting"]
    market_weights = weighting["market_weights"]
    multipliers = weighting["validation_multipliers"]
    per_market = defaultdict(list)
    for persona in personas:
        per_market[persona.market].append(persona)
    total_market = sum(market_weights.get(m, 0) for m in per_market) or 1
    weights = {}
    for market, members in per_market.items():
        share = market_weights.get(market, 0) / total_market
        for persona in members:
            weights[persona.id] = share / len(members) * multipliers.get(persona.validation_status, 0.5)
    return weights


def run_market_twin(run_id: uuid.UUID, requirement_ids: list[str], challenge: str | None, engine_name: str) -> dict:
    settings = get_settings()
    llm = get_llm()
    with session_scope() as session:
        policy = active_policy(session).document
        personas = active_agents(session, "market_persona")
        requirements = [session.get(Requirement, rid) for rid in requirement_ids]
        groundings = {p.id: persona_grounding(session, p, policy, settings.grounding_quotes_per_persona) for p in personas}
        weights = _persona_weights(policy, personas)
    if not personas:
        return {"personas": 0}
    with _step(run_id, "market_twin", agent_id="engine:" + engine_name) as detail:
        engine = TinyTroupeEngine() if engine_name == "tinytroupe" else DirectEngine()
        if isinstance(engine, TinyTroupeEngine):
            results = engine.evaluate_many(llm, [(p, groundings[p.id]) for p in personas], requirements, run_id, challenge)
        else:
            results: list[PersonaResult] = []
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = [pool.submit(engine.evaluate, llm, p, groundings[p.id], requirements, run_id, challenge)
                           for p in personas]
                for future in as_completed(futures):
                    results.append(future.result())
        anchor_sets = policy["parallax"]["ssr_anchor_sets"]
        rows = []
        for result in results:
            importance = ssr.rate(llm, [r.reaction for r in result.reactions], anchor_sets, run_id=run_id, agent_id=result.agent.id)
            fit = ssr.rate(llm, [r.class_fit for r in result.reactions], FIT_ANCHORS, run_id=run_id, agent_id=result.agent.id)
            for reaction, imp, fit_score in zip(result.reactions, importance, fit):
                rows.append(PersonaResponse(
                    run_id=run_id, agent_id=result.agent.id, agent_version=result.agent.version,
                    requirement_id=reaction.requirement_id, engine=result.engine,
                    response_text=reaction.reaction + ("\n[raw] " + result.raw_text[:3000] if result.raw_text else ""),
                    stance=reaction.stance, ssr_distribution=imp["distribution"], ssr_mean=imp["mean"],
                    importance_0_5=imp["importance_0_5"], market_fit_0_5=fit_score["importance_0_5"],
                    concerns=reaction.concerns, info_requests=[i.model_dump() for i in reaction.would_need_to_know],
                    grounding_record_ids=result.grounding.record_ids,
                ))
        with session_scope() as session:
            session.add_all(rows)
            session.flush()
            _simulated_ratings(session, run_id, requirement_ids, rows, weights, {p.id: p for p in personas})
        from parallax.agents.market_twin import stimulus

        detail.update({"personas": len(results), "responses": len(rows), "engine": engine_name,
                       "question": stimulus(requirements, challenge),
                       "grounding": {pid: g.gate for pid, g in groundings.items()}})
    return {"personas": len(results), "responses": len(rows)}


def _weighted(values: list[tuple[float, float]]) -> tuple[float, float] | None:
    total = sum(w for _, w in values)
    if total <= 0:
        return None
    mean = sum(v * w for v, w in values) / total
    spread = pstdev([v for v, _ in values]) if len(values) > 1 else 0.5
    return mean, spread


def _simulated_ratings(session: Session, run_id, requirement_ids, rows: list[PersonaResponse], weights: dict,
                       personas: dict[str, Agent]) -> None:
    by_req = defaultdict(list)
    for row in rows:
        by_req[row.requirement_id].append(row)
    for rid in requirement_ids:
        requirement = session.get(Requirement, rid)
        relevant = [r for r in by_req.get(rid, []) if requirement.market is None or personas[r.agent_id].market == requirement.market]
        if not relevant:
            continue
        scope = requirement.market or "ALL"
        for criterion, attr in (("impact", "importance_0_5"), ("vehicle_market_fit", "market_fit_0_5")):
            agg = _weighted([(getattr(r, attr), weights.get(r.agent_id, 0)) for r in relevant if getattr(r, attr) is not None])
            if agg is None:
                continue
            mean, spread = agg
            session.add(CriterionRating(
                requirement_id=rid, run_id=run_id, criterion=criterion, score=round(mean, 3),
                low=round(max(0.0, mean - spread), 3), high=round(min(5.0, mean + spread), 3), status="simulated",
                rater_type="persona", rater_id=f"market_twin:{scope}",
                rationale=(f"Weighted SSR {attr} of {len(relevant)} simulated owners ({scope}); weights = market exposure "
                           f"x validation multiplier (policy). Simulation, not evidence."),
                evidence_ids=[],
            ))


# ------------------------------------------------------------------ stage A: company twin


def run_department(run_id: uuid.UUID, agent_id: str, requirement_id: str, challenge: str | None) -> dict:
    llm = get_llm()
    with session_scope() as session:
        agent = session.get(Agent, agent_id)
        requirement = session.get(Requirement, requirement_id)
        evidence, evidence_ids = _evidence_package(session, requirement)
    with _step(run_id, "company_twin", requirement_id, agent_id) as detail:
        memo = company_twin.review(llm, agent, requirement, evidence, evidence_ids, run_id, challenge)
        with session_scope() as session:
            session.add(DepartmentMemo(run_id=run_id, agent_id=agent_id, agent_version=agent.version,
                                       requirement_id=requirement_id, stance=memo.stance, memo=memo.model_dump()))
            for rating in memo.criterion_ratings:
                session.add(CriterionRating(
                    requirement_id=requirement_id, run_id=run_id, criterion=rating.criterion, score=None,
                    low=rating.low, high=rating.high, status="assumed", rater_type="department", rater_id=agent_id,
                    rationale=rating.rationale, evidence_ids=[],
                ))
        detail.update({"stance": memo.stance, "effort_band": memo.effort_band, "info_requests": len(memo.info_requests)})
    return {"agent_id": agent_id, "info_requests": [(agent_id, i.question, i.why) for i in memo.info_requests]}


# ------------------------------------------------------------------ stage B: research loop


def run_research_for_case(run_id: uuid.UUID, requirement_id: str, requests: list[tuple[str, str, str]]) -> int:
    settings = get_settings()
    llm = get_llm()
    seen, chosen = set(), []
    # Department requests first (they are tied to decision criteria), then persona requests.
    for agent_id, question, why in sorted(requests, key=lambda r: not r[0].startswith("dept:")):
        key = question.strip().lower()
        if key and key not in seen:
            seen.add(key)
            chosen.append((agent_id, question, why))
    chosen = chosen[: settings.max_research_requests_per_case]
    with session_scope() as session:
        requirement = session.get(Requirement, requirement_id)
    done = 0
    for agent_id, question, why in chosen:
        with session_scope() as session:
            row = ResearchRequest(run_id=run_id, requirement_id=requirement_id, requested_by=agent_id, question=question,
                                  rationale=why, status="open")
            session.add(row)
            session.flush()
            request_id = row.id
            record_event(session, category="ai", actor_id=agent_id, action="research.request", entity_type="research_request",
                         entity_id=str(request_id), requirement_id=requirement_id, run_id=run_id, after={"question": question})
        with _step(run_id, "research", requirement_id, "agent:research") as detail:
            found = research.research(llm, requirement, question, why, agent_id, run_id)
            citations = llm.last_citations()
            detail.update({"findings": len(found.findings), "citations": len(citations)})
        with _step(run_id, "verification", requirement_id, "agent:verifier") as detail:
            checked = research.verify(llm, requirement, question, found, run_id)
            detail.update({"overall": checked.overall})
        with session_scope() as session:
            row = session.get(ResearchRequest, request_id)
            row.findings = [f.model_dump() for f in found.findings]
            row.sources = citations or [{"url": f.source_url, "title": f.source_title} for f in found.findings]
            row.verification = checked.model_dump()
            row.verdict = checked.overall
            row.status = "verified" if checked.overall in ("verified", "partially_verified") else "rejected"
            row.findings.append({"answer_summary": found.answer_summary, "limitations": found.limitations})
            gap = found.competitive_gap
            if gap.applicable and checked.overall in ("verified", "partially_verified"):
                low, high = min(gap.low, gap.high), max(gap.low, gap.high)
                session.add(CriterionRating(
                    requirement_id=requirement_id, run_id=run_id, criterion="competitive_gap", score=round((low + high) / 2, 3),
                    low=low, high=high, status="estimated", rater_type="research", rater_id="agent:research",
                    rationale=f"{gap.rationale} (verifier: {checked.overall})", evidence_ids=[],
                ))
            record_event(session, category="ai", actor_id="agent:verifier", action="research.verify",
                         entity_type="research_request", entity_id=str(request_id), requirement_id=requirement_id,
                         run_id=run_id, after={"verdict": checked.overall, "status": row.status})
        done += 1
    return done


# ------------------------------------------------------------------ stages C-E per case


def score_case(session: Session, run_id: uuid.UUID, requirement: Requirement, policy: dict) -> dict:
    reqs.add_observed_ratings(session, requirement, run_id=run_id)
    session.flush()
    ratings = session.scalars(select(CriterionRating).where(
        CriterionRating.requirement_id == requirement.id,
        (CriterionRating.run_id == run_id) | (CriterionRating.rater_type == "pm"),
    )).all()
    result = scoring.compute(policy, list(ratings))
    reqs.refresh_code_gates(session, requirement, run_id=run_id)
    return result


def _market_twin_summary(session: Session, run_id, requirement_id: str) -> dict:
    rows = session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == run_id,
                                                         PersonaResponse.requirement_id == requirement_id)).all()
    agents = {a.id: a for a in session.scalars(select(Agent)).all()}
    by_market = defaultdict(list)
    for row in rows:
        by_market[agents[row.agent_id].market].append(row)
    summary = {}
    for market, items in by_market.items():
        stances = defaultdict(int)
        for r in items:
            stances[r.stance] += 1
        summary[market] = {
            "personas": len(items), "stances": dict(stances),
            "mean_importance_0_5": round(sum(r.importance_0_5 for r in items) / len(items), 2),
            "mean_class_fit_0_5": round(sum((r.market_fit_0_5 or 0) for r in items) / len(items), 2),
            "reactions": [{"persona": agents[r.agent_id].display_name, "validation": agents[r.agent_id].validation_status,
                           "stance": r.stance, "importance_0_5": r.importance_0_5,
                           "reaction": r.response_text.split("\n[raw]")[0][:400], "concerns": r.concerns} for r in items],
            "label": "SIMULATED owner reactions (hypotheses, not evidence)",
        }
    return summary


def build_package(session: Session, run_id, requirement: Requirement, scores: dict, sensitivity: dict | None,
                  challenge: str | None) -> tuple[dict, list[str]]:
    evidence, evidence_ids = _evidence_package(session, requirement)
    memos = session.scalars(select(DepartmentMemo).where(DepartmentMemo.run_id == run_id,
                                                         DepartmentMemo.requirement_id == requirement.id)).all()
    research_rows = session.scalars(select(ResearchRequest).where(ResearchRequest.run_id == run_id,
                                                                  ResearchRequest.requirement_id == requirement.id)).all()
    package = {
        "requirement": _requirement_payload(requirement),
        "evidence": evidence,
        "market_twin": _market_twin_summary(session, run_id, requirement.id),
        "company_twin": [{"department": m.agent_id, "stance": m.stance, "summary": m.memo.get("summary"),
                          "effort_band": m.memo.get("effort_band"), "ratings": m.memo.get("criterion_ratings"),
                          "risks": m.memo.get("risks"), "conditions": m.memo.get("conditions"),
                          "label": "SIMULATED department view (assumption)"} for m in memos],
        "research": [{"question": r.question, "requested_by": r.requested_by, "verdict": r.verdict,
                      "findings": [f for f in r.findings if "claim" in f][:6],
                      "verification": r.verification.get("checks", [])[:6]} for r in research_rows],
        "scores": scores,
        "rank_sensitivity": sensitivity,
        "gates": reqs.current_gates(session, requirement.id),
        "lessons_from_past_pm_decisions": relevant_lessons(session, requirement),
        "pm_challenge": challenge,
    }
    return package, evidence_ids


def synthesize_case(run_id: uuid.UUID, requirement_id: str, package: dict, evidence_ids: list[str]) -> dict:
    llm = get_llm()
    with session_scope() as session:
        requirement = session.get(Requirement, requirement_id)
    with _step(run_id, "synthesis", requirement_id, "agent:synthesizer") as detail:
        out = synthesis.synthesize(llm, requirement, package, evidence_ids, run_id)
        detail["recommended_next_action"] = out.recommended_next_action
    with session_scope() as session:
        session.add(Synthesis(run_id=run_id, requirement_id=requirement_id, content=out.model_dump()))
        requirement = session.get(Requirement, requirement_id)
        theme = next((t for t in reqs.themes_for(session, requirement)
                      if t.market == requirement.market), None)
        level, explanation = reqs.evidence_level(theme, has_simulation=True)
        changes = {
            "prioritization_rationale": out.prioritization_rationale,
            "assumptions": list(dict.fromkeys([*(requirement.assumptions or []), *out.assumptions])),
            "uncertainties": list(dict.fromkeys([*(requirement.uncertainties or []), *out.uncertainties])),
            "evidence_level": level, "evidence_level_explanation": explanation,
            "suggested_next_action": out.recommended_next_action,
        }
        locked = reqs.human_locked(session, requirement_id, [k for k in changes if k in reqs.EDITABLE_FIELDS])
        for field in locked:
            changes.pop(field)  # the PM wrote it last; the AI text stays available in the synthesis as a suggestion
        if requirement.status in ("draft", "proposed", "challenged", "investigate"):
            changes["status"] = "in_review"
        reqs.edit(session, requirement, changes, "agent:synthesizer",
                  f"Synthesis of run {run_id}" + (f"; kept PM-written fields: {sorted(locked)}" if locked else ""),
                  action="requirement.ai_update", run_id=run_id)
    return out.model_dump()


def vote_case(run_id: uuid.UUID, requirement_id: str, package: dict, synthesis_out: dict, evidence_ids: list[str],
              policy: dict) -> dict:
    settings = get_settings()
    llm = get_llm()
    with session_scope() as session:
        requirement = session.get(Requirement, requirement_id)
        judges = active_agents(session, "judge")
        gates = {g: v["value"] for g, v in reqs.current_gates(session, requirement_id).items()}
    compact = {"requirement": package["requirement"], "synthesis": synthesis_out, "scores": package["scores"],
               "gates": package["gates"], "evidence": {"themes_by_market": package["evidence"]["themes_by_market"],
                                                       "owner_quotes": package["evidence"]["owner_quotes"][:5]}}
    # The challenger argues first, so the judges vote knowing the strongest counter-case.
    with _step(run_id, "challenge", requirement_id, "agent:challenger") as detail:
        challenged = vote.challenge(llm, requirement, compact,
                                    {"proposed_next_action": synthesis_out.get("recommended_next_action"),
                                     "headline": synthesis_out.get("headline")},
                                    evidence_ids, run_id, settings.model_strong)
        detail["risk_if_outcome_is_wrong"] = challenged.risk_if_outcome_is_wrong
    compact["challenge"] = challenged.model_dump()
    votes = []
    with _step(run_id, "vote", requirement_id, "panel") as detail:
        with ThreadPoolExecutor(max_workers=max(1, len(judges))) as pool:
            futures = {pool.submit(vote.cast, llm, j.id, j.spec.get("model", settings.model_fast), requirement, compact,
                                   evidence_ids, run_id): j for j in judges}
            for future in as_completed(futures):
                judge = futures[future]
                votes.append((judge.id, judge.spec.get("model", settings.model_fast), future.result()))
        result = vote.tally([(j, v) for j, _, v in votes], gates, policy["parallax"]["vote"]["tie_breaker"])
        detail.update(result)
    with session_scope() as session:
        for judge_id, model, out in votes:
            session.add(Vote(run_id=run_id, requirement_id=requirement_id, agent_id=judge_id, model=model, vote=out.vote,
                             rationale=out.rationale, key_points=out.key_points))
        recommendation = Recommendation(run_id=run_id, requirement_id=requirement_id, recommendation=result["recommendation"],
                                        tally={k: v for k, v in result.items() if k != "minority"},
                                        minority_report=result["minority"], challenge=challenged.model_dump(),
                                        score_snapshot=package["scores"])
        session.add(recommendation)
        session.flush()
        record_event(session, category="ai", actor_id="system:panel", action="recommendation.create",
                     entity_type="recommendation", entity_id=str(recommendation.id), requirement_id=requirement_id,
                     run_id=run_id, after={"recommendation": result["recommendation"], "counts": result["counts"],
                                           "gate_cap": result["gate_cap"]})
    return result


# ------------------------------------------------------------------ main entry


def execute(run_id: uuid.UUID) -> None:
    settings = get_settings()
    try:
        with session_scope() as session:
            run = session.get(SimRun, run_id)
            run.status, run.started_at = "running", _now()
            requirement_ids = list(run.requirement_ids)
            challenge = run.challenge_question
            engine_name = run.config.get("persona_engine", settings.persona_engine)
            # Regional departments (e.g. Sales US) review only their market's cases and pooled cases.
            dept_markets = {a.id: a.market for a in active_agents(session, "department")}
            case_markets = {rid: session.get(Requirement, rid).market for rid in requirement_ids}
            policy = active_policy(session).document
        failures = 0

        # A: market twin || company twin
        _progress(run_id, stage="market_and_company_twin")
        info_requests: dict[str, list] = defaultdict(list)
        with ThreadPoolExecutor(max_workers=max(2, settings.max_parallel_cases * 2)) as pool:
            market_future = pool.submit(run_market_twin, run_id, requirement_ids, challenge, engine_name)
            dept_futures = {pool.submit(run_department, run_id, d, rid, challenge): rid
                            for rid in requirement_ids for d, market in dept_markets.items()
                            if market is None or case_markets[rid] is None or market == case_markets[rid]}
            for future in as_completed(dept_futures):
                try:
                    info_requests[dept_futures[future]] += future.result()["info_requests"]
                except Exception:
                    failures += 1
            try:
                market_future.result()
            except Exception:
                failures += 1
        with session_scope() as session:
            for row in session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == run_id)):
                for item in row.info_requests or []:
                    info_requests[row.requirement_id].append((row.agent_id, item["question"], item["why"]))
        _progress(run_id, stage_done="market_and_company_twin")

        # B: research loop
        _progress(run_id, stage="research")
        with ThreadPoolExecutor(max_workers=settings.max_parallel_cases) as pool:
            futures = [pool.submit(run_research_for_case, run_id, rid, info_requests.get(rid, [])) for rid in requirement_ids]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    failures += 1
        _progress(run_id, stage_done="research")

        # C: scoring (+ sensitivity across the cases of this run)
        _progress(run_id, stage="scoring")
        scores: dict[str, dict] = {}
        with session_scope() as session:
            for rid in requirement_ids:
                with _step(run_id, "scoring", rid, "code:mcda") as detail:
                    scores[rid] = score_case(session, run_id, session.get(Requirement, rid), policy)
                    detail.update({"score_low": scores[rid]["score_low"], "score_high": scores[rid]["score_high"]})
            sens = scoring.sensitivity(policy, scores) if len(scores) > 1 else {}
            overlaps = scoring.overlapping(scores)
            for rid, result in scores.items():
                result["overlapping_with"] = overlaps.get(rid, [])
                requirement = session.get(Requirement, rid)
                reqs.edit(session, requirement, {"score": result["score_midpoint"], "score_low": result["score_low"],
                                                 "score_high": result["score_high"], "last_run_id": run_id},
                          "code:mcda", f"MCDA scoring in run {run_id}", action="requirement.score", run_id=run_id)
        _progress(run_id, stage_done="scoring")

        # D + E: synthesis then vote, cases in parallel
        _progress(run_id, stage="synthesis_and_vote")

        def finish_case(rid: str) -> None:
            with session_scope() as session:
                package, evidence_ids = build_package(session, run_id, session.get(Requirement, rid), scores[rid],
                                                      sens.get(rid), challenge)
            synthesis_out = synthesize_case(run_id, rid, package, evidence_ids)
            vote_case(run_id, rid, package, synthesis_out, evidence_ids, policy)

        with ThreadPoolExecutor(max_workers=settings.max_parallel_cases) as pool:
            futures = [pool.submit(finish_case, rid) for rid in requirement_ids]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    failures += 1
        with session_scope() as session:
            reqs.rerank(session, run_id=run_id)
        _progress(run_id, stage_done="synthesis_and_vote")
        _finish(run_id, "partial" if failures else "completed", f"{failures} task(s) failed" if failures else None)
    except Exception as error:
        _finish(run_id, "failed", f"{error!r}\n{traceback.format_exc()[-3000:]}")


def execute_validation(run_id: uuid.UUID) -> None:
    llm = get_llm()
    try:
        with session_scope() as session:
            run = session.get(SimRun, run_id)
            run.status, run.started_at = "running", _now()
            agent_ids = run.config.get("options", {}).get("agent_ids") or [a.id for a in active_agents(session, "market_persona")]
            actor = run.requested_by
            include_examples = bool(run.config.get("options", {}).get("include_examples"))
        _progress(run_id, stage="persona_validation", total=len(agent_ids))
        failures = 0
        for agent_id in agent_ids:
            try:
                with _step(run_id, "validation", agent_id=agent_id) as detail:
                    with session_scope() as session:
                        result = validate_persona(session, llm, session.get(Agent, agent_id), run_id, actor, include_examples)
                    detail.update({k: v for k, v in result.items() if k != "per_attribute"})
            except Exception:
                failures += 1
        _finish(run_id, "partial" if failures else "completed", f"{failures} persona(s) failed" if failures else None)
    except Exception as error:
        _finish(run_id, "failed", f"{error!r}\n{traceback.format_exc()[-3000:]}")
