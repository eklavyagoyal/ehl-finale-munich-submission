"""Agents: personas, departments, judges and workers; specs, versions, validation."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.agents.grounding import persona_grounding
from parallax.agents.roster import seed_agents, upsert_agent
from parallax.api.common import actor, human_actor, not_found, row
from parallax.config import get_settings
from parallax.db import get_session
from parallax.models import Agent, AgentVersion
from parallax.orchestrator import create_run, launch
from parallax.policy import active_policy

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", summary="All agents; filter by kind: market_persona, department, judge, drafter, research, verifier, synthesizer")
def list_agents(kind: str | None = None, session: Session = Depends(get_session)):
    query = select(Agent)
    if kind:
        query = query.where(Agent.kind == kind)
    return [row(a) for a in session.scalars(query.order_by(Agent.kind, Agent.id)).all()]


@router.post("/seed", summary="Sync personas/departments from roster JSON files and register worker agents")
def seed(session: Session = Depends(get_session), who: str = Depends(actor)):
    return seed_agents(session, who)


@router.get("/{agent_id}")
def get_agent(agent_id: str, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise not_found("agent", agent_id)
    versions = session.scalars(select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.version)).all()
    return {"agent": row(agent), "versions": [row(v, exclude={"spec"}) for v in versions]}


@router.get("/{agent_id}/grounding", summary="Preview which real records a persona would see (after the LLM gate)")
def grounding(agent_id: str, include_examples: bool = False, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if agent is None or agent.kind != "market_persona":
        raise not_found("persona", agent_id)
    g = persona_grounding(session, agent, active_policy(session).document, get_settings().grounding_quotes_per_persona,
                          include_examples)
    return {"quotes": g.quotes, "study": g.study, "gate": g.gate}


class SpecIn(BaseModel):
    spec: dict
    rationale: str


@router.put("/{agent_id}", summary="Replace a persona/department spec (new version; personas need re-validation)")
def update_spec(agent_id: str, body: SpecIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise not_found("agent", agent_id)
    spec = {**body.spec, "id": agent_id, "kind": agent.kind}
    if "display_name" not in spec:
        spec["display_name"] = agent.display_name
    updated, outcome = upsert_agent(session, spec, human_actor(who), body.rationale)
    return {"outcome": outcome, "agent": row(updated)}


class ActiveIn(BaseModel):
    active: bool
    rationale: str


@router.post("/{agent_id}/active")
def set_active(agent_id: str, body: ActiveIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    from parallax.audit import record_event

    agent = session.get(Agent, agent_id)
    if agent is None:
        raise not_found("agent", agent_id)
    before = agent.active
    agent.active = body.active
    record_event(session, category="change", actor_id=human_actor(who), action="agent.active", entity_type="agent",
                 entity_id=agent_id, before={"active": before}, after={"active": body.active}, rationale=body.rationale)
    return row(agent)


class ValidateIn(BaseModel):
    agent_ids: list[str] | None = None
    include_examples: bool = False


@router.post("/validate", summary="Validate personas against held-out study data (background run)")
def validate(body: ValidateIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    if body.agent_ids:
        for agent_id in body.agent_ids:
            agent = session.get(Agent, agent_id)
            if agent is None or agent.kind != "market_persona":
                raise HTTPException(400, f"{agent_id} is not a market persona")
    run = create_run(session, requirement_ids=[], actor_id=who, kind="validation",
                     options={"agent_ids": body.agent_ids, "include_examples": body.include_examples})
    session.commit()
    launch(run.id)
    return row(run)
