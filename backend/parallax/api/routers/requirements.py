"""Requirements: list, detail, draft, create, edit, evidence links, gates, PM decisions, history."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax import decisions
from parallax import requirements as reqs
from parallax.agents.drafter import draft_requirements
from parallax.api.common import actor, human_actor, not_found, row
from parallax.provenance import claims_for, sources_for
from parallax.api.schemas import AuditEventOut, DecisionResultOut, RequirementDetailOut, RequirementOut
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import get_session
from parallax.llm.client import get_llm
from parallax.models import (
    AuditEvent,
    CriterionRating,
    DepartmentMemo,
    PersonaResponse,
    PMDecision,
    Recommendation,
    Record,
    Requirement,
    RequirementEvidence,
    RequirementVersion,
    ResearchRequest,
    Synthesis,
    Vote,
)
from parallax.orchestrator import launch
from parallax.policy import active_policy
from parallax.scoring import compute
from parallax.themes import latest_snapshot_id

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


def summary(requirement: Requirement, session: Session) -> dict:
    data = row(requirement)
    data["gates"] = {g: v["value"] for g, v in reqs.current_gates(session, requirement.id).items()}
    rec = session.scalars(select(Recommendation).where(Recommendation.requirement_id == requirement.id)
                          .order_by(Recommendation.id.desc()).limit(1)).first()
    data["ai_recommendation"] = rec.recommendation if rec else None
    data["progress"] = _progress(requirement, session, rec)
    return data


def _progress(requirement: Requirement, session: Session, rec) -> list[dict]:
    """Where the requirement stands in the pipeline: drafted -> councils -> AI recommendation -> PM decision.
    The AI recommendation is advice; only the last step is a decision."""
    from parallax.models import PMDecision, SimRun

    run = session.get(SimRun, requirement.last_run_id) if requirement.last_run_id else None
    decision = session.scalars(select(PMDecision).where(PMDecision.requirement_id == requirement.id)
                               .order_by(PMDecision.id.desc()).limit(1)).first()
    decided = requirement.status in ("approved", "rejected", "deferred")
    return [
        {"key": "drafted", "label": "Drafted", "done": True, "at": requirement.created_at.isoformat(), "value": requirement.created_by},
        {"key": "councils", "label": "Councils", "done": bool(run and run.status in ("completed", "partial")),
         "at": run.finished_at.isoformat() if run and run.finished_at else None, "value": run.status if run else "not_run"},
        {"key": "recommendation", "label": "AI suggests", "done": rec is not None, "at": None,
         "value": rec.recommendation if rec else None},
        {"key": "decision", "label": "Your decision", "done": decided,
         "at": decision.created_at.isoformat() if decision and decided else None,
         "value": requirement.status if decided else None},
    ]


@router.get("", summary="Requirement list with the eight brief fields, gates and latest AI recommendation",
            response_model=list[RequirementOut])
def list_requirements(status: str | None = None, market: str | None = None, feature_key: str | None = None,
                      sort: Literal["priority", "score", "created", "updated"] = "priority",
                      session: Session = Depends(get_session, scope="function")):
    query = select(Requirement)
    if status:
        query = query.where(Requirement.status == status)
    if market:
        query = query.where(Requirement.market == market)
    if feature_key:
        query = query.where(Requirement.feature_key == feature_key)
    order = {
        "priority": (Requirement.priority_rank.asc().nulls_last(), Requirement.id),
        "score": (Requirement.score.desc().nulls_last(), Requirement.id),
        "created": (Requirement.created_at.desc(),),
        "updated": (Requirement.updated_at.desc(),),
    }[sort]
    return [summary(r, session) for r in session.scalars(query.order_by(*order)).all()]


class DraftIn(BaseModel):
    market: str | None = Field(None, description="US, EU, CN or null for all markets pooled")
    limit: int = Field(5, ge=1, le=30)
    feature_keys: list[str] | None = None


@router.post("/draft", summary="AI drafts candidate requirements from the strongest themes")
def draft(body: DraftIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    settings = get_settings()
    snapshot = latest_snapshot_id(session, settings.target_model)
    if snapshot is None:
        raise HTTPException(409, "no theme snapshot yet; POST /api/themes/build first")
    record_event(session, category="ai", actor_id=who, action="requirements.draft.request",
                 after={"market": body.market, "limit": body.limit, "feature_keys": body.feature_keys})
    return draft_requirements(session, get_llm(), target_model=settings.target_model, snapshot_id=snapshot,
                              market=body.market, limit=body.limit, actor_id=who, feature_keys=body.feature_keys)


class RequirementIn(BaseModel):
    title: str
    description: str
    customer_problem: str = ""
    market: str | None = None
    feature_key: str | None = None
    acceptance_criteria: list[str] = []
    assumptions: list[str] = []
    uncertainties: list[str] = []
    rationale: str = "Created manually by PM"


@router.post("", summary="PM creates a requirement manually", response_model=RequirementOut)
def create(body: RequirementIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    fields = body.model_dump(exclude={"rationale"})
    fields["target_model"] = get_settings().target_model
    requirement = reqs.create(session, fields, human_actor(who), body.rationale)
    reqs.add_observed_ratings(session, requirement)
    reqs.refresh_code_gates(session, requirement)
    return summary(requirement, session)


@router.get("/{requirement_id}", summary="Everything about one requirement, for the PM detail view",
            response_model=RequirementDetailOut)
def detail(requirement_id: str, session: Session = Depends(get_session, scope="function")):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    run_id = requirement.last_run_id
    evidence = session.execute(
        select(RequirementEvidence, Record).join(Record, Record.record_id == RequirementEvidence.record_id)
        .where(RequirementEvidence.requirement_id == requirement_id).order_by(RequirementEvidence.id)
    ).all()
    latest = lambda model: session.scalars(select(model).where(model.requirement_id == requirement_id, model.run_id == run_id)).all() if run_id else []
    in_scope = (CriterionRating.run_id == run_id) if run_id else CriterionRating.run_id.is_(None)
    ratings = session.scalars(select(CriterionRating).where(
        CriterionRating.requirement_id == requirement_id, in_scope | (CriterionRating.rater_type == "pm"),
    )).all()
    policy = active_policy(session).document
    sources = sources_for(session, {rec.source_id for _, rec in evidence})
    claims = claims_for(session, {rec.record_id for _, rec in evidence}, requirement.feature_key)
    return {
        "requirement": summary(requirement, session),
        "gates": reqs.current_gates(session, requirement_id),
        "scores": compute(policy, list(ratings)),
        "ratings": [row(r) for r in ratings],
        "evidence": [{**row(link),
                      "record": {"text": rec.text_original, "translation_en": rec.translation_en, "language": rec.language,
                                 "markets": rec.markets, "subject_ids": rec.subject_ids, "source_id": rec.source_id,
                                 "locator": rec.locator, "content_date": rec.content_date.isoformat() if rec.content_date else None,
                                 "record_kind": rec.record_kind},
                      "source": sources.get(rec.source_id),
                      "claims": claims.get(rec.record_id, [])}
                     for link, rec in evidence],
        "latest_run_id": str(run_id) if run_id else None,
        "synthesis": next((row(s) for s in latest(Synthesis)), None),
        "recommendation": next((row(r) for r in latest(Recommendation)), None),
        "votes": [row(v) for v in latest(Vote)],
        "persona_responses": [row(p) for p in latest(PersonaResponse)],
        "department_memos": [row(m) for m in latest(DepartmentMemo)],
        "research": [row(r) for r in latest(ResearchRequest)],
        "decisions": [row(d, exclude={"snapshot"}) for d in session.scalars(
            select(PMDecision).where(PMDecision.requirement_id == requirement_id).order_by(PMDecision.id)).all()],
    }


class EditIn(BaseModel):
    changes: dict = Field(description=f"Any of: {sorted(reqs.EDITABLE_FIELDS)}")
    rationale: str


@router.patch("/{requirement_id}", summary="PM edits requirement content (new version, audited)", response_model=RequirementOut)
def edit(requirement_id: str, body: EditIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    if not body.rationale.strip():
        raise HTTPException(400, "rationale required")
    bad = set(body.changes) - reqs.EDITABLE_FIELDS
    if bad:
        raise HTTPException(400, f"not editable here: {sorted(bad)} (status changes go through /decision)")
    reqs.edit(session, requirement, body.changes, human_actor(who), body.rationale)
    return summary(requirement, session)


class DecisionIn(BaseModel):
    action: Literal["approve", "reject", "challenge", "defer"]
    rationale: str
    challenge_question: str | None = Field(None, description="For 'challenge': what the agents should re-examine")


@router.post("/{requirement_id}/decision", summary="PM approves, rejects, challenges or defers (approve needs all gates passed)",
             response_model=DecisionResultOut)
def decide(requirement_id: str, body: DecisionIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    try:
        decision, followup = decisions.decide(session, requirement, body.action, body.rationale, human_actor(who),
                                              body.challenge_question)
    except decisions.DecisionBlocked as error:
        raise HTTPException(409, str(error))
    except ValueError as error:
        raise HTTPException(400, str(error))
    session.commit()
    if followup:
        launch(followup)
    return {"decision": row(decision, exclude={"snapshot"}), "followup_run_id": str(followup) if followup else None,
            "requirement": summary(requirement, session)}


class GateIn(BaseModel):
    value: Literal["pass", "fail", "unknown"]
    rationale: str


@router.post("/{requirement_id}/gates/{gate}", summary="PM overrides a gate with a rationale")
def set_gate(requirement_id: str, gate: str, body: GateIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    try:
        decisions.override_gate(session, requirement, gate, body.value, human_actor(who), body.rationale)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return reqs.current_gates(session, requirement_id)


class EvidenceIn(BaseModel):
    record_id: str
    relation: Literal["supporting", "contradicting", "context"]
    quote: str | None = None
    rationale: str


@router.post("/{requirement_id}/evidence", summary="PM links a record as supporting/contradicting evidence")
def add_evidence(requirement_id: str, body: EvidenceIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    try:
        link = reqs.link_evidence(session, requirement, body.record_id, body.relation, human_actor(who), body.quote,
                                  rationale=body.rationale)
    except ValueError as error:
        raise HTTPException(400, str(error))
    reqs.refresh_code_gates(session, requirement)
    return row(link)


class RatingIn(BaseModel):
    criterion: Literal["demand", "impact", "competitive_gap", "vehicle_market_fit", "delivery_fit", "reuse"]
    score: float | None = Field(None, ge=0, le=5)
    low: float | None = Field(None, ge=0, le=5)
    high: float | None = Field(None, ge=0, le=5)
    status: Literal["observed", "estimated", "assumed"] = "estimated"
    rationale: str
    evidence_ids: list[str] = []


@router.post("/{requirement_id}/ratings", summary="PM adds a criterion rating (e.g. a reviewed scoring anchor)")
def add_rating(requirement_id: str, body: RatingIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    if body.score is None and (body.low is None or body.high is None):
        raise HTTPException(400, "give a score or a low/high range")
    rating = CriterionRating(requirement_id=requirement_id, criterion=body.criterion, score=body.score, low=body.low,
                             high=body.high, status=body.status, rater_type="pm", rater_id=human_actor(who),
                             rationale=body.rationale, evidence_ids=body.evidence_ids)
    session.add(rating)
    session.flush()
    record_event(session, category="change", actor_id=who, action="requirement.rating", entity_type="requirement",
                 entity_id=requirement_id, requirement_id=requirement_id, after=row(rating), rationale=body.rationale)
    return row(rating)


@router.get("/{requirement_id}/versions")
def versions(requirement_id: str, session: Session = Depends(get_session, scope="function")):
    return [row(v) for v in session.scalars(select(RequirementVersion).where(
        RequirementVersion.requirement_id == requirement_id).order_by(RequirementVersion.version)).all()]


@router.get("/{requirement_id}/audit", summary="Chronological audit trail for one requirement",
            response_model=list[AuditEventOut])
def audit(requirement_id: str, include_access: bool = False, session: Session = Depends(get_session, scope="function")):
    query = select(AuditEvent).where(AuditEvent.requirement_id == requirement_id)
    if not include_access:
        query = query.where(AuditEvent.category != "access")
    return [row(e) for e in session.scalars(query.order_by(AuditEvent.id)).all()]


@router.get("/{requirement_id}/decisions/{decision_id}/snapshot", summary="What the AI recommended when the PM decided")
def decision_snapshot(requirement_id: str, decision_id: int, session: Session = Depends(get_session, scope="function")):
    decision = session.get(PMDecision, decision_id)
    if decision is None or decision.requirement_id != requirement_id:
        raise not_found("decision", decision_id)
    return row(decision)


@router.get("/{requirement_id}/council",
            summary="Customer council vs company council for the latest run: who said what, tensions, challenger, judges")
def council(requirement_id: str, session: Session = Depends(get_session, scope="function")):
    from collections import Counter

    from parallax.models import Agent, SimStep

    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    run_id = requirement.last_run_id
    if run_id is None:
        return {"requirement_id": requirement_id, "run_id": None, "status": "not_simulated"}
    agents = {a.id: a for a in session.scalars(select(Agent))}
    owners = session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == run_id,
                                                           PersonaResponse.requirement_id == requirement_id)).all()
    by_market: dict[str, dict] = {}
    for p in owners:
        agent = agents.get(p.agent_id)
        spec = agent.spec if agent else {}
        market = by_market.setdefault(agent.market if agent else "other", {"personas": []})
        market["personas"].append({
            "agent_id": p.agent_id, "name": spec.get("persona", {}).get("name"), "display_name": agent.display_name if agent else p.agent_id,
            "vehicle": spec.get("vehicle_label"), "powertrain": spec.get("powertrain"), "verdict": p.verdict,
            "budget_points": p.budget_points, "importance_0_5": p.importance_0_5, "stance": p.stance,
            "quote": p.response_text.split("\n[raw] ")[0], "concerns": p.concerns,
            "validation_status": agent.validation_status if agent else None,
        })
    for market in by_market.values():
        people = market["personas"]
        verdicts = Counter(x["verdict"] or "unknown" for x in people)
        budgets = [x["budget_points"] for x in people if x["budget_points"] is not None]
        importance = [x["importance_0_5"] for x in people if x["importance_0_5"] is not None]
        market["summary"] = {"personas": len(people), "verdicts": dict(verdicts),
                             "mean_budget_points_of_100": round(sum(budgets) / len(budgets), 1) if budgets else None,
                             "mean_importance_0_5": round(sum(importance) / len(importance), 2) if importance else None}
    memos = session.scalars(select(DepartmentMemo).where(DepartmentMemo.run_id == run_id,
                                                         DepartmentMemo.requirement_id == requirement_id)).all()
    departments = [{
        "agent_id": m.agent_id, "display_name": agents[m.agent_id].display_name if m.agent_id in agents else m.agent_id,
        "market": agents[m.agent_id].market if m.agent_id in agents else None,
        "verdict": m.memo.get("verdict") or {"support": "for", "oppose": "against"}.get(m.stance, "conditional"),
        "main_argument": m.memo.get("main_argument") or m.memo.get("summary"),
        "strongest_counterargument": m.memo.get("strongest_counterargument"), "cost_view": m.memo.get("cost_view"),
        "effort_band": m.memo.get("effort_band"), "risks": m.memo.get("risks", []),
    } for m in memos]
    synthesis = session.scalars(select(Synthesis).where(Synthesis.run_id == run_id, Synthesis.requirement_id == requirement_id)).first()
    content = synthesis.content if synthesis else {}
    rec = session.scalars(select(Recommendation).where(Recommendation.run_id == run_id,
                                                       Recommendation.requirement_id == requirement_id)).first()
    votes = session.scalars(select(Vote).where(Vote.run_id == run_id, Vote.requirement_id == requirement_id)).all()
    research = session.scalars(select(ResearchRequest).where(ResearchRequest.run_id == run_id,
                                                             ResearchRequest.requirement_id == requirement_id)).all()
    twin = session.scalars(select(SimStep).where(SimStep.run_id == run_id, SimStep.stage == "market_twin")).first()
    return {
        "requirement_id": requirement_id, "title": requirement.title, "run_id": str(run_id), "status": "simulated",
        "question_to_owners": (twin.detail or {}).get("question") if twin else None,
        "customers": {"by_market": by_market, "view": content.get("customer_view")},
        "company": {"departments": departments, "view": content.get("company_view"),
                    "verdicts": dict(Counter(d["verdict"] for d in departments))},
        "tensions": content.get("tensions") or [{"topic": c.get("between"), "customers_say": None, "company_says": None,
                                                 "resolution_options": [], "description": c.get("description")}
                                                for c in content.get("conflicts", [])],
        "headline": content.get("headline"),
        "research": [{"requested_by": r.requested_by, "question": r.question, "verdict": r.verdict} for r in research],
        "challenger": rec.challenge if rec else None,
        "judges": [{"agent_id": v.agent_id, "model": v.model, "vote": v.vote, "rationale": v.rationale} for v in votes],
        "recommendation": rec.recommendation if rec else None,
        "order": ["customer council + company council (parallel)", "research + verifier", "scoring", "synthesis",
                  "challenger", "judges", "PM decision"],
    }


@router.get("/{requirement_id}/trace",
            summary="Decision path: per step who was involved, what they got, what they concluded, why, basis and effect")
def trace(requirement_id: str, session: Session = Depends(get_session, scope="function")):
    from parallax.trace import build_trace

    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise not_found("requirement", requirement_id)
    return build_trace(session, requirement)
