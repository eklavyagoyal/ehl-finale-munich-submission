"""Decision history and learning hooks.

Every PM decision stores a full snapshot of what the AI recommended and why (ratings, gates, votes,
persona and department stances, policy and agent versions). That history enables:
  * agreement statistics per agent (which personas/departments/judges track PM judgment),
  * lessons: PM rationales retrieved for similar features in later runs,
  * later: calibrating policy weights or persona weights from accumulated decisions.
"""

import math
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.llm.client import get_llm
from parallax.models import (
    Agent,
    CriterionRating,
    DepartmentMemo,
    Feature,
    Lesson,
    PersonaResponse,
    PMDecision,
    PolicyVersion,
    Recommendation,
    Requirement,
    Synthesis,
    Vote,
)
from parallax.requirements import current_gates, snapshot

AGREEMENT = {
    # PM action -> AI outputs that count as agreeing
    "approve": {"approve", "positive", "support"},
    "reject": {"reject", "negative", "oppose"},
    "defer": {"defer", "neutral", "unsure"},
    "challenge": {"investigate", "neutral", "unsure"},
}


def latest_recommendation(session: Session, requirement_id: str) -> Recommendation | None:
    return session.scalars(select(Recommendation).where(Recommendation.requirement_id == requirement_id)
                           .order_by(Recommendation.id.desc()).limit(1)).first()


def decision_snapshot(session: Session, requirement: Requirement) -> dict:
    recommendation = latest_recommendation(session, requirement.id)
    run_id = recommendation.run_id if recommendation else requirement.last_run_id
    snap: dict = {"requirement": snapshot(requirement), "gates": current_gates(session, requirement.id)}
    policy = session.scalars(select(PolicyVersion).where(PolicyVersion.active.is_(True))).first()
    snap["policy_version_id"] = policy.id if policy else None
    if recommendation:
        snap["recommendation"] = {"id": recommendation.id, "value": recommendation.recommendation,
                                  "tally": recommendation.tally, "scores": recommendation.score_snapshot}
    if run_id:
        snap["run_id"] = str(run_id)
        snap["votes"] = [{"agent_id": v.agent_id, "model": v.model, "vote": v.vote}
                         for v in session.scalars(select(Vote).where(Vote.run_id == run_id, Vote.requirement_id == requirement.id))]
        snap["personas"] = [{"agent_id": p.agent_id, "version": p.agent_version, "stance": p.stance,
                             "importance_0_5": p.importance_0_5}
                            for p in session.scalars(select(PersonaResponse).where(
                                PersonaResponse.run_id == run_id, PersonaResponse.requirement_id == requirement.id))]
        snap["departments"] = [{"agent_id": m.agent_id, "version": m.agent_version, "stance": m.stance,
                                "effort_band": m.memo.get("effort_band")}
                               for m in session.scalars(select(DepartmentMemo).where(
                                   DepartmentMemo.run_id == run_id, DepartmentMemo.requirement_id == requirement.id))]
        snap["ratings"] = [{"criterion": r.criterion, "score": r.score, "low": r.low, "high": r.high, "status": r.status,
                            "rater_id": r.rater_id}
                           for r in session.scalars(select(CriterionRating).where(
                               CriterionRating.run_id == run_id, CriterionRating.requirement_id == requirement.id))]
        synthesis = session.scalars(select(Synthesis).where(Synthesis.run_id == run_id, Synthesis.requirement_id == requirement.id)).first()
        if synthesis:
            snap["synthesis_headline"] = synthesis.content.get("headline")
    return snap


def agreed(pm_action: str, ai_value: str | None) -> bool | None:
    if ai_value is None:
        return None
    return ai_value in AGREEMENT.get(pm_action, set())


def create_lesson(session: Session, decision: PMDecision, requirement: Requirement) -> Lesson:
    feature = session.get(Feature, requirement.feature_key) if requirement.feature_key else None
    text = (f"PM {decision.action} '{requirement.title}' ({requirement.market or 'all markets'}): {decision.rationale}")
    embedding = None
    try:
        embedding = get_llm().embed([text], purpose="lesson_embedding")[0]
    except Exception:  # lessons work without embeddings (feature/area matching)
        embedding = None
    lesson = Lesson(decision_id=decision.id, requirement_id=requirement.id, feature_key=requirement.feature_key,
                    area=feature.area if feature else None, market=requirement.market, action=decision.action,
                    text=text, embedding=embedding)
    session.add(lesson)
    return lesson


def _cos(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((math.sqrt(sum(x * x for x in a)) or 1) * (math.sqrt(sum(y * y for y in b)) or 1))


def relevant_lessons(session: Session, requirement: Requirement, k: int = 3) -> list[dict]:
    lessons = session.scalars(select(Lesson).where(Lesson.requirement_id != requirement.id).order_by(Lesson.id.desc()).limit(500)).all()
    if not lessons:
        return []
    feature = session.get(Feature, requirement.feature_key) if requirement.feature_key else None
    query_vec = None
    try:
        query_vec = get_llm().embed([f"{requirement.title}: {requirement.description}"], purpose="lesson_query")[0]
    except Exception:
        query_vec = None
    scored = []
    for lesson in lessons:
        score = 0.0
        if requirement.feature_key and lesson.feature_key == requirement.feature_key:
            score += 2.0
        if feature and lesson.area and lesson.area == feature.area:
            score += 1.0
        if query_vec and lesson.embedding:
            score += _cos(query_vec, lesson.embedding)
        scored.append((score, lesson))
    scored.sort(key=lambda pair: -pair[0])
    return [{"text": l.text, "action": l.action, "feature_key": l.feature_key, "market": l.market, "relevance": round(s, 3)}
            for s, l in scored[:k] if s > 0.3]


def agreement_stats(session: Session) -> list[dict]:
    """Per agent: how often its stance/vote matched the later PM decision."""
    stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "agree": 0})
    for decision in session.scalars(select(PMDecision).where(PMDecision.action.in_(list(AGREEMENT)))).all():
        snap = decision.snapshot or {}
        outputs = [(v["agent_id"], v["vote"]) for v in snap.get("votes", [])]
        outputs += [(p["agent_id"], p["stance"]) for p in snap.get("personas", [])]
        outputs += [(d["agent_id"], d["stance"]) for d in snap.get("departments", [])]
        if snap.get("recommendation"):
            outputs.append(("panel:recommendation", snap["recommendation"]["value"]))
        for agent_id, value in outputs:
            stats[agent_id]["n"] += 1
            stats[agent_id]["agree"] += int(agreed(decision.action, value) or False)
    names = {a.id: a.display_name for a in session.scalars(select(Agent)).all()}
    return sorted(
        [{"agent_id": aid, "display_name": names.get(aid, aid), "decisions": s["n"], "agreements": s["agree"],
          "agreement_rate": round(s["agree"] / s["n"], 3) if s["n"] else None} for aid, s in stats.items()],
        key=lambda row: (-(row["decisions"]), row["agent_id"]),
    )
