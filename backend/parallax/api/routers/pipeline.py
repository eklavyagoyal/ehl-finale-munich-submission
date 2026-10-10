"""The PM's path as data: sources -> processing -> signals -> expert pipeline -> decision.

`GET /api/pipeline` powers the start page (one card per stage, counts, status, next action).
`GET /api/signals` turns theme counts into what a PM reads first: pain points, strengths, requests.
"""

from collections import Counter
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from parallax.config import get_settings
from parallax.db import get_session
from parallax.models import Claim, IngestRun, Record, Requirement, SimRun, Source, Theme
from parallax.themes import latest_snapshot_id

router = APIRouter(prefix="/api", tags=["pipeline"])

STREAM_LABELS = {"bmw": "BMW", "social": "Social media", "competitors": "Competitors"}


def classify(theme: Theme) -> str:
    total = theme.mention_review_count or 0
    if not total:
        return "none"
    pain, praise, requests = theme.pain_review_count / total, theme.praise_review_count / total, theme.request_review_count / total
    if pain >= 0.4:
        return "pain"
    if requests >= 0.3:
        return "request"
    if praise >= 0.6 and pain < 0.15:
        return "strength"
    return "mixed"


def _signal(theme: Theme, kind: str, texts: dict[str, str], drafted: set) -> dict:
    return {
        "theme_id": theme.id, "feature_key": theme.feature_key, "label": theme.label, "area": theme.area,
        "market": theme.market, "kind": kind, "reviews": theme.mention_review_count,
        "direct_reviews": theme.direct_review_count, "pain": theme.pain_review_count,
        "requests": theme.request_review_count, "praise": theme.praise_review_count,
        "competitor_reviews": theme.competitor_review_count, "channels": theme.channels,
        "demand_0_5": theme.demand_score, "impact_0_5": theme.impact_score,
        "sample_quotes": [{"record_id": rid, "text": texts[rid][:280]} for rid in theme.record_ids[:2] if rid in texts],
        "has_requirement": (theme.feature_key, theme.market) in drafted,
    }


@router.get("/signals", summary="What customers say, ranked: pain points, strengths, requests (from deterministic theme counts)")
def signals(market: str | None = Query(None, description="US, EU, CN or omit for all markets pooled"),
            kind: Literal["pain", "strength", "request", "mixed", "all"] = "all", limit: int = Query(15, le=100),
            session: Session = Depends(get_session, scope="function")):
    snapshot = latest_snapshot_id(session, get_settings().target_model)
    if snapshot is None:
        return {"snapshot_id": None, "market": market, "items": []}
    query = select(Theme).where(Theme.snapshot_id == snapshot, Theme.mention_review_count > 0)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    themes = [(t, classify(t)) for t in session.scalars(query)]
    if kind != "all":
        themes = [(t, k) for t, k in themes if k == kind]
    order = {"pain": lambda t: (t.pain_review_count, t.impact_score or 0), "strength": lambda t: (t.praise_review_count,),
             "request": lambda t: (t.request_review_count,), "mixed": lambda t: (t.mention_review_count,),
             "all": lambda t: (t.demand_score, t.pain_review_count, t.mention_review_count)}[kind]
    themes.sort(key=lambda pair: order(pair[0]), reverse=True)
    themes = themes[:limit]
    ids = {rid for t, _ in themes for rid in t.record_ids[:2]}
    texts = {r.record_id: (r.translation_en or r.text_original or "")
             for r in session.scalars(select(Record).where(Record.record_id.in_(list(ids))))} if ids else {}
    drafted = {(r.feature_key, r.market) for r in session.scalars(select(Requirement))}
    return {"snapshot_id": str(snapshot), "market": market,
            "basis": "Distinct collected reviews per feature; pain = defects and hard-to-use reports; not customer prevalence.",
            "items": [_signal(t, k, texts, drafted) for t, k in themes]}


@router.get("/pipeline", summary="Start page: one card per stage with counts, status and the next action")
def pipeline(session: Session = Depends(get_session, scope="function")):
    settings = get_settings()
    # 1 sources
    by_stream = dict(session.execute(
        select(Source.stream, func.count(Record.record_id)).join(Record, Record.source_id == Source.source_id)
        .where(Record.superseded_by.is_(None)).group_by(Source.stream)).all())
    source_count = session.scalar(select(func.count()).select_from(Source)) or 0
    pending_sources = session.scalar(select(func.count()).select_from(Source).where(Source.review_status == "pending")) or 0
    last_ingest = session.scalars(select(IngestRun).order_by(IngestRun.created_at.desc()).limit(1)).first()
    # 2 processing
    claim_status = dict(session.execute(select(Claim.review_status, func.count()).group_by(Claim.review_status)).all())
    producers = Counter()
    for producer, derived in session.execute(select(Claim.producer, Claim.derived)):
        producers["BMW labels" if derived else (producer or {}).get("method", "unknown")] += 1
    feedback = session.scalar(select(func.count()).select_from(Record).where(Record.record_kind == "feedback",
                                                                             Record.superseded_by.is_(None))) or 0
    with_claims = session.scalar(select(func.count(func.distinct(Claim.record_id)))) or 0
    # 3 signals
    snapshot = latest_snapshot_id(session, settings.target_model)
    pooled = list(session.scalars(select(Theme).where(Theme.snapshot_id == snapshot, Theme.market.is_(None),
                                                      Theme.mention_review_count > 0))) if snapshot else []
    kinds = Counter(classify(t) for t in pooled)
    top = lambda k, key: [t.label for t in sorted((t for t in pooled if classify(t) == k), key=key, reverse=True)[:3]]
    # 4 experts, 5 decision
    req_status = dict(session.execute(select(Requirement.status, func.count()).group_by(Requirement.status)).all())
    runs = dict(session.execute(select(SimRun.status, func.count()).where(SimRun.kind != "validation")
                                .group_by(SimRun.status)).all())
    requirements = sum(req_status.values())

    def status(done: bool, started: bool) -> str:
        return "done" if done else ("in_progress" if started else "todo")

    stages = [
        {"key": "sources", "title": "Sources", "question": "Where does the data come from?",
         "status": status(source_count > 0 and pending_sources == 0, source_count > 0),
         "counts": {"sources": source_count, "records": sum(by_stream.values()), "pending_review": pending_sources,
                    "by_stream": [{"stream": s, "label": STREAM_LABELS.get(s, s), "records": n} for s, n in by_stream.items()]},
         "last_import": last_ingest.created_at.isoformat() if last_ingest else None},
        {"key": "processing", "title": "Processing", "question": "What did we extract from it?",
         "status": status(bool(claim_status.get("accepted")) and not claim_status.get("pending"), bool(claim_status)),
         "counts": {"feedback_records": feedback, "records_with_claims": with_claims,
                    "records_without_claims": max(0, feedback - with_claims), "claims_by_status": claim_status,
                    "claims_by_producer": dict(producers)}},
        {"key": "signals", "title": "Signals", "question": "What do customers tell us?",
         "status": status(bool(pooled), bool(snapshot)),
         "counts": {"features_with_evidence": len(pooled), "by_kind": dict(kinds)},
         "top_pains": top("pain", lambda t: t.pain_review_count), "top_strengths": top("strength", lambda t: t.praise_review_count),
         "top_requests": top("request", lambda t: t.request_review_count)},
        {"key": "experts", "title": "Expert pipeline", "question": "What do owners and departments think?",
         "status": status(runs.get("completed", 0) > 0 and not runs.get("running"), requirements > 0),
         "counts": {"requirements": requirements, "runs_by_status": runs}},
        {"key": "decision", "title": "Decision", "question": "What goes into the successor?",
         "status": status(requirements > 0 and not req_status.get("in_review") and not req_status.get("proposed"),
                          any(req_status.get(s) for s in ("approved", "rejected", "deferred", "challenged"))),
         "counts": {"by_status": req_status}},
    ]
    if not source_count:
        nxt = {"stage": "sources", "label": "Import evidence (python -m parallax.cli push-research)"}
    elif pending_sources:
        nxt = {"stage": "sources", "label": f"Review {pending_sources} pending source(s)"}
    elif not pooled:
        nxt = {"stage": "signals", "label": "Build signals (POST /api/themes/build)", "action": "POST /api/themes/build"}
    elif not requirements:
        nxt = {"stage": "signals", "label": "Pick signals and draft requirements", "action": "POST /api/requirements/draft"}
    elif req_status.get("proposed") or req_status.get("challenged"):
        nxt = {"stage": "experts", "label": "Run the expert pipeline on proposed requirements", "action": "POST /api/simulations"}
    elif req_status.get("in_review"):
        nxt = {"stage": "decision", "label": f"Decide on {req_status['in_review']} requirement(s)"}
    else:
        nxt = {"stage": "signals", "label": "Draft more requirements or revisit signals"}
    return {"target_model": settings.target_model, "stages": stages, "next_action": nxt}
