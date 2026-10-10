"""Simulation runs: start, follow progress, read results and the LLM call log."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.api.common import actor, not_found, row
from parallax.api.schemas import LLMCallOut, RunDetailOut, RunOut
from parallax.db import get_session
from parallax.models import (
    CriterionRating,
    DepartmentMemo,
    LLMCall,
    PersonaResponse,
    Recommendation,
    ResearchRequest,
    SimRun,
    SimStep,
    Synthesis,
    Vote,
)
from parallax.orchestrator import create_run, launch

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(400, "invalid run id")


class SimulationIn(BaseModel):
    requirement_ids: list[str] = Field(min_length=1, max_length=20, description="Cases run in parallel (default 5 at a time)")
    challenge: str | None = Field(None, description="Optional PM question every agent must address")
    persona_engine: Literal["tinytroupe", "direct"] | None = None


@router.post("", summary="Start a Parallax run (market twin || company twin -> research -> scoring -> synthesis -> vote)",
             response_model=RunOut)
def start(body: SimulationIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    try:
        run = create_run(session, requirement_ids=body.requirement_ids, actor_id=who, challenge=body.challenge,
                         options={"persona_engine": body.persona_engine} if body.persona_engine else {})
    except ValueError as error:
        raise HTTPException(400, str(error))
    session.commit()
    launch(run.id)
    return row(run)


@router.get("", response_model=list[RunOut])
def list_runs(kind: str | None = None, limit: int = Query(50, le=200), session: Session = Depends(get_session)):
    query = select(SimRun)
    if kind:
        query = query.where(SimRun.kind == kind)
    return [row(r) for r in session.scalars(query.order_by(SimRun.created_at.desc()).limit(limit)).all()]


@router.get("/{run_id}", summary="Run status, progress and step trace (poll this)", response_model=RunDetailOut)
def get_run(run_id: str, session: Session = Depends(get_session)):
    run = session.get(SimRun, _uuid(run_id))
    if run is None:
        raise not_found("run", run_id)
    steps = session.scalars(select(SimStep).where(SimStep.run_id == run.id).order_by(SimStep.id)).all()
    return {"run": row(run), "steps": [row(s) for s in steps]}


@router.get("/{run_id}/results", summary="All agent outputs of a run, grouped by requirement")
def results(run_id: str, session: Session = Depends(get_session)):
    rid = _uuid(run_id)
    run = session.get(SimRun, rid)
    if run is None:
        raise not_found("run", run_id)
    out = {}
    for requirement_id in run.requirement_ids:
        def rows(model):
            return [row(x) for x in session.scalars(select(model).where(model.run_id == rid, model.requirement_id == requirement_id)).all()]
        out[requirement_id] = {
            "persona_responses": rows(PersonaResponse), "department_memos": rows(DepartmentMemo),
            "research": rows(ResearchRequest), "ratings": rows(CriterionRating), "synthesis": rows(Synthesis),
            "votes": rows(Vote), "recommendation": rows(Recommendation),
        }
    return {"run": row(run), "requirements": out}


@router.get("/{run_id}/llm-calls", summary="Every model call of the run: model, prompt version, input record IDs, tokens",
            response_model=list[LLMCallOut])
def llm_calls(run_id: str, include_payloads: bool = False, requirement_id: str | None = None, agent_id: str | None = None,
              session: Session = Depends(get_session)):
    query = select(LLMCall).where(LLMCall.run_id == _uuid(run_id))
    if requirement_id:
        # Persona calls cover all cases of a run at once and carry no requirement_id; include them.
        query = query.where((LLMCall.requirement_id == requirement_id) | LLMCall.requirement_id.is_(None))
    if agent_id:
        query = query.where(LLMCall.agent_id == agent_id)
    calls = session.scalars(query.order_by(LLMCall.id)).all()
    exclude = set() if include_payloads else {"request", "response"}
    return [row(c, exclude=exclude) for c in calls]
