"""Triage of online reviews: vehicle, engine type, author (owner?) and relevance, like BMW's feedback columns."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from parallax import triage
from parallax.api.common import actor, row
from parallax.db import get_session
from parallax.orchestrator import launch
from parallax.scope import normalize_vehicle

router = APIRouter(prefix="/api/triage", tags=["triage"])


class TriageIn(BaseModel):
    limit: int | None = Field(None, ge=1, description="Optional cap on records")
    workers: int = Field(32, ge=1, le=64, description="Parallel model calls")
    record_ids: list[str] | None = Field(None, description="Triage exactly these records")
    retriage: bool = Field(False, description="Also redo records already triaged with the current prompt version")


@router.post("/run", summary="Triage online reviews (background run; poll /api/simulations/{id})")
def run(body: TriageIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    sim = triage.start(session, who, body.model_dump())
    session.commit()
    launch(sim.id)
    return row(sim)


@router.get("/summary", summary="Online data after triage: overall and for the records collected under the vehicle")
def summary(vehicle: str | None = Query(None, description="e.g. G60; default: the active vehicle"),
            session: Session = Depends(get_session, scope="function")):
    return triage.summary(session, normalize_vehicle(vehicle))


@router.get("/sample", summary="Spot-check sample of triaged reviews (text next to the labels)")
def sample(n: int = Query(30, ge=1, le=200), seed: int = 1,
           only: str | None = Query(None, description="not_relevant | owner | omit for all"),
           session: Session = Depends(get_session, scope="function")):
    return {"note": triage.VALIDATION_NOTE, "items": triage.sample(session, n, seed, only)}
