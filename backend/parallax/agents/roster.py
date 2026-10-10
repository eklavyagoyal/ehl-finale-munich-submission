"""Agent roster: market personas and departments come from editable JSON files in roster/;
worker agents (drafter, research, verifier, synthesizer, judges) are defined here.

Seeding is idempotent. A changed spec bumps the agent version and stores the previous spec,
so every simulation output can be traced to the exact persona/department version.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.audit import record_event
from parallax.config import get_settings
from parallax.models import Agent, AgentVersion

ROSTER_DIR = Path(__file__).parent / "roster"

WORKER_AGENTS = [
    {"id": "agent:drafter", "kind": "drafter", "display_name": "Requirement drafter",
     "spec": {"role": "Turns theme signals and cited evidence into the eight requirement fields; checks scope.", "model_role": "strong"}},
    {"id": "agent:research", "kind": "research", "display_name": "Web research agent",
     "spec": {"role": "Answers information requests raised by personas or departments using web search.", "model_role": "fast"}},
    {"id": "agent:verifier", "kind": "verifier", "display_name": "Verifier (expensive model)",
     "spec": {"role": "Checks every research claim against its cited source before it may influence a decision.", "model_role": "strong"}},
    {"id": "agent:synthesizer", "kind": "synthesizer", "display_name": "Synthesizer",
     "spec": {"role": "Crystallizes market twin, company twin, research and scores into one brief for the PM.", "model_role": "strong"}},
    {"id": "agent:challenger", "kind": "challenger", "display_name": "Challenger (devil's advocate)",
     "spec": {"role": "Makes the strongest case against the panel's outcome so the PM sees what could make it wrong.", "model_role": "strong"}},
]


def judge_agents() -> list[dict]:
    return [
        {"id": f"judge:{index + 1}", "kind": "judge", "display_name": f"Judge {index + 1} ({model})",
         "spec": {"role": "Votes approve/reject/investigate/defer as a recommendation to the PM.", "model": model}}
        for index, model in enumerate(get_settings().judge_models)
    ]


def load_roster_files() -> list[dict]:
    specs = []
    for folder in ("personas", "departments"):
        for path in sorted((ROSTER_DIR / folder).glob("*.json")):
            specs.append(json.loads(path.read_text(encoding="utf-8")))
    return specs


def _row_from_spec(spec: dict) -> dict:
    return {
        "kind": spec["kind"],
        "display_name": spec["display_name"],
        "market": spec.get("market"),
        "country": spec.get("country"),
        "vehicle": spec.get("vehicle"),
        "powertrain": spec.get("powertrain"),
        "segment": spec.get("segment"),
        "details_status": spec.get("details_status", "complete"),
    }


def upsert_agent(session: Session, spec: dict, actor_id: str, reason: str) -> tuple[Agent, str]:
    agent = session.get(Agent, spec["id"])
    if agent is None:
        agent = Agent(id=spec["id"], spec=spec, version=1, **_row_from_spec(spec))
        session.add(agent)
        session.flush()
        session.add(AgentVersion(agent_id=agent.id, version=1, spec=spec, actor_id=actor_id, reason=reason))
        record_event(session, category="change", actor_id=actor_id, action="agent.create", entity_type="agent",
                     entity_id=agent.id, after={"version": 1}, rationale=reason)
        return agent, "created"
    if agent.spec == spec:
        return agent, "unchanged"
    before = agent.version
    agent.spec = spec
    agent.version += 1
    for key, value in _row_from_spec(spec).items():
        setattr(agent, key, value)
    # A changed persona must be validated again.
    if agent.kind == "market_persona":
        agent.validation_status = "not_validated"
        agent.validation_metrics = {}
    session.add(AgentVersion(agent_id=agent.id, version=agent.version, spec=spec, actor_id=actor_id, reason=reason))
    record_event(session, category="change", actor_id=actor_id, action="agent.update", entity_type="agent",
                 entity_id=agent.id, before={"version": before}, after={"version": agent.version}, rationale=reason)
    return agent, "updated"


def seed_agents(session: Session, actor_id: str = "system:seed") -> dict:
    summary = {"created": 0, "updated": 0, "unchanged": 0, "deactivated": 0}
    files = load_roster_files()
    for spec in files:
        _, outcome = upsert_agent(session, spec, actor_id, "roster file sync")
        summary[outcome] += 1
    # A persona/department whose roster file was removed stops taking part (history is kept).
    in_files = {spec["id"] for spec in files}
    for agent in session.scalars(select(Agent).where(Agent.kind.in_(["market_persona", "department"]), Agent.active.is_(True))):
        if agent.id not in in_files:
            agent.active = False
            summary["deactivated"] += 1
            record_event(session, category="change", actor_id=actor_id, action="agent.deactivate", entity_type="agent",
                         entity_id=agent.id, before={"active": True}, after={"active": False},
                         rationale="roster file removed")
    for worker in WORKER_AGENTS + judge_agents():
        spec = {**worker["spec"], "id": worker["id"], "kind": worker["kind"], "display_name": worker["display_name"],
                "details_status": "complete"}
        _, outcome = upsert_agent(session, spec, actor_id, "worker agent sync")
        summary[outcome] += 1
    return summary


def active_agents(session: Session, kind: str) -> list[Agent]:
    return list(session.scalars(select(Agent).where(Agent.kind == kind, Agent.active.is_(True)).order_by(Agent.id)).all())
