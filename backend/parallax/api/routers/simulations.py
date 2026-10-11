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
    persona_scope: Literal["market", "all"] = Field("market", description="market = owners of the case's market answer "
                                                    "(default, like the regional sales departments); all = every owner")


@router.post("", summary="Start a Parallax run (market twin || company twin -> research -> scoring -> synthesis -> vote)",
             response_model=RunOut)
def start(body: SimulationIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    try:
        run = create_run(session, requirement_ids=body.requirement_ids, actor_id=who, challenge=body.challenge,
                         options={**({"persona_engine": body.persona_engine} if body.persona_engine else {}),
                                  "persona_scope": body.persona_scope})
    except ValueError as error:
        raise HTTPException(400, str(error))
    session.commit()
    launch(run.id)
    return row(run)


@router.get("", response_model=list[RunOut])
def list_runs(kind: str | None = None, limit: int = Query(50, le=200),
              include_failed: bool = Query(False, description="Also list failed and interrupted runs (kept in the audit trail)"),
              session: Session = Depends(get_session, scope="function")):
    query = select(SimRun)
    if not include_failed:
        query = query.where(SimRun.status.not_in(("failed", "interrupted")))
    if kind:
        query = query.where(SimRun.kind == kind)
    return [row(r) for r in session.scalars(query.order_by(SimRun.created_at.desc()).limit(limit)).all()]


@router.get("/{run_id}", summary="Run status, progress and step trace (poll this)", response_model=RunDetailOut)
def get_run(run_id: str, session: Session = Depends(get_session, scope="function")):
    run = session.get(SimRun, _uuid(run_id))
    if run is None:
        raise not_found("run", run_id)
    steps = session.scalars(select(SimStep).where(SimStep.run_id == run.id).order_by(SimStep.id)).all()
    return {"run": row(run), "steps": [row(s) for s in steps]}


@router.get("/{run_id}/results", summary="All agent outputs of a run, grouped by requirement")
def results(run_id: str, session: Session = Depends(get_session, scope="function")):
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
              session: Session = Depends(get_session, scope="function")):
    query = select(LLMCall).where(LLMCall.run_id == _uuid(run_id))
    if requirement_id:
        # Persona calls cover all cases of a run at once and carry no requirement_id; include them.
        query = query.where((LLMCall.requirement_id == requirement_id) | LLMCall.requirement_id.is_(None))
    if agent_id:
        query = query.where(LLMCall.agent_id == agent_id)
    calls = session.scalars(query.order_by(LLMCall.id)).all()
    exclude = set() if include_payloads else {"request", "response"}
    return [row(c, exclude=exclude) for c in calls]


SUMMARY_FIELDS = ("summary", "headline", "main_argument", "reaction", "rationale", "counter_position", "answer_summary",
                  "customer_view", "verdict", "recommendation", "vote")


def _call_summary(call: LLMCall) -> str | None:
    """One line for the side panel: the most telling field of the answer, else its first sentence."""
    response = call.response or {}
    parsed = response.get("parsed")
    if isinstance(parsed, dict):
        for field in SUMMARY_FIELDS:
            value = parsed.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()[:280]
        for value in parsed.values():  # e.g. {"reactions": [...]} or {"items": [...]}
            if isinstance(value, list) and value and isinstance(value[0], dict):
                first = next((value[0][f] for f in SUMMARY_FIELDS if isinstance(value[0].get(f), str)), None)
                if first:
                    return f"{len(value)} items · first: {first.strip()[:240]}"
    text = response.get("content")
    if isinstance(text, str) and text.strip():
        return text.strip().split("\n")[0][:280]
    return None


@router.get("/llm-calls/{call_id}", summary="One model call opened up: what was sent, what came back, a one-line summary")
def llm_call(call_id: int, session: Session = Depends(get_session, scope="function")):
    from parallax.models import Agent

    call = session.get(LLMCall, call_id)
    if call is None:
        raise not_found("llm call", str(call_id))
    agent = session.get(Agent, call.agent_id) if call.agent_id else None
    request = call.request or {}
    if "messages" in request:  # TinyTroupe: the persona definition is the first message, the stimulus the last
        messages = request["messages"]
        prompt = {"system": next((m["content"] for m in messages if m.get("role") == "system"), None),
                  "user": "\n\n".join(m["content"] for m in messages if m.get("role") != "system")[-6000:]}
    else:
        prompt = {"system": request.get("system"), "user": request.get("user")}
    response = call.response or {}
    return {
        "id": call.id, "run_id": str(call.run_id) if call.run_id else None, "agent_id": call.agent_id,
        "agent_name": agent.display_name if agent else call.agent_id, "requirement_id": call.requirement_id,
        "purpose": call.purpose, "model": call.model, "prompt_version": call.prompt_version, "status": call.status,
        "error": call.error, "input_tokens": call.input_tokens, "output_tokens": call.output_tokens,
        "latency_ms": call.latency_ms, "created_at": call.created_at.isoformat(),
        "summary": _call_summary(call),
        "prompt": {k: (v[:12000] if isinstance(v, str) else v) for k, v in prompt.items()},
        "response": response.get("parsed") if response.get("parsed") is not None else response.get("content"),
        "citations": response.get("citations") or [],
        "input_record_ids": call.input_record_ids,
        "note": None if response.get("parsed") is not None or response.get("content") else
                "The answer text of this call was not stored (persona calls of runs before this feature).",
    }


@router.get("/{run_id}/conversation",
            summary="Who was asked what and how they answered: owners by market, departments, research, challenger, judges")
def conversation(run_id: str, session: Session = Depends(get_session, scope="function")):
    from parallax.models import Agent, Requirement

    rid = _uuid(run_id)
    run = session.get(SimRun, rid)
    if run is None:
        raise not_found("run", run_id)
    agents = {a.id: a for a in session.scalars(select(Agent))}
    titles = {r.id: r.title for r in session.scalars(select(Requirement).where(Requirement.id.in_(run.requirement_ids or [])))}
    steps = session.scalars(select(SimStep).where(SimStep.run_id == rid).order_by(SimStep.id)).all()
    twin = next((s for s in steps if s.stage == "market_twin"), None)

    owners: dict[str, dict] = {}
    for p in session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == rid).order_by(PersonaResponse.id)):
        agent = agents.get(p.agent_id)
        spec = agent.spec if agent else {}
        reaction, _, transcript = p.response_text.partition("\n[raw] ")
        owner = owners.setdefault(p.agent_id, {
            "agent_id": p.agent_id, "name": spec.get("persona", {}).get("name"), "display_name": agent.display_name if agent else p.agent_id,
            "market": agent.market if agent else None, "country": agent.country if agent else None,
            "vehicle": spec.get("vehicle_label"), "powertrain": spec.get("powertrain"), "segment": spec.get("segment"),
            "environment": spec.get("environment", {}), "validation_status": agent.validation_status if agent else None,
            "engine": p.engine, "grounding_records": len(p.grounding_record_ids or []), "transcript": transcript or None,
            "answers": [],
        })
        owner["answers"].append({
            "requirement_id": p.requirement_id, "requirement_title": titles.get(p.requirement_id), "reaction": reaction,
            "stance": p.stance, "importance_0_5": p.importance_0_5, "class_fit_0_5": p.market_fit_0_5,
            "concerns": p.concerns, "would_need_to_know": p.info_requests,
        })
    by_market: dict[str, list] = {}
    for owner in owners.values():
        by_market.setdefault(owner["market"] or "other", []).append(owner)

    departments: dict[str, dict] = {}
    for m in session.scalars(select(DepartmentMemo).where(DepartmentMemo.run_id == rid).order_by(DepartmentMemo.id)):
        agent = agents.get(m.agent_id)
        dept = departments.setdefault(m.agent_id, {
            "agent_id": m.agent_id, "display_name": agent.display_name if agent else m.agent_id,
            "market": agent.market if agent else None, "role": (agent.spec.get("role", {}) if agent else {}).get("title"),
            "answers": [],
        })
        dept["answers"].append({"requirement_id": m.requirement_id, "requirement_title": titles.get(m.requirement_id),
                                "question": f"Review requirement {m.requirement_id} from the {dept['display_name']} perspective",
                                "stance": m.stance, **{k: m.memo.get(k) for k in ("summary", "effort_band", "risks", "conditions",
                                                                                 "criterion_ratings", "info_requests")}})

    per_requirement = {}
    for requirement_id in run.requirement_ids or []:
        rec = session.scalars(select(Recommendation).where(Recommendation.run_id == rid,
                                                           Recommendation.requirement_id == requirement_id)).first()
        syn = session.scalars(select(Synthesis).where(Synthesis.run_id == rid, Synthesis.requirement_id == requirement_id)).first()
        per_requirement[requirement_id] = {
            "title": titles.get(requirement_id),
            "research": [{"requested_by": r.requested_by, "question": r.question, "verdict": r.verdict,
                          "answer": next((f.get("answer_summary") for f in r.findings if "answer_summary" in f), None),
                          "sources": r.sources[:5]}
                         for r in session.scalars(select(ResearchRequest).where(ResearchRequest.run_id == rid,
                                                                                ResearchRequest.requirement_id == requirement_id))],
            "synthesis_headline": syn.content.get("headline") if syn else None,
            "challenger": rec.challenge if rec else None,
            "judges": [{"agent_id": v.agent_id, "model": v.model, "vote": v.vote, "rationale": v.rationale}
                       for v in session.scalars(select(Vote).where(Vote.run_id == rid, Vote.requirement_id == requirement_id))],
            "recommendation": rec.recommendation if rec else None,
        }
    return {
        "run": {"id": str(run.id), "status": run.status, "stage": (run.progress or {}).get("stage"),
                "challenge_question": run.challenge_question, "engine": (run.config or {}).get("persona_engine")},
        "order": ["owners + departments (parallel)", "research + verifier", "scoring", "synthesis", "challenger", "judges", "PM"],
        "question_to_owners": (twin.detail or {}).get("question") if twin else None,
        "owners_by_market": by_market,
        "departments": list(departments.values()),
        "requirements": per_requirement,
    }
