"""Governance: meta, decision policy, audit trail, decision history and learning."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from parallax import __version__
from parallax.api.common import actor, human_actor, row
from parallax.api.schemas import AuditPageOut, TaskOut
from parallax.config import get_settings
from parallax.db import get_session
from parallax.learning import agreement_stats
from parallax.models import Agent, AuditEvent, Lesson, PMDecision, PolicyVersion, Requirement, SimRun
from parallax.policy import active_policy, publish_policy

router = APIRouter(prefix="/api", tags=["governance"])


@router.get("/health")
def health(session: Session = Depends(get_session, scope="function")):
    session.execute(select(1))
    return {"status": "ok", "version": __version__}


@router.get("/meta", summary="Runtime configuration the frontend may want to show")
def meta(session: Session = Depends(get_session, scope="function")):
    s = get_settings()
    policy = active_policy(session)
    return {
        "version": __version__, "llm_mode": s.llm_mode, "model_fast": s.model_fast, "model_strong": s.model_strong,
        "judge_models": s.judge_models, "embedding_model": s.embedding_model, "persona_engine": s.persona_engine,
        "target_model": s.target_model, "markets": s.markets, "max_parallel_cases": s.max_parallel_cases,
        "policy_version_id": policy.id, "allow_unreviewed_evidence_for_llm": s.allow_unreviewed_evidence_for_llm,
        "counts": {
            "requirements": session.scalar(select(func.count()).select_from(Requirement)),
            "agents": session.scalar(select(func.count()).select_from(Agent)),
            "runs": session.scalar(select(func.count()).select_from(SimRun)),
            "decisions": session.scalar(select(func.count()).select_from(PMDecision)),
        },
        "enums": {
            "requirement_status": ["draft", "proposed", "in_review", "approved", "rejected", "challenged", "deferred", "investigate"],
            "pm_actions": ["approve", "reject", "challenge", "defer"],
            "gates": ["customer_facing_scope", "model_market_applicability", "evidence_traceability", "pm_review"],
            "gate_values": ["pass", "fail", "unknown"],
            "rating_status": ["observed", "estimated", "simulated", "assumed", "unknown"],
            "evidence_level": ["strong", "moderate", "weak", "simulated_only", "none", "unassessed"],
            "recommendation": ["approve", "reject", "investigate", "defer"],
        },
    }


@router.get("/llm/models", summary="Configured model roles and which of them the OpenAI key can use")
def llm_models():
    from parallax.cli import _model_check

    return _model_check()


@router.get("/tasks", summary="What needs the PM now (sidebar 'My tasks')", response_model=list[TaskOut])
def tasks(session: Session = Depends(get_session, scope="function")):
    from parallax.learning import latest_recommendation
    from parallax.models import Source
    from parallax.requirements import current_gates

    items = []
    for req in session.scalars(select(Requirement).where(Requirement.status.in_(["in_review", "proposed", "draft"]))
                               .order_by(Requirement.priority_rank.asc().nulls_last(), Requirement.id)).all():
        rec = latest_recommendation(session, req.id)
        gates = {g: v["value"] for g, v in current_gates(session, req.id).items()}
        if req.status == "in_review":
            kind, label = "decide", f"Decide on {req.id}"
        else:
            kind, label = "simulate", f"Run Parallax on {req.id}"
        items.append({"kind": kind, "label": label, "requirement_id": req.id, "title": req.title, "market": req.market,
                      "ai_recommendation": rec.recommendation if rec else None, "score": req.score,
                      "score_low": req.score_low, "score_high": req.score_high,
                      "failed_gates": [g for g, v in gates.items() if v == "fail"]})
    running = session.scalars(select(SimRun).where(SimRun.status.in_(["queued", "running"]))).all()
    for run in running:
        if run.kind not in ("simulation", "followup"):
            continue  # condensing, labeling and validation jobs are not PM tasks
        items.append({"kind": "running", "label": f"Run {str(run.id)[:8]} is {run.status}", "run_id": str(run.id),
                      "requirement_ids": list(run.requirement_ids or []), "stage": (run.progress or {}).get("stage")})
    pending_sources = session.scalar(select(func.count()).select_from(Source).where(Source.review_status == "pending"))
    if pending_sources:
        items.append({"kind": "review_evidence", "label": f"{pending_sources} evidence source(s) await review",
                      "count": pending_sources})
    return items


@router.get("/policy")
def get_policy(session: Session = Depends(get_session, scope="function")):
    return row(active_policy(session))


@router.get("/policy/versions")
def policy_versions(session: Session = Depends(get_session, scope="function")):
    return [row(p, exclude={"document"}) for p in session.scalars(select(PolicyVersion).order_by(PolicyVersion.id)).all()]


class PolicyIn(BaseModel):
    document: dict
    rationale: str


@router.put("/policy", summary="Publish a new policy version (weights, anchors, persona weighting)")
def put_policy(body: PolicyIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    try:
        policy = publish_policy(session, body.document, human_actor(who), body.rationale)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return row(policy)


@router.get("/audit", summary="Chronological audit trail (changes, decisions, AI actions, evidence, access)",
            response_model=AuditPageOut)
def audit(requirement_id: str | None = None, actor_id: str | None = None, category: str | None = None,
          entity_type: str | None = None, entity_id: str | None = None, since: datetime | None = None,
          include_access: bool = False, limit: int = Query(200, le=2000), offset: int = 0,
          session: Session = Depends(get_session, scope="function")):
    query = select(AuditEvent)
    if requirement_id:
        query = query.where(AuditEvent.requirement_id == requirement_id)
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if category:
        query = query.where(AuditEvent.category == category)
    elif not include_access:
        query = query.where(AuditEvent.category != "access")
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if since:
        query = query.where(AuditEvent.occurred_at >= since)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(query.order_by(AuditEvent.id.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [row(e) for e in items]}


@router.get("/learning/decisions", summary="Decision history with AI-vs-PM agreement")
def decisions(session: Session = Depends(get_session, scope="function")):
    rows = session.scalars(select(PMDecision).order_by(PMDecision.id.desc())).all()
    return [row(d, exclude={"snapshot"}) for d in rows]


@router.get("/learning/agreement", summary="Per agent: how often its stance matched the PM's later decision")
def agreement(session: Session = Depends(get_session, scope="function")):
    return agreement_stats(session)


@router.get("/learning/lessons")
def lessons(feature_key: str | None = None, session: Session = Depends(get_session, scope="function")):
    query = select(Lesson)
    if feature_key:
        query = query.where(Lesson.feature_key == feature_key)
    return [row(l, exclude={"embedding"}) for l in session.scalars(query.order_by(Lesson.id.desc())).all()]
