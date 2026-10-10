"""PM decisions and evidence review: the human-in-the-loop actions.

Evidence acceptance (is this source usable / may it reach an external LLM?) is deliberately separate
from requirement approval (should the successor vehicle have this?), as the research contract requires.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax import requirements as reqs
from parallax.audit import record_event
from parallax.learning import create_lesson, decision_snapshot, latest_recommendation
from parallax.models import Claim, PMDecision, Requirement, Source
from parallax.orchestrator import create_run

ACTION_STATUS = {"approve": "approved", "reject": "rejected", "challenge": "challenged", "defer": "deferred"}
ACTION_GATE = {"approve": "pass", "reject": "fail", "challenge": "unknown", "defer": "unknown"}
AI_EQUIVALENT = {"approve": "approve", "reject": "reject", "defer": "defer", "challenge": "investigate"}


class DecisionBlocked(RuntimeError):
    pass


def decide(session: Session, requirement: Requirement, action: str, rationale: str, actor_id: str,
           challenge_question: str | None = None) -> tuple[PMDecision, uuid.UUID | None]:
    if action not in ACTION_STATUS:
        raise ValueError(f"unknown action {action}")
    if not rationale.strip():
        raise ValueError("a rationale is required for every PM decision")
    gates = reqs.current_gates(session, requirement.id)
    open_or_failed = {g: v["value"] for g, v in gates.items() if g != "pm_review" and v["value"] != "pass"}
    if action == "approve" and open_or_failed:
        # Contract: failed checks need revision or rejection; unknown checks stay proposed/under investigation.
        raise DecisionBlocked(
            f"cannot approve while gates are not passed: {open_or_failed}. Revise the requirement, add evidence, "
            "or override the gate with a rationale (POST /api/requirements/{id}/gates/{gate}).")
    recommendation = latest_recommendation(session, requirement.id)
    snap = decision_snapshot(session, requirement)
    snap["open_gates_at_decision"] = [g for g, v in gates.items() if v["value"] == "unknown" and g != "pm_review"]
    decision = PMDecision(
        requirement_id=requirement.id, action=action, rationale=rationale, actor_id=actor_id,
        requirement_version=requirement.version, recommendation_id=recommendation.id if recommendation else None,
        ai_recommendation=recommendation.recommendation if recommendation else None,
        agreed_with_ai=(recommendation.recommendation == AI_EQUIVALENT[action]) if recommendation else None,
        snapshot=snap,
    )
    session.add(decision)
    session.flush()
    reqs.set_gate(session, requirement, "pm_review", ACTION_GATE[action], actor_id, rationale)
    reqs.edit(session, requirement, {"status": ACTION_STATUS[action]}, actor_id, rationale, action=f"requirement.{action}")
    record_event(session, category="decision", actor_id=actor_id, action=f"pm.{action}", entity_type="requirement",
                 entity_id=requirement.id, requirement_id=requirement.id,
                 after={"status": requirement.status, "ai_recommendation": decision.ai_recommendation,
                        "agreed_with_ai": decision.agreed_with_ai, "decision_id": decision.id},
                 rationale=rationale, meta={"challenge_question": challenge_question})
    create_lesson(session, decision, requirement)
    followup = None
    if action == "challenge":
        run = create_run(session, requirement_ids=[requirement.id], actor_id=actor_id, kind="followup",
                         challenge=challenge_question or rationale, parent_run_id=requirement.last_run_id)
        decision.followup_run_id = run.id
        followup = run.id
    return decision, followup


def override_gate(session: Session, requirement: Requirement, gate: str, value: str, actor_id: str, rationale: str) -> None:
    if value not in ("pass", "fail", "unknown"):
        raise ValueError("gate value must be pass, fail or unknown")
    if gate == "pm_review":
        raise ValueError("pm_review is set by PM decisions")
    if not rationale.strip():
        raise ValueError("a rationale is required to override a gate")
    reqs.set_gate(session, requirement, gate, value, actor_id, rationale, reference="pm_override")


def review_source(session: Session, source: Source, *, review_status: str, external_llm: bool | None, notes: str,
                  actor_id: str) -> Source:
    if review_status not in ("pending", "accepted", "rejected"):
        raise ValueError("review_status must be pending, accepted or rejected")
    before = {"review_status": source.review_status, "external_llm": source.external_llm}
    source.review_status = review_status
    source.external_llm = external_llm
    source.export_permissions = {**source.export_permissions, "external_llm": external_llm}
    provenance = dict(source.provenance)
    provenance["notes"] = ((provenance.get("notes") or "") + f"\n[{actor_id}] {notes}").strip()
    source.provenance = provenance
    record_event(session, category="evidence", actor_id=actor_id, action="evidence.source.review", entity_type="source",
                 entity_id=source.source_id, before=before, after={"review_status": review_status, "external_llm": external_llm},
                 rationale=notes)
    return source


def review_claim(session: Session, claim: Claim, review_status: str, notes: str, actor_id: str) -> Claim:
    if review_status not in ("pending", "accepted", "rejected"):
        raise ValueError("review_status must be pending, accepted or rejected")
    before = {"review_status": claim.review_status}
    claim.review_status = review_status
    record_event(session, category="evidence", actor_id=actor_id, action="evidence.claim.review", entity_type="claim",
                 entity_id=claim.claim_id, before=before, after={"review_status": review_status}, rationale=notes)
    return claim


def review_sources_bulk(session: Session, *, stream: str | None, channel: str | None, dataset_key: str | None,
                        review_status: str, external_llm: bool | None, notes: str, actor_id: str,
                        include_claims: bool = False) -> dict:
    query = select(Source)
    if stream:
        query = query.where(Source.stream == stream)
    if channel:
        query = query.where(Source.channel == channel)
    if dataset_key:
        query = query.where(Source.dataset_key == dataset_key)
    sources = session.scalars(query).all()
    for source in sources:
        review_source(session, source, review_status=review_status, external_llm=external_llm, notes=notes, actor_id=actor_id)
    claims_updated = 0
    if include_claims and sources:
        from parallax.models import Record

        ids = [s.source_id for s in sources]
        claims = session.scalars(select(Claim).join(Record, Record.record_id == Claim.record_id)
                                 .where(Record.source_id.in_(ids), Claim.review_status == "pending")).all()
        for claim in claims:
            claim.review_status = review_status
        claims_updated = len(claims)
        record_event(session, category="evidence", actor_id=actor_id, action="evidence.claims.bulk_review",
                     entity_type="source_set", entity_id=",".join(ids[:20]) + ("..." if len(ids) > 20 else ""),
                     after={"claims": claims_updated, "review_status": review_status}, rationale=notes)
    return {"sources": len(sources), "claims": claims_updated}
