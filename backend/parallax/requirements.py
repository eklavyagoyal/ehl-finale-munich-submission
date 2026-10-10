"""Requirement lifecycle: create, version, edit, link evidence, observed ratings and code gates."""

import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from parallax.audit import diff, record_event
from parallax.models import (
    CriterionRating,
    GateState,
    Record,
    Requirement,
    RequirementEvidence,
    RequirementVersion,
    Theme,
)

EDITABLE_FIELDS = {
    "title", "description", "customer_problem", "acceptance_criteria", "assumptions", "uncertainties",
    "market", "evidence_level", "evidence_level_explanation", "prioritization_rationale", "planning_horizon",
    "kano_class", "kano_rationale", "benchmark_target",
}
KANO_CLASSES = {"must_be", "performance", "attractive", "indifferent", "reverse", "unclear"}
STATUSES = {"draft", "proposed", "in_review", "approved", "rejected", "challenged", "deferred", "investigate"}

SNAPSHOT_FIELDS = [
    "id", "target_model", "market", "feature_key", "title", "description", "customer_problem", "acceptance_criteria",
    "evidence_level", "evidence_level_explanation", "assumptions", "uncertainties", "planning_horizon", "status",
    "priority_rank", "score", "score_low", "score_high", "prioritization_rationale", "suggested_next_action",
    "kano_class", "kano_rationale", "benchmark_target", "version",
]


def snapshot(requirement: Requirement) -> dict:
    data = {}
    for name in SNAPSHOT_FIELDS:
        value = getattr(requirement, name)
        data[name] = value.isoformat() if isinstance(value, datetime) else value
    return data


def next_id(session: Session, target_model: str) -> str:
    code = target_model.split(":")[-1]
    prefix = f"REQ-{code}-"
    existing = session.scalars(select(Requirement.id).where(Requirement.id.like(f"{prefix}%"))).all()
    numbers = [int(m.group(1)) for rid in existing if (m := re.search(r"(\d+)$", rid))]
    return f"{prefix}{(max(numbers) if numbers else 0) + 1:04d}"


def _version(session: Session, requirement: Requirement, actor_id: str, reason: str) -> None:
    from parallax.audit import actor_type_of

    session.add(RequirementVersion(
        requirement_id=requirement.id, version=requirement.version, snapshot=snapshot(requirement),
        actor_type=actor_type_of(actor_id), actor_id=actor_id, change_reason=reason,
    ))


def create(session: Session, fields: dict, actor_id: str, reason: str, run_id=None) -> Requirement:
    requirement = Requirement(id=next_id(session, fields["target_model"]), created_by=actor_id, version=1,
                              status=fields.pop("status", "proposed"), **fields)
    session.add(requirement)
    session.flush()
    _version(session, requirement, actor_id, reason)
    record_event(session, category="change", actor_id=actor_id, action="requirement.create", entity_type="requirement",
                 entity_id=requirement.id, requirement_id=requirement.id, run_id=run_id, after=snapshot(requirement),
                 rationale=reason)
    return requirement


def edit(session: Session, requirement: Requirement, changes: dict, actor_id: str, rationale: str,
         action: str = "requirement.edit", run_id=None) -> Requirement:
    unknown = set(changes) - EDITABLE_FIELDS - {"status", "score", "score_low", "score_high", "priority_rank",
                                                "suggested_next_action", "last_run_id"}
    if unknown:
        raise ValueError(f"not editable: {sorted(unknown)}")
    if "status" in changes and changes["status"] not in STATUSES:
        raise ValueError(f"unknown status {changes['status']}")
    if changes.get("kano_class") is not None and changes["kano_class"] not in KANO_CLASSES:
        raise ValueError(f"kano_class must be one of {sorted(KANO_CLASSES)}")
    before = snapshot(requirement)
    content_change = any(k in EDITABLE_FIELDS for k in changes)
    for key, value in changes.items():
        setattr(requirement, key, value)
    after_full = snapshot(requirement)
    before_diff, after_diff = diff(before, after_full)
    if not after_diff:
        return requirement
    if content_change or "status" in changes:
        requirement.version += 1
        after_full["version"] = requirement.version
        after_diff["version"] = requirement.version
        _version(session, requirement, actor_id, rationale)
    record_event(session, category="change", actor_id=actor_id, action=action, entity_type="requirement",
                 entity_id=requirement.id, requirement_id=requirement.id, run_id=run_id, before=before_diff,
                 after=after_diff, rationale=rationale)
    return requirement


def last_editor(session: Session, requirement_id: str, field: str) -> str | None:
    """Actor of the most recent version that changed `field` (None if never changed after creation)."""
    versions = session.scalars(select(RequirementVersion).where(RequirementVersion.requirement_id == requirement_id)
                               .order_by(RequirementVersion.version.desc())).all()
    for newer, older in zip(versions, versions[1:]):
        if newer.snapshot.get(field) != older.snapshot.get(field):
            return newer.actor_id
    return None


def human_locked(session: Session, requirement_id: str, fields) -> set[str]:
    """Fields whose latest change came from a human; AI updates must not overwrite them."""
    return {f for f in fields if is_human(last_editor(session, requirement_id, f))}


def link_evidence(session: Session, requirement: Requirement, record_id: str, relation: str, actor_id: str,
                  quote: str | None = None, claim_id: str | None = None, rationale: str = "", run_id=None) -> RequirementEvidence:
    record = session.get(Record, record_id)
    if record is None:
        raise ValueError(f"unknown record {record_id}")
    verified = bool(quote) and quote in (record.text_original or "") or (bool(quote) and quote in (record.translation_en or ""))
    link = RequirementEvidence(requirement_id=requirement.id, record_id=record_id, claim_id=claim_id, relation=relation,
                               quote=quote, quote_verified=verified if quote else True, added_by=actor_id)
    session.add(link)
    record_event(session, category="evidence", actor_id=actor_id, action="requirement.evidence.link",
                 entity_type="requirement", entity_id=requirement.id, requirement_id=requirement.id, run_id=run_id,
                 after={"record_id": record_id, "relation": relation, "quote_verified": link.quote_verified},
                 rationale=rationale or None)
    return link


def themes_for(session: Session, requirement: Requirement) -> list[Theme]:
    if not requirement.feature_key:
        return []
    latest = session.scalars(
        select(Theme.snapshot_id).where(Theme.target_model == requirement.target_model).order_by(Theme.id.desc()).limit(1)
    ).first()
    if latest is None:
        return []
    return list(session.scalars(select(Theme).where(Theme.snapshot_id == latest, Theme.feature_key == requirement.feature_key)).all())


def add_observed_ratings(session: Session, requirement: Requirement, run_id=None) -> list[CriterionRating]:
    """Demand and impact from deterministic theme counts (status observed, rater code)."""
    themes = {t.market: t for t in themes_for(session, requirement)}
    theme = themes.get(requirement.market) if requirement.market else themes.get(None)
    if theme is None:
        return []
    ratings = [CriterionRating(
        requirement_id=requirement.id, run_id=run_id, criterion="demand", score=theme.demand_score, status="observed",
        rater_type="code", rater_id="code:theme-counts",
        rationale=(f"{theme.mention_review_count} distinct reviews mention '{theme.label}' "
                   f"({theme.direct_review_count} directly about {requirement.target_model}); max within-cohort share "
                   f"{theme.max_cohort_share:.1%} across {len(theme.channels)} channel(s). Anchors: policy demand_anchors."),
        evidence_ids=theme.record_ids[:200],
    )]
    if theme.impact_score is not None:
        ratings.append(CriterionRating(
            requirement_id=requirement.id, run_id=run_id, criterion="impact", score=theme.impact_score, status="observed",
            rater_type="code", rater_id="code:claim-mix",
            rationale=(f"Claim mix of supporting reviews: {theme.counts_by_claim_type}; pain (defect/difficult to use) "
                       f"{theme.pain_review_count}, requests {theme.request_review_count}, praise {theme.praise_review_count}."),
            evidence_ids=theme.record_ids[:200],
        ))
    session.add_all(ratings)
    return ratings


def set_gate(session: Session, requirement: Requirement, gate: str, value: str, owner: str, reason: str,
             reference: str | None = None, run_id=None) -> GateState:
    return _set_gate(session, requirement, gate, value, owner, reason, reference, run_id)


def _set_gate(session: Session, requirement: Requirement, gate: str, value: str, owner: str, reason: str,
              reference: str | None = None, run_id=None) -> GateState:
    current = current_gates(session, requirement.id).get(gate)
    state = GateState(requirement_id=requirement.id, gate=gate, value=value, owner=owner, reason=reason,
                      reference=reference, run_id=run_id)
    session.add(state)
    if current is None or current["value"] != value or current["reason"] != reason:
        record_event(session, category="change", actor_id=owner, action="requirement.gate", entity_type="requirement",
                     entity_id=requirement.id, requirement_id=requirement.id, run_id=run_id,
                     before={gate: current["value"]} if current else None, after={gate: value}, rationale=reason)
    return state


def current_gates(session: Session, requirement_id: str) -> dict[str, dict]:
    rows = session.scalars(select(GateState).where(GateState.requirement_id == requirement_id).order_by(GateState.id)).all()
    gates: dict[str, dict] = {}
    for row in rows:
        gates[row.gate] = {"value": row.value, "owner": row.owner, "reason": row.reason, "reference": row.reference,
                           "at": row.created_at.isoformat() if row.created_at else None}
    return gates


def is_human(actor_id: str | None) -> bool:
    return bool(actor_id) and actor_id.startswith(("pm:", "user:"))


def refresh_code_gates(session: Session, requirement: Requirement, run_id=None) -> None:
    """Recompute automatic gates. A gate whose latest state was set by a human (PM override or
    decision) is left alone: automatic checks never silently revert a human judgment."""
    existing = current_gates(session, requirement.id)

    def set_gate(session, requirement, gate, value, owner, reason, run_id=None):
        state = existing.get(gate)
        if state and (is_human(state["owner"]) or state.get("reference") == "pm_override"):
            return
        _set_gate(session, requirement, gate, value, owner, reason, run_id=run_id)

    links = session.scalars(select(RequirementEvidence).where(RequirementEvidence.requirement_id == requirement.id)).all()
    supporting = [l for l in links if l.relation == "supporting"]
    if not supporting:
        set_gate(session, requirement, "evidence_traceability", "unknown", "system:gates", "No linked supporting evidence yet.", run_id=run_id)
    elif all(l.quote_verified for l in supporting):
        set_gate(session, requirement, "evidence_traceability", "pass", "system:gates",
                 f"{len(supporting)} supporting record(s) exist; all quotes match the original text.", run_id=run_id)
    else:
        bad = sum(not l.quote_verified for l in supporting)
        set_gate(session, requirement, "evidence_traceability", "fail", "system:gates",
                 f"{bad} linked quote(s) do not match their record text.", run_id=run_id)

    themes = {t.market: t for t in themes_for(session, requirement)}
    theme = themes.get(requirement.market) if requirement.market else themes.get(None)
    if theme is None:
        set_gate(session, requirement, "model_market_applicability", "unknown", "system:gates",
                 "No theme evidence for this feature/market.", run_id=run_id)
    elif theme.direct_review_count > 0:
        set_gate(session, requirement, "model_market_applicability", "pass", "system:gates",
                 f"{theme.direct_review_count} review(s) directly about {requirement.target_model}"
                 + (f" in {requirement.market}" if requirement.market else ""), run_id=run_id)
    else:
        set_gate(session, requirement, "model_market_applicability", "unknown", "system:gates",
                 "Only combined-model, brand-wide or unresolved evidence; applicability to the target model is not established.",
                 run_id=run_id)
    if "pm_review" not in existing:
        _set_gate(session, requirement, "pm_review", "unknown", "system:gates", "Awaiting PM decision.", run_id=run_id)


def evidence_level(theme: Theme | None, has_simulation: bool) -> tuple[str, str]:
    """Deterministic evidence level, so it never depends on an LLM's self-assessment."""
    if theme is None or theme.mention_review_count == 0:
        return ("simulated_only" if has_simulation else "none",
                "No real customer evidence linked; any support comes from simulation or assumptions.")
    channels = len(theme.channels)
    if theme.demand_score >= 3 and theme.direct_review_count > 0 and channels >= 2:
        return "strong", f"{theme.mention_review_count} reviews across {channels} channels, including direct target-model evidence."
    if theme.demand_score >= 2:
        return "moderate", f"{theme.mention_review_count} reviews; corroboration across channels or direct evidence is limited."
    return "weak", f"Only {theme.mention_review_count} review(s) mention this feature."


def rerank(session: Session, run_id=None) -> None:
    """Priority rank over all open requirements by score midpoint (bounds overlap is reported separately).
    Every changed rank is an audited priority change."""
    open_reqs = session.scalars(
        select(Requirement).where(Requirement.status.notin_(["rejected"]), Requirement.score.is_not(None))
    ).all()
    for rank, requirement in enumerate(sorted(open_reqs, key=lambda r: -(r.score or 0)), 1):
        if requirement.priority_rank != rank:
            before = requirement.priority_rank
            requirement.priority_rank = rank
            record_event(session, category="change", actor_id="code:rank", action="requirement.priority",
                         entity_type="requirement", entity_id=requirement.id, requirement_id=requirement.id, run_id=run_id,
                         before={"priority_rank": before}, after={"priority_rank": rank},
                         rationale=f"Re-ranked by score midpoint ({requirement.score}) across {len(open_reqs)} open requirements"
                                   + (f" after run {run_id}" if run_id else ""))


def count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Requirement)) or 0
