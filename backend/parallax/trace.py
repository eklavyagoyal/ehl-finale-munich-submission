"""Decision trace: one ordered, aggregated explanation of how a requirement got its recommendation.

Each step answers: who was involved, what they received, what they concluded, why, on which basis
(evidence / simulation / assumption / human) and in which direction it pushed. Steps hold aggregates and
top-3 items only, so the trace stays readable no matter how much data sits underneath; every step
names the endpoint for drill-down.
"""

import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax import requirements as reqs
from parallax import scoring
from parallax.models import (
    Agent,
    CriterionRating,
    DepartmentMemo,
    PersonaResponse,
    PMDecision,
    Recommendation,
    Record,
    RequirementEvidence,
    ResearchRequest,
    Requirement,
    Source,
    Synthesis,
    Vote,
)
from parallax.policy import active_policy
from parallax.signals import classify, finding_order, latest_findings

EFFECT_OF_VERDICT = {"for": "supports", "against": "against", "conditional": "neutral"}


def _short(text: str | None, limit: int = 110) -> str | None:
    """First sentence, cut to one line: the headline a PM reads before opening the step."""
    if not text:
        return None
    first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
    return first if len(first) <= limit else first[:limit - 1].rstrip() + "…"


def _agents(session: Session) -> dict[str, Agent]:
    return {a.id: a for a in session.scalars(select(Agent))}


def build_trace(session: Session, requirement: Requirement) -> dict:
    agents = _agents(session)
    run_id = requirement.last_run_id
    steps: list[dict] = []

    # 1 evidence -------------------------------------------------------------------------------
    themes = {t.market: t for t in reqs.themes_for(session, requirement)}
    theme = themes.get(requirement.market) if requirement.market else themes.get(None)
    findings = latest_findings(session, requirement.market, [requirement.feature_key] if requirement.feature_key else [])
    findings = findings.get(requirement.feature_key, []) if requirement.feature_key else []
    findings = sorted(findings, key=finding_order(classify(theme) if theme else None))
    links = session.execute(
        select(RequirementEvidence.relation, Source.stream, Source.channel)
        .join(Record, Record.record_id == RequirementEvidence.record_id).join(Source, Source.source_id == Record.source_id)
        .where(RequirementEvidence.requirement_id == requirement.id)
    ).all()
    by_channel = Counter(f"{stream}/{channel}" for _, stream, channel in links)
    steps.append({
        "key": "evidence", "title": "Why this requirement exists", "question": "What do real customers report?",
        "headline": (f"{theme.mention_review_count} reviews · " if theme else "") + (findings[0].title if findings else
                    f"{theme.pain_review_count if theme else 0} report a problem"),
        "agents": [{"id": "code:theme-counts", "name": "Counting (code)", "kind": "code"},
                   {"id": "agent:condenser", "name": "Condenser", "kind": "agent"}, {"id": "agent:drafter", "name": "Drafter", "kind": "agent"}],
        "basis": "evidence",
        "inputs": {"signal": theme.label if theme else requirement.feature_key, "market": requirement.market or "all",
                   "reviews": theme.mention_review_count if theme else 0, "complaints": theme.pain_review_count if theme else 0,
                   "requests": theme.request_review_count if theme else 0, "praise": theme.praise_review_count if theme else 0,
                   "linked_evidence_by_channel": dict(by_channel)},
        "output": [{"finding": f.title, "kind": f.kind, "reviews": f.review_count, "share": f.share_of_theme} for f in findings[:3]],
        "why": requirement.customer_problem or requirement.description,
        "effect": "supports" if theme and theme.pain_review_count else "neutral",
        "drill_down": f"/api/requirements/{requirement.id} (evidence) · /api/signals?market={requirement.market or ''}",
    })
    if run_id is None:
        steps.append({"key": "not_simulated", "title": "Expert pipeline not run yet", "basis": "none", "headline": "Not run yet",
                      "why": "Run Parallax to get the customer council, company council, research and a recommendation.",
                      "effect": "neutral"})
        return _envelope(requirement, steps, session)

    # 2 customer council --------------------------------------------------------------------------
    owners = session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == run_id,
                                                           PersonaResponse.requirement_id == requirement.id)).all()
    markets: dict[str, dict] = {}
    for p in owners:
        market = agents[p.agent_id].market if p.agent_id in agents else "other"
        m = markets.setdefault(market, {"personas": 0, "verdicts": Counter(), "budget": [], "concerns": Counter()})
        m["personas"] += 1
        m["verdicts"][p.verdict or "unknown"] += 1
        if p.budget_points is not None:
            m["budget"].append(p.budget_points)
        for concern in p.concerns or []:
            m["concerns"][concern] += 1
    market_rows = []
    for market, m in sorted(markets.items()):
        budget = round(sum(m["budget"]) / len(m["budget"]), 1) if m["budget"] else None
        market_rows.append({"market": market, "personas": m["personas"], "verdicts": dict(m["verdicts"]),
                            "mean_budget_points_of_100": budget, "top_concern": m["concerns"].most_common(1)[0][0] if m["concerns"] else None,
                            "validated": market == "US", "basis": "simulation" if market == "US" else "assumption"})
    all_budget = [b for m in markets.values() for b in m["budget"]]
    mean_budget = round(sum(all_budget) / len(all_budget), 1) if all_budget else None
    must = sum(m["verdicts"].get("must_have", 0) for m in markets.values())
    asked = "/".join(sorted(markets)) or "no"
    customer_headline = (f"{must}/{len(owners)} must-have · {mean_budget} of 100 points · {asked} owners"
                         if mean_budget is not None else "No verdicts in this run")
    if mean_budget is None:
        customer_why = "This run did not ask the owners for verdicts or budget points (older run); see their free-text reactions."
        customer_effect = "neutral"
    else:
        customer_why = f"{must} of {len(owners)} owners call it a must-have; on average {mean_budget} of 100 budget points."
        customer_effect = "supports" if mean_budget >= 20 else ("against" if mean_budget < 10 else "neutral")
    steps.append({
        "key": "customers", "title": "Customer council", "question": "Would owners pay for it?", "headline": customer_headline,
        "agents": [{"id": a, "name": agents[a].display_name, "kind": "persona"} for a in sorted({p.agent_id for p in owners}) if a in agents],
        "basis": "simulation",
        "inputs": {"asked": "React to each proposal, give a verdict and split 100 points between proposals and 'keep the price down'",
                   "owners": len(owners)},
        "output": market_rows,
        "why": customer_why,
        "effect": customer_effect,
        "caveat": "Simulated owners. Validated against the BMW customer study for the US (rho about 0.5-0.6); EU weak, China untestable.",
        "drill_down": f"/api/requirements/{requirement.id}/council · /api/simulations/{run_id}/conversation",
    })

    # 3 company council ---------------------------------------------------------------------------
    memos = session.scalars(select(DepartmentMemo).where(DepartmentMemo.run_id == run_id,
                                                         DepartmentMemo.requirement_id == requirement.id)).all()
    synthesis = session.scalars(select(Synthesis).where(Synthesis.run_id == run_id, Synthesis.requirement_id == requirement.id)).first()
    content = synthesis.content if synthesis else {}
    tensions = content.get("tensions") or []
    verdicts = Counter(m.memo.get("verdict") or "unknown" for m in memos)
    company_headline = (f"Tension: {tensions[0].get('topic')}" if tensions else
                        " · ".join(f"{n} {v}" for v, n in verdicts.most_common()) or "No department answered")
    steps.append({
        "key": "company", "title": "Company council", "question": "What does BMW internally think?", "headline": company_headline,
        "agents": [{"id": m.agent_id, "name": agents[m.agent_id].display_name if m.agent_id in agents else m.agent_id, "kind": "department"} for m in memos],
        "basis": "assumption",
        "inputs": {"asked": "Review the requirement from your department's perspective: clear position, main argument, cost view"},
        "output": [{"department": agents[m.agent_id].display_name if m.agent_id in agents else m.agent_id,
                    "verdict": m.memo.get("verdict"), "main_argument": m.memo.get("main_argument"), "cost_view": m.memo.get("cost_view")}
                   for m in memos],
        "tensions": [{"topic": t.get("topic"), "customers_say": t.get("customers_say"), "company_says": t.get("company_says")} for t in tensions[:3]],
        "why": content.get("company_view") or "",
        "effect": "neutral",
        "caveat": "Simulated departments: use the arguments and tensions, not the verdict labels (validation: verdicts rarely differ).",
        "drill_down": f"/api/requirements/{requirement.id}/council",
    })

    # 4 research -----------------------------------------------------------------------------------
    research = session.scalars(select(ResearchRequest).where(ResearchRequest.run_id == run_id,
                                                             ResearchRequest.requirement_id == requirement.id)).all()
    steps.append({
        "key": "research", "title": "Research and verification", "question": "What do external sources say?",
        "headline": (f"{sum(r.verdict in ('verified', 'partially_verified') for r in research)}/{len(research)} answers verified"
                     if research else "No open questions"),
        "agents": [{"id": "agent:research", "name": "Web research", "kind": "agent"}, {"id": "agent:verifier", "name": "Verifier", "kind": "agent"}],
        "basis": "evidence",
        "inputs": {"questions_raised_by": dict(Counter(r.requested_by for r in research))},
        "output": [{"question": r.question, "verdict": r.verdict,
                    "answer": next((f.get("answer_summary") for f in r.findings if "answer_summary" in f), None)} for r in research[:3]],
        "why": f"{sum(r.verdict in ('verified', 'partially_verified') for r in research)} of {len(research)} answers (partially) verified.",
        "effect": "neutral",
        "drill_down": f"/api/requirements/{requirement.id} (research)",
    })

    # 5 scoring ------------------------------------------------------------------------------------
    policy = active_policy(session).document
    ratings = session.scalars(select(CriterionRating).where(CriterionRating.requirement_id == requirement.id,
                                                            (CriterionRating.run_id == run_id) | (CriterionRating.rater_type == "pm"))).all()
    scores = scoring.compute(policy, list(ratings))
    criteria = []
    for key, c in scores["criteria"].items():
        low = c["score"] if c["score"] is not None else c["low"]
        high = c["score"] if c["score"] is not None else c["high"]
        criteria.append({"criterion": key, "weight": c["weight"], "status": c["status"],
                         "points_low": round(20 * c["weight"] * low, 1), "points_high": round(20 * c["weight"] * high, 1)})
    steps.append({
        "key": "scores", "title": "Score", "question": "How does it rank under the decision model?",
        "headline": (f"{round(scores['score_low'])}-{round(scores['score_high'])} of 100"
                     if scores.get("score_low") is not None and scores.get("score_high") is not None else "Not scored"),
        "agents": [{"id": "code:mcda", "name": "Scoring (code)", "kind": "code"}], "basis": "mixed",
        "inputs": {"formula": scores["formula"]},
        "output": {"score_low": scores["score_low"], "score_high": scores["score_high"], "rank": requirement.priority_rank,
                   "criteria": criteria},
        "why": "Observed criteria come from real reviews; simulated and assumed criteria only widen the range.",
        "effect": "neutral", "drill_down": f"/api/requirements/{requirement.id} (scores, ratings)",
    })

    # 6 synthesis, 7 challenger, 8 judge --------------------------------------------------------
    steps.append({
        "key": "synthesis", "title": "Synthesis", "question": "What is the overall picture?",
        "headline": _short(content.get("headline") or content.get("customer_view")),
        "agents": [{"id": "agent:synthesizer", "name": "Synthesizer", "kind": "agent"}], "basis": "mixed",
        "output": {"headline": content.get("headline"), "customer_view": content.get("customer_view"),
                   "evidence_vs_simulation": content.get("evidence_vs_simulation"),
                   "clinic_questions": (content.get("clinic_questions") or [])[:3]},
        "why": content.get("prioritization_rationale"), "effect": "neutral",
    })
    rec = session.scalars(select(Recommendation).where(Recommendation.run_id == run_id,
                                                       Recommendation.requirement_id == requirement.id)).first()
    challenge = rec.challenge if rec else {}
    steps.append({
        "key": "challenger", "title": "Challenger", "question": "What could make this wrong?",
        "headline": _short(challenge.get("counter_position")) or f"Risk if wrong: {challenge.get('risk_if_outcome_is_wrong', 'n/a')}",
        "agents": [{"id": "agent:challenger", "name": "Challenger", "kind": "agent"}], "basis": "mixed",
        "output": {"counter_position": challenge.get("counter_position"), "strongest_arguments": (challenge.get("strongest_arguments") or [])[:3],
                   "evidence_that_would_change_the_call": (challenge.get("evidence_that_would_change_the_call") or [])[:3]},
        "why": f"Risk if the proposal is wrong: {challenge.get('risk_if_outcome_is_wrong', 'n/a')}", "effect": "against",
    })
    votes = session.scalars(select(Vote).where(Vote.run_id == run_id, Vote.requirement_id == requirement.id)).all()
    vote = votes[0] if votes else None
    extra = next((k for k in (vote.key_points if vote else []) if isinstance(k, dict)), {})
    steps.append({
        "key": "judge", "title": "Recommendation", "question": "What should the PM do?",
        "headline": ((rec.recommendation or "").replace("_", " ").capitalize() + (" · capped by open gates" if (rec.tally or {}).get("gate_cap") else "")
                     if rec else "No recommendation"),
        "agents": [{"id": v.agent_id, "name": f"Judge ({v.model})", "kind": "judge"} for v in votes], "basis": "mixed",
        "output": {"recommendation": rec.recommendation if rec else None, "gate_cap": (rec.tally or {}).get("gate_cap") if rec else None,
                   "drivers": extra.get("drivers", []), "what_would_change_it": extra.get("what_would_change_it")},
        "why": vote.rationale if vote else None,
        "effect": {"approve": "supports", "reject": "against"}.get(rec.recommendation if rec else "", "neutral"),
    })
    return _envelope(requirement, steps, session)


def _envelope(requirement: Requirement, steps: list[dict], session: Session) -> dict:
    gates = reqs.current_gates(session, requirement.id)
    decisions = session.scalars(select(PMDecision).where(PMDecision.requirement_id == requirement.id).order_by(PMDecision.id)).all()
    blocking = [g for g, v in gates.items() if g != "pm_review" and v["value"] != "pass"]
    steps.append({
        "key": "decision", "title": "Your decision", "question": "Approve, reject, challenge or defer?",
        "headline": (f"Decided: {requirement.status}" if decisions and requirement.status in ("approved", "rejected", "deferred")
                     else f"{len(blocking)} gate(s) open: " + ", ".join(g.replace("_", " ") for g in blocking) if blocking
                     else "Ready to decide"),
        "agents": [{"id": "pm", "name": "Product manager", "kind": "human"}], "basis": "human",
        "output": {"status": requirement.status, "gates": {g: v["value"] for g, v in gates.items()},
                   "blocking_gates": blocking,
                   "decisions": [{"action": d.action, "by": d.actor_id, "at": d.created_at.isoformat(), "rationale": d.rationale,
                                  "agreed_with_ai": d.agreed_with_ai} for d in decisions]},
        "why": "Approval needs every gate on pass; every decision is recorded with its rationale.", "effect": "neutral",
        "drill_down": f"/api/requirements/{requirement.id}/audit",
    })
    for index, step in enumerate(steps, 1):
        step["order"] = index
    return {"requirement_id": requirement.id, "title": requirement.title, "market": requirement.market,
            "legend": {"evidence": "real data", "simulation": "simulated owners", "assumption": "simulated departments",
                       "mixed": "combines several", "human": "your decision"},
            "text_levels": "headline = one line shown by default; why/output = the long form on request",
            "steps": steps}
