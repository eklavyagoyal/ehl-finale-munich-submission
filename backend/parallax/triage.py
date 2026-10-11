"""Triage: the columns BMW's own feedback export has per row, filled in for online reviews.

BMW feedback comes from owners through BMW channels and carries, per row: vehicle (derivate), engine type,
country, feedback type and topic. Online reviews only carry what the scraper knew (the video or search they
were collected under). Triage adds, per online review:

  vehicle   is it about the target vehicle, an older generation, another BMW, a competitor, or unclear
  engine    ICE / BEV / PHEV / unclear (BMW's "Engine Type")
  author    owner / not owner (prospect, reviewer, fan, dealer) / unclear
  relevant  does it say something about the car a product manager can use

There is no ground truth for author and relevance (BMW's data has no such columns), so triage is marked
unvalidated; a spot-check sample is part of the API. Feature and feedback type stay with the labeler.
"""

import random
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import session_scope
from parallax.llm.client import LLMClient, get_llm
from parallax.llm.gate import check_records
from parallax.llm.prompts import SAFETY
from parallax.models import Entity, Record, RecordTriage, SimRun, Source

PROMPT_VERSION = "triage-v1"
BATCH = 40
MIN_CHARS = 15
ONLINE_STREAMS = ("social", "competitors")
VALIDATION_NOTE = ("Unvalidated: BMW's data has no owner or relevance columns to compare against. "
                   "Check the spot-check sample before excluding anything.")

Vehicle = Literal["target", "older_generation", "other_bmw", "competitor", "unclear"]
Engine = Literal["ice", "bev", "phev", "unclear"]
Author = Literal["owner", "not_owner", "unclear"]


class TriageItem(BaseModel):
    record_id: str
    vehicle: Vehicle = Field(description="Which car the text is about (see the definitions).")
    engine: Engine = Field(description="Powertrain the text is about, only if stated or obvious (i5 = bev, 530e/550e = phev).")
    author: Author = Field(description="owner = drives or owns this car (or did until recently); not_owner = prospect, "
                                       "reviewer, journalist, fan, dealer; unclear if not stated.")
    relevant: bool = Field(description="True if the text says something concrete about the car (features, quality, "
                                       "driving, comfort, software, price-value) that a product manager can use.")
    reason: str = Field(description="At most 12 words, English.")


class TriageBatch(BaseModel):
    items: list[TriageItem]


SYSTEM = """\
You triage online reviews and comments for BMW product planning, the way BMW's own feedback export is
organised per row (vehicle, engine type, author, relevance). The target vehicle is {target}.
vehicle: target = the text is about the target vehicle ({target_names}); older_generation = an earlier
generation of the same model; other_bmw = another BMW model; competitor = a non-BMW car; unclear = cannot tell
(e.g. a generic comment under a video about the target vehicle).
relevant = false for spam, jokes, emojis, greetings, app-login or account problems unrelated to the car,
dealer small talk, politics, and anything without content about the car.
Judge only from the text and its collection context. Do not guess ownership: "I love mine" = owner,
"I want one" = not_owner, no hint = unclear.
{safety}"""

TARGET_NAMES = {"bmw:G60": "BMW 5 Series sedan from 2023/2024 on, G60, incl. i5, 520i/530i/540i, 530e/550e, M60"}


def _collected_under(record: Record, entities: dict[str, str]) -> str:
    names = [entities.get(s, s) for s in record.subject_ids or []]
    return ", ".join(names) or "no vehicle"


def candidates(session: Session, *, limit: int | None = None, record_ids: list[str] | None = None,
               retriage: bool = False) -> tuple[list[str], list[str]]:
    """(ids for the model, ids too short for the model). Online feedback only; BMW feedback is owner feedback by source."""
    query = (select(Record.record_id, Record.text_original).join(Source, Source.source_id == Record.source_id)
             .where(Record.record_kind == "feedback", Record.superseded_by.is_(None), Source.stream.in_(ONLINE_STREAMS)))
    if record_ids:
        query = query.where(Record.record_id.in_(record_ids))
    done = set() if retriage or record_ids else {
        rid for rid, in session.execute(select(RecordTriage.record_id).where(RecordTriage.prompt_version == PROMPT_VERSION))}
    model_ids, short = [], []
    for record_id, text in session.execute(query):
        if record_id in done:
            continue
        (short if len((text or "").strip()) < MIN_CHARS else model_ids).append(record_id)
    model_ids.sort()
    random.Random(7).shuffle(model_ids)  # spread batches over sources
    allowed = set(check_records(session, model_ids).allowed)
    model_ids = [rid for rid in model_ids if rid in allowed]
    return (model_ids[:limit] if limit else model_ids), short


def _row(record_id: str, target: str, item: TriageItem | None, run_id: uuid.UUID, model: str) -> dict:
    if item is None:
        return {"record_id": record_id, "target_model": target, "vehicle": "unclear", "engine": "unclear",
                "author": "unclear", "relevant": False, "reason": f"under {MIN_CHARS} characters", "method": "rule",
                "model": None, "prompt_version": PROMPT_VERSION, "run_id": run_id}
    return {"record_id": record_id, "target_model": target, "vehicle": item.vehicle, "engine": item.engine,
            "author": item.author, "relevant": item.relevant, "reason": item.reason.replace("\x00", "")[:200],
            "method": "llm", "model": model, "prompt_version": PROMPT_VERSION, "run_id": run_id}


def _store(rows: list[dict]) -> None:
    if not rows:
        return
    with session_scope() as session:
        statement = insert(RecordTriage).values(rows)
        session.execute(statement.on_conflict_do_update(
            index_elements=[RecordTriage.record_id],
            set_={c: statement.excluded[c] for c in ("target_model", "vehicle", "engine", "author", "relevant", "reason",
                                                     "method", "model", "prompt_version", "run_id")} | {"created_at": func.now()}))


def _triage_batch(llm: LLMClient, ids: list[str], target: str, run_id: uuid.UUID) -> Counter:
    settings = get_settings()
    with session_scope() as session:
        records = list(session.scalars(select(Record).where(Record.record_id.in_(ids))))
        sources = {s.source_id: s.channel for s in session.scalars(select(Source).where(
            Source.source_id.in_({r.source_id for r in records})))}
        entities = {e.entity_id: e.label for e in session.scalars(select(Entity))}
        session.expunge_all()
    lines = ["Records:"]
    for r in records:
        text = (r.text_original or "").replace("\n", " ")[:700]
        lines.append(f"- record_id={r.record_id} | channel={sources.get(r.source_id)} | collected under: "
                     f"{_collected_under(r, entities)} | text: {text}")

    def mock(rng):
        return TriageBatch(items=[TriageItem(record_id=r.record_id, vehicle=rng.choice(["target", "unclear", "competitor"]),
                                             engine=rng.choice(["ice", "bev", "unclear"]),
                                             author=rng.choice(["owner", "not_owner", "unclear"]),
                                             relevant=rng.random() > 0.3, reason="[mock]") for r in records])

    out = llm.structured(TriageBatch, system=SYSTEM.format(target=target, target_names=TARGET_NAMES.get(target, target),
                                                           safety=SAFETY),
                         user="\n".join(lines), model=settings.model_fast, purpose="triage", prompt_version=PROMPT_VERSION,
                         agent_id="agent:triage", run_id=run_id, input_record_ids=ids, mock=mock, reasoning_effort="low")
    by_id = {i.record_id: i for i in out.items}
    rows = [_row(r.record_id, target, by_id[r.record_id], run_id, settings.model_fast) for r in records if r.record_id in by_id]
    _store(rows)
    return Counter(triaged=len(rows), missing=len(records) - len(rows))


def start(session: Session, actor_id: str, options: dict) -> SimRun:
    run = SimRun(kind="triage", status="queued", requirement_ids=[], requested_by=actor_id,
                 config={"options": options, "model": get_settings().model_fast, "prompt_version": PROMPT_VERSION},
                 progress={"stage": "queued"})
    session.add(run)
    session.flush()
    record_event(session, category="ai", actor_id=actor_id, action="triage.start", entity_type="sim_run",
                 entity_id=str(run.id), run_id=run.id, after=options)
    return run


def execute(run_id: uuid.UUID) -> None:
    llm = get_llm()
    target = get_settings().target_model
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.started_at = "running", datetime.now(timezone.utc)
        options, actor = run.config.get("options", {}), run.requested_by
        ids, short = candidates(session, limit=options.get("limit"), record_ids=options.get("record_ids"),
                                retriage=bool(options.get("retriage")))
    _store([_row(rid, target, None, run_id, "") for rid in short])
    batches = [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]
    llm.set_budget(run_id, len(batches) + 10)
    totals, failures = Counter(short_rule=len(short)), 0
    workers = max(1, min(64, int(options.get("workers", 32))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_triage_batch, llm, batch, target, run_id) for batch in batches]
        for done, future in enumerate(as_completed(futures), 1):
            try:
                totals.update(future.result())
            except Exception:
                failures += 1
            if done % 10 == 0 or done == len(futures):
                with session_scope() as session:
                    session.get(SimRun, run_id).progress = {"stage": "triage", "batches_done": done,
                                                            "batches_total": len(futures), "failed_batches": failures}
    status = "partial" if failures else "completed"
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.finished_at = status, datetime.now(timezone.utc)
        run.progress = {"stage": "done", "result": {**totals, "batches": len(batches), "failed_batches": failures}}
        record_event(session, category="ai", actor_id=actor, action=f"triage.{status}", entity_type="sim_run",
                     entity_id=str(run_id), run_id=run_id, after=run.progress["result"])


def summary(session: Session, target_model: str) -> dict:
    """What the online data is after triage, overall and for the records collected under the vehicle."""
    from parallax.scope import VehicleScope

    scope = VehicleScope(session, target_model)
    online = Counter()
    for subjects, stream, n in session.execute(
            select(Record.subject_ids, Source.stream, func.count()).join(Source, Source.source_id == Record.source_id)
            .where(Record.record_kind == "feedback", Record.superseded_by.is_(None), Source.stream.in_(ONLINE_STREAMS))
            .group_by(Record.subject_ids, Source.stream)):
        online["all"] += n
        online[scope.of(subjects)] += n
    rows = session.execute(select(Record.subject_ids, RecordTriage.vehicle, RecordTriage.engine, RecordTriage.author,
                                  RecordTriage.relevant, RecordTriage.method)
                           .join(RecordTriage, RecordTriage.record_id == Record.record_id)).all()
    overall = {"vehicle": Counter(), "engine": Counter(), "author": Counter(), "relevant": Counter(), "method": Counter()}
    vehicle_scope = {"vehicle": Counter(), "engine": Counter(), "author": Counter(), "relevant": Counter()}
    usable = owners = 0
    for subjects, vehicle, engine, author, relevant, method in rows:
        for key, value in (("vehicle", vehicle), ("engine", engine), ("author", author), ("relevant", relevant)):
            overall[key][str(value).lower()] += 1
        overall["method"][method] += 1
        if scope.of(subjects) == "target":
            for key, value in (("vehicle", vehicle), ("engine", engine), ("author", author), ("relevant", relevant)):
                vehicle_scope[key][str(value).lower()] += 1
            if relevant and vehicle in ("target", "unclear"):
                usable += 1
                owners += author == "owner"
    last = session.scalars(select(SimRun).where(SimRun.kind == "triage").order_by(SimRun.created_at.desc()).limit(1)).first()
    return {
        "target_model": target_model, "validated": False, "note": VALIDATION_NOTE, "prompt_version": PROMPT_VERSION,
        "online_records": online["all"], "triaged": len(rows),
        "overall": {k: dict(v) for k, v in overall.items()},
        "vehicle_scope": {"collected_under_vehicle": online["target"], **{k: dict(v) for k, v in vehicle_scope.items()},
                          "usable": usable, "usable_owners": owners,
                          "usable_rule": "relevant and about the vehicle (or unclear, collected under it)"},
        "bmw_feedback": "Owner feedback through BMW channels: vehicle, engine type and country come with every row; not triaged.",
        "last_run": {"id": str(last.id), "status": last.status} if last else None,
    }


def sample(session: Session, n: int, seed: int, only: str | None = None) -> list[dict]:
    query = (select(RecordTriage, Record.text_original, Source.channel).join(Record, Record.record_id == RecordTriage.record_id)
             .join(Source, Source.source_id == Record.source_id).where(RecordTriage.method == "llm"))
    if only == "not_relevant":
        query = query.where(RecordTriage.relevant.is_(False))
    elif only == "owner":
        query = query.where(RecordTriage.author == "owner")
    rows = session.execute(query.order_by(func.md5(func.concat(RecordTriage.record_id, str(seed)))).limit(n)).all()
    return [{"record_id": t.record_id, "channel": channel, "text": (text or "")[:400], "vehicle": t.vehicle, "engine": t.engine,
             "author": t.author, "relevant": t.relevant, "reason": t.reason} for t, text, channel in rows]
