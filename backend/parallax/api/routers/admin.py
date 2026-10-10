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
    GateState,
    IngestRun,
    Lesson,
    PersonaResponse,
    PMDecision,
    Recommendation,
    Record,
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
DATA_TABLES = [Lesson, PMDecision, Vote, Recommendation, Synthesis, ResearchRequest, DepartmentMemo, PersonaResponse,
               SimStep, CriterionRating, GateState, RequirementEvidence, RequirementVersion, Requirement, SimRun,
               Theme, Claim, Record, Source, IngestRun, Feature, Entity]


def require_cli(request: Request) -> None:
    if get_settings().cli_token and getattr(request.state, "credential", None) != "cli":
        raise HTTPException(403, "admin endpoints need the CLI token")


class ResetIn(BaseModel):
    confirm: Literal["DELETE ALL DATA"]
    rationale: str


@router.post("/reset", summary="Delete all evidence, themes, requirements and runs (keeps agents, policy, audit trail)")
def reset(body: ResetIn, request: Request, session: Session = Depends(get_session), who: str = Depends(actor)):
    require_cli(request)
    counts = {model.__tablename__: session.scalar(select(func.count()).select_from(model)) for model in DATA_TABLES}
    for model in DATA_TABLES:
        session.execute(delete(model))
    record_event(session, category="system", actor_id=who, action="data.reset", entity_type="database",
                 entity_id="all_data", before=counts, after={table: 0 for table in counts}, rationale=body.rationale,
                 meta={"kept": ["agents", "agent_versions", "policy_versions", "audit_events", "llm_calls"]})
    return {"deleted": counts, "kept": ["agents", "policy_versions", "audit_events", "llm_calls"]}
