"""Operator-only maintenance. Requires the CLI token (never reachable through the frontend proxy)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from parallax.api.common import actor
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import get_session
from parallax.models import (
    Claim,
    CriterionRating,
    DepartmentMemo,
    Entity,
    Feature,
    Finding,
    GateState,
    IngestRun,
    Lesson,
    PersonaResponse,
    PMDecision,
    Recommendation,
    Record,
    RecordTriage,
    Requirement,
    RequirementEvidence,
    RequirementVersion,
    ResearchRequest,
    SimRun,
    SimStep,
    Source,
    Synthesis,
    Theme,
    Vote,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Children before parents. Agents, policy versions, the audit trail and the LLM call log are kept.
REQUIREMENT_TABLES = [Lesson, PMDecision, Vote, Recommendation, Synthesis, ResearchRequest, DepartmentMemo, PersonaResponse,
                      SimStep, CriterionRating, GateState, RequirementEvidence, RequirementVersion, Requirement, SimRun]
DATA_TABLES = REQUIREMENT_TABLES + [Finding, Theme, Claim, RecordTriage, Record, Source, IngestRun, Feature, Entity]


def require_cli(request: Request) -> None:
    if get_settings().cli_token and getattr(request.state, "credential", None) != "cli":
        raise HTTPException(403, "admin endpoints need the CLI token")


class ResetIn(BaseModel):
    confirm: Literal["DELETE ALL DATA", "DELETE REQUIREMENTS"]
    scope: Literal["all_data", "requirements"] = "all_data"
    rationale: str


@router.post("/reset", summary="Delete all evidence, themes, requirements and runs (keeps agents, policy, audit trail)")
def reset(body: ResetIn, request: Request, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    require_cli(request)
    if (body.scope == "all_data") != (body.confirm == "DELETE ALL DATA"):
        raise HTTPException(400, "confirm text does not match the scope")
    tables = DATA_TABLES if body.scope == "all_data" else REQUIREMENT_TABLES
    counts = {model.__tablename__: session.scalar(select(func.count()).select_from(model)) for model in tables}
    for model in tables:
        session.execute(delete(model))
    record_event(session, category="system", actor_id=who, action="data.reset", entity_type="database",
                 entity_id=body.scope, before=counts, after={table: 0 for table in counts}, rationale=body.rationale,
                 meta={"kept": ["agents", "agent_versions", "policy_versions", "audit_events", "llm_calls"]})
    return {"deleted": counts, "kept": ["agents", "policy_versions", "audit_events", "llm_calls"]}
