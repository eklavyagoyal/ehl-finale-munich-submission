"""Labeling: claims for unlabeled feedback (social, competitor, unclassified BMW) with BMW's vocabulary."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from parallax import labeling
from parallax.api.common import actor, row
from parallax.db import get_session
from parallax.orchestrator import launch

router = APIRouter(prefix="/api/labeling", tags=["labeling"])


class CalibrateIn(BaseModel):
    n: int = Field(300, ge=20, le=2000, description="BMW feedback records to label blind")
    workers: int = Field(16, ge=1, le=64)


@router.post("/calibrate", summary="Label BMW feedback blind and measure agreement with BMW's VFC labels (background run)")
def calibrate(body: CalibrateIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    run = labeling.start(session, "calibration", who, body.model_dump())
    session.commit()
    launch(run.id)
    return row(run)


class LabelIn(BaseModel):
    scope: Literal["social", "competitors", "bmw_unclassified", "all"] = "social"
    limit: int | None = Field(None, ge=1, description="Optional cap on records")
    workers: int = Field(24, ge=1, le=64, description="Parallel model calls")
    record_ids: list[str] | None = Field(None, description="Label exactly these records")
    retry_run_id: str | None = Field(None, description="Retry the batches of this earlier labeling run that stored no claims")


@router.post("/run", summary="Label unlabeled feedback into claims (pending review); poll /api/simulations/{id}")
def run_labeling(body: LabelIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    run = labeling.start(session, "labeling", who, body.model_dump())
    session.commit()
    launch(run.id)
    return row(run)
