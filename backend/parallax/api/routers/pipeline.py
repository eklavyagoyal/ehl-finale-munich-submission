"""The PM's path as data: sources -> processing -> signals -> expert pipeline -> decision.

`GET /api/pipeline` powers the start page (one card per stage, counts, status, next action).
`GET /api/signals` turns theme counts into what a PM reads first: pain points, strengths, requests.
"""

from collections import Counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from parallax.api.common import actor
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from parallax.config import get_settings
from parallax.db import get_session
from parallax.models import Claim, Finding, IngestRun, Record, Requirement, SimRun, Source, Theme
from parallax.policy import active_policy
from parallax.scope import SCOPE_LABELS, SCOPES, VehicleScope
from parallax.signals import CHANNEL_LABELS, classify, explain_kind, latest_findings, need_share, quadrant, ranked_themes
from parallax.themes import latest_snapshot_id

router = APIRouter(prefix="/api", tags=["pipeline"])

STREAM_LABELS = {"bmw": "BMW", "social": "Social media", "competitors": "Competitors"}
EXPERT_RUN_KINDS = ("simulation", "followup")


FINDING_KINDS = {"pain": {"pain"}, "request": {"request"}, "strength": {"praise"}}


def _finding(f: Finding, signal_kind: str | None = None) -> dict:
    matches = signal_kind not in FINDING_KINDS or f.kind in FINDING_KINDS[signal_kind]
    return {"id": f.id, "title": f.title, "description": f.description, "kind": f.kind, "reviews": f.review_count,
            "share_of_theme": f.share_of_theme, "quotes": f.quotes, "record_ids": f.record_ids[:200],
            "matches_signal": matches}


def _ordered_findings(findings: list[Finding], kind: str) -> list[dict]:
    """Findings of the signal's own kind first (a pain card leads with pains, not with praise), then by size."""
    rows = [_finding(f, kind) for f in findings]
    return sorted(rows, key=lambda r: (not r["matches_signal"], -r["reviews"]))


def _signal(theme: Theme, kind: str, texts: dict[str, str], drafted: set, findings: list[Finding] | None,
            thresholds: dict) -> dict:
    ordered = _ordered_findings(findings or [], kind)
    return {
        "theme_id": theme.id, "feature_key": theme.feature_key, "label": theme.label, "area": theme.area,
        "market": theme.market, "kind": kind, "reviews": theme.mention_review_count,
        "direct_reviews": theme.direct_review_count, "pain": theme.pain_review_count,
        "requests": theme.request_review_count, "praise": theme.praise_review_count,
        "need": theme.need_review_count, "need_share": need_share(theme), "quadrant": quadrant(theme, thresholds),
        "competitor_reviews": theme.competitor_review_count, "brand_wide_reviews": theme.brand_review_count,
        "channels": theme.channels,
        "demand_0_5": theme.demand_score, "impact_0_5": theme.impact_score,
        "sample_quotes": [{"record_id": rid, "text": texts[rid][:280]} for rid in theme.record_ids[:2] if rid in texts],
        "has_requirement": (theme.feature_key, theme.market) in drafted,
        "condensed": bool(findings),
        "findings": ordered,
        "other_kind_findings": sum(not f["matches_signal"] for f in ordered),
    }


def _thresholds(session: Session) -> dict:
    return active_policy(session).document["parallax"]["signal_map"]


@router.get("/signals", summary="What customers say, ranked: pain points, strengths, requests (from deterministic theme counts)")
def signals(market: str | None = Query(None, description="US, EU, CN or omit for all markets pooled"),
            kind: Literal["pain", "strength", "request", "mixed", "all"] = "all", limit: int = Query(15, le=100),
            session: Session = Depends(get_session, scope="function")):
    snapshot = latest_snapshot_id(session, get_settings().target_model)
    if snapshot is None:
        return {"snapshot_id": None, "market": market, "items": []}
    themes = ranked_themes(session, market, kind, limit)
    ids = {rid for t, _ in themes for rid in t.record_ids[:2]}
    texts = {r.record_id: (r.translation_en or r.text_original or "")
             for r in session.scalars(select(Record).where(Record.record_id.in_(list(ids))))} if ids else {}
    drafted = {(r.feature_key, r.market) for r in session.scalars(select(Requirement))}
    findings = latest_findings(session, market, [t.feature_key for t, _ in themes])
    thresholds = _thresholds(session)
    return {"snapshot_id": str(snapshot), "market": market,
            "basis": "Distinct collected reviews per feature; pain = defects and hard-to-use reports; not customer prevalence. "
                     "Findings: the LLM groups reviews, counts come from code.",
            "items": [_signal(t, k, texts, drafted, findings.get(t.feature_key), thresholds) for t, k in themes]}


QUADRANTS = [
    {"key": "act", "label": "Act", "hint": "Many reviews, mostly problems or wishes"},
    {"key": "protect", "label": "Protect", "hint": "Many reviews, few problems"},
    {"key": "watch", "label": "Watch", "hint": "Few reviews, mostly problems or wishes"},
    {"key": "background", "label": "Background", "hint": "Few reviews, few problems"},
]


@router.get("/signals/map", summary="Every signal of a market on one four-field map: reviews (x) vs share of problems and wishes (y)")
def signal_map(market: str | None = Query(None, description="US, EU, CN or omit for all markets pooled"),
               min_reviews: int = Query(3, ge=1, description="Hide signals with fewer reviews (noise)"),
               session: Session = Depends(get_session, scope="function")):
    settings = get_settings()
    snapshot = latest_snapshot_id(session, settings.target_model)
    thresholds = _thresholds(session)
    axes = {
        "x": {"key": "reviews", "label": "Reviews", "scale": "log", "threshold": thresholds["frequent_min_reviews"],
              "hint": "How many owners mention it",
              "detail": "Distinct collected reviews of this vehicle that mention the feature (one review counts once). "
                        "Collected reviews, not customer prevalence."},
        "y": {"key": "need_share", "label": "Problems & wishes", "scale": "linear", "min": 0, "max": 1,
              "threshold": thresholds["need_share_threshold"], "hint": "Share of those reviews reporting a problem or a wish",
              "detail": "Problem = defect or hard to use; wish = new request, discontinued feature or competitor parity. "
                        "The rest is praise or neutral mentions."},
    }
    if snapshot is None:
        return {"snapshot_id": None, "market": market, "axes": axes, "quadrants": QUADRANTS, "items": []}
    query = select(Theme).where(Theme.snapshot_id == snapshot, Theme.mention_review_count > 0)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    themes = list(session.scalars(query))
    shown = [t for t in themes if t.mention_review_count >= min_reviews]
    drafted = {}
    for r in session.scalars(select(Requirement).where(Requirement.target_model == settings.target_model)):
        drafted.setdefault((r.feature_key, r.market), []).append(r.id)
    findings = latest_findings(session, market, [t.feature_key for t in shown])
    items = []
    for t in sorted(shown, key=lambda t: -t.mention_review_count):
        kind = classify(t)
        items.append({
            "theme_id": t.id, "feature_key": t.feature_key, "label": t.label, "area": t.area, "kind": kind,
            "reviews": t.mention_review_count, "need_share": need_share(t), "quadrant": quadrant(t, thresholds),
            "pain": t.pain_review_count, "requests": t.request_review_count, "praise": t.praise_review_count,
            "findings": sum(f.kind in FINDING_KINDS.get(kind, {f.kind}) for f in findings.get(t.feature_key, [])),
            "requirement_ids": drafted.get((t.feature_key, t.market), []),
        })
    counts = Counter(i["quadrant"] for i in items)
    return {"snapshot_id": str(snapshot), "market": market, "axes": axes,
            "quadrants": [{**q, "signals": counts.get(q["key"], 0)} for q in QUADRANTS],
            "hidden_below_min_reviews": len(themes) - len(shown), "items": items}


@router.get("/signals/{feature_key}", summary="One signal opened up: how it was collected, tagged, counted, classified and grouped")
def signal_detail(feature_key: str, market: str | None = Query(None, description="US, EU, CN or omit for pooled"),
                  session: Session = Depends(get_session, scope="function")):
    settings = get_settings()
    snapshot = latest_snapshot_id(session, settings.target_model)
    theme = session.scalars(select(Theme).where(Theme.snapshot_id == snapshot, Theme.feature_key == feature_key,
                                                (Theme.market == market) if market else Theme.market.is_(None))).first() if snapshot else None
    if theme is None:
        raise HTTPException(404, f"no signal {feature_key} for market {market or 'all'}")
    thresholds = _thresholds(session)
    kind = classify(theme)
    findings = latest_findings(session, market, [feature_key]).get(feature_key, [])
    condense_run = session.get(SimRun, findings[0].run_id) if findings and findings[0].run_id else None
    reviews = theme.mention_review_count
    labeled_by_bmw = theme.derived_from_labels or 0
    quality = labeler_quality(session)
    cohorts = [{"channel": c["channel"], "dataset_key": c["dataset_key"], "markets": c["markets"],
                "reviews": c["mention_review_count"], "of_collected": c["feedback_review_count"],
                "share": round(c["share"], 3)} for c in (theme.cohorts or [])[:8]]
    channels = ", ".join(CHANNEL_LABELS.get(c, c) for c in theme.channels) or "no channel"
    q = next(x for x in QUADRANTS if x["key"] == quadrant(theme, thresholds))
    requirements = [r.id for r in session.scalars(select(Requirement).where(Requirement.feature_key == feature_key,
                                                                             Requirement.target_model == settings.target_model))
                    if r.market == market or market is None]
    texts = {r.record_id: (r.translation_en or r.text_original or "")
             for r in session.scalars(select(Record).where(Record.record_id.in_(theme.record_ids[:3])))}
    steps = [
        {"key": "collected", "label": "Collected", "short": f"{reviews} reviews · {channels}",
         "detail": "Reviews of this vehicle (or a group that contains it) from accepted sources. Brand-wide reviews "
                   f"({theme.brand_review_count}, e.g. My BMW app) and competitor reviews ({theme.competitor_review_count}) "
                   "mentioning the same feature are kept apart and not counted here.",
         "data": {"cohorts": cohorts}},
        {"key": "tagged", "label": "Tagged", "short": f"{labeled_by_bmw} by BMW labels · {max(0, reviews - labeled_by_bmw)} by the AI labeler",
         "detail": "Every review was split into claims: which catalog feature, and whether it reports a defect, a wish or "
                   "praise. BMW's own labels are used as they are; the rest was labeled by the AI labeler with BMW examples "
                   "and a verbatim quote per claim." + (f" Blind test against BMW labels: same area in "
                   f"{round(100 * quality['area_agreement'])} % of cases." if quality else ""),
         "data": {"labeler_quality": quality}},
        {"key": "counted", "label": "Counted", "short": f"{theme.pain_review_count} problems · {theme.request_review_count} wishes · "
                                                       f"{theme.praise_review_count} praise",
         "detail": "Code counts each review once per feature and market. A review can contain a problem and praise at once, "
                   "so the three numbers can add up to more than the reviews.",
         "data": {"by_claim_type": theme.counts_by_claim_type}},
        {"key": "classified", "label": "Classified", "short": explain_kind(theme),
         "detail": "Rule, first match wins: pain from 40 % problems; wish from 30 % wishes; strength from 60 % praise with "
                   "under 15 % problems; otherwise mixed. Problems = defects and 'difficult to use'.",
         "data": {"kind": kind}},
        {"key": "placed", "label": "Placed", "short": f"{q['label']}: {reviews} reviews, {round(100 * need_share(theme))} % problems or wishes",
         "detail": f"Frequent from {thresholds['frequent_min_reviews']} reviews; mostly problems from "
                   f"{round(100 * thresholds['need_share_threshold'])} % problems or wishes. Thresholds live in the policy.",
         "data": {"quadrant": q["key"]}},
        {"key": "grouped", "label": "Grouped",
         "short": f"{len(findings)} findings · {findings[0].model}" if findings else "Not grouped into findings yet",
         "detail": "The AI groups the reviews of a top signal into 2-5 concrete statements and assigns every review to one "
                   "of them; counts, shares and quotes come from code, quotes are verbatim.",
         "data": {"run_id": str(condense_run.id) if condense_run else None,
                  "at": condense_run.finished_at.isoformat() if condense_run and condense_run.finished_at else None}},
    ]
    return {"feature_key": feature_key, "label": theme.label, "area": theme.area, "market": market, "kind": kind,
            "quadrant": q["key"], "reviews": reviews, "need_share": need_share(theme),
            "how_sorted": steps, "findings": _ordered_findings(findings, kind),
            "sample_quotes": [{"record_id": rid, "text": texts[rid][:280]} for rid in theme.record_ids[:3] if rid in texts],
            "requirement_ids": requirements, "theme_id": theme.id}


class CondenseIn(BaseModel):
    markets: list[str | None] = Field(default=["US", "EU", None], description="Markets to condense; null = all pooled")
    kinds: list[Literal["pain", "request", "strength", "mixed"]] = ["pain", "request", "strength"]
    limit: int = Field(8, ge=1, le=30, description="Top signals per market and kind")


@router.post("/signals/condense", summary="Condense the top signals into concrete findings (background run, poll /api/simulations/{id})")
def condense(body: CondenseIn, session: Session = Depends(get_session, scope="function"), who: str = Depends(actor)):
    from parallax import signals as signal_service
    from parallax.orchestrator import launch

    run = signal_service.start(session, who, body.model_dump())
    session.commit()
    launch(run.id)
    return {"run_id": str(run.id), "status": run.status}


def labeler_quality(session: Session) -> dict | None:
    run = session.scalars(select(SimRun).where(SimRun.kind == "calibration", SimRun.status == "completed")
                          .order_by(SimRun.created_at.desc()).limit(1)).first()
    result = (run.progress or {}).get("result") if run else None
    if not result or result.get("area_recall_vs_bmw") is None:
        return None
    return {"area_agreement": result["area_recall_vs_bmw"], "exact_recall": result.get("recall_vs_bmw"),
            "sample": result.get("sample"), "run_id": str(run.id)}


def _text(label: str, hint: str, detail: str) -> dict:
    return {"label": label, "hint": hint, "detail": detail}


@router.get("/pipeline", summary="Start page of one vehicle: one card per stage with counts, status and the next action")
def pipeline(vehicle: str | None = Query(None, description="e.g. G60 or bmw:G60; default: the active vehicle"),
             session: Session = Depends(get_session, scope="function")):
    scope = VehicleScope(session, vehicle)
    target = scope.target_model
    # 1 sources: every record falls into exactly one scope; only the vehicle's records count as its data
    stream_records: Counter = Counter()
    outside: Counter = Counter()
    target_sources: set[str] = set()
    target_feedback = 0
    for stream, source_id, kind, subjects, n in session.execute(
            select(Source.stream, Source.source_id, Record.record_kind, Record.subject_ids, func.count())
            .join(Record, Record.source_id == Source.source_id).where(Record.superseded_by.is_(None))
            .group_by(Source.stream, Source.source_id, Record.record_kind, Record.subject_ids)):
        where = scope.of(subjects)
        if where != "target":
            outside[where] += n
            continue
        stream_records[stream] += n
        target_sources.add(source_id)
        if kind == "feedback":
            target_feedback += n
    pending_sources = session.scalar(select(func.count()).select_from(Source).where(
        Source.review_status == "pending", Source.source_id.in_(target_sources))) if target_sources else 0
    last_ingest = session.scalars(select(IngestRun).order_by(IngestRun.created_at.desc()).limit(1)).first()
    # 2 processing: the vehicle's feedback -> reviews with a topic -> signals -> findings
    by_bmw, by_ai = set(), set()
    pending_claims = 0
    for record_id, derived, status in session.execute(
            select(Claim.record_id, Claim.derived, Claim.review_status).join(Record, Record.record_id == Claim.record_id)
            .where(scope.target_filter(), Record.record_kind == "feedback", Record.superseded_by.is_(None),
                   Claim.feature_key.is_not(None), Claim.review_status != "rejected")):
        if status == "pending":
            pending_claims += 1
            continue
        (by_bmw if derived else by_ai).add(record_id)
    tagged = len(by_bmw | by_ai)
    by_ai -= by_bmw
    findings_count = session.scalar(select(func.count()).select_from(Finding).where(Finding.target_model == target)) or 0
    condensed_features = session.scalar(select(func.count(func.distinct(Finding.feature_key))).where(Finding.target_model == target)) or 0
    quality = labeler_quality(session)
    # 3 signals
    snapshot = latest_snapshot_id(session, target)
    pooled = list(session.scalars(select(Theme).where(Theme.snapshot_id == snapshot, Theme.market.is_(None),
                                                      Theme.mention_review_count > 0))) if snapshot else []
    kinds = Counter(classify(t) for t in pooled)
    thresholds = _thresholds(session)
    quadrants = Counter(quadrant(t, thresholds) for t in pooled)
    top = lambda k, key: [t.label for t in sorted((t for t in pooled if classify(t) == k), key=key, reverse=True)[:3]]
    # 4 experts, 5 decision: this vehicle's requirements only
    vehicle_reqs = list(session.scalars(select(Requirement).where(Requirement.target_model == target)))
    req_ids = {r.id for r in vehicle_reqs}
    req_status = dict(Counter(r.status for r in vehicle_reqs))
    runs = dict(Counter(r.status for r in session.scalars(select(SimRun).where(SimRun.kind.in_(EXPERT_RUN_KINDS)))
                        if set(r.requirement_ids or []) & req_ids))
    requirements = len(vehicle_reqs)

    def status(done: bool, started: bool) -> str:
        return "done" if done else ("in_progress" if started else "todo")

    code = target.split(":")[-1]
    agreement = f" Blind test against BMW labels: same area in {round(100 * quality['area_agreement'])} % of cases." if quality else ""
    funnel = [
        {"key": "reviews", "count": target_feedback, **_text(
            "Reviews", f"Customer feedback about the {code}",
            f"Feedback records whose subject is the {code} or a group that contains it. Study metrics and sales figures "
            "are not reviews and are not counted here.")},
        {"key": "tagged", "count": tagged, **_text(
            "With a topic", f"{len(by_bmw):,} by BMW labels · {len(by_ai):,} by the AI labeler",
            "Each review is split into claims: which catalog feature, and whether it reports a problem, a wish or praise. "
            "BMW's own labels are used as they are; the rest was labeled by the AI labeler with BMW examples." + agreement)},
        {"key": "signals", "count": len(pooled), **_text(
            "Signals", "One per feature, counted by code",
            "Code counts each review once per feature and market and classifies the feature as pain, wish, strength or mixed.")},
        {"key": "findings", "count": findings_count, **_text(
            "Findings", f"Concrete statements for {condensed_features} top signals",
            "For the top signals the AI groups reviews into 2-5 concrete statements; counts and quotes come from code.")},
    ]
    stages = [
        {"key": "sources", "title": "Sources", "question": "Where does the data come from?",
         "status": status(bool(target_sources) and not pending_sources, bool(target_sources)),
         "counts": {"sources": len(target_sources), "records": sum(stream_records.values()), "pending_review": pending_sources,
                    "by_stream": [{"stream": s, "label": STREAM_LABELS.get(s, s), "records": n} for s, n in stream_records.most_common()]},
         "outside_scope": [{"scope": k, "label": SCOPE_LABELS[k], "records": outside[k]} for k in SCOPES if k != "target" and outside[k]],
         "last_import": last_ingest.created_at.isoformat() if last_ingest else None},
        {"key": "processing", "title": "Processing", "question": "What did we extract from it?",
         "status": status(tagged > 0 and not pending_claims, tagged > 0 or pending_claims > 0),
         "counts": {"feedback_records": target_feedback, "records_with_claims": tagged,
                    "records_without_claims": max(0, target_feedback - tagged), "pending_claims": pending_claims,
                    "records_by_producer": {"BMW labels": len(by_bmw), "AI labeler": len(by_ai)}},
         "funnel": funnel,
         "gap": {"count": max(0, target_feedback - tagged), **_text(
             "No topic", "Mention no catalog feature",
             "Reviews without any catalog feature, e.g. 'great car' or dealer experience. They stay searchable but feed no signal.")},
         "labeler_quality": quality},
        {"key": "signals", "title": "Signals", "question": "What do customers tell us?",
         "status": status(bool(pooled), bool(snapshot)),
         "counts": {"features_with_evidence": len(pooled), "by_kind": dict(kinds), "by_quadrant": dict(quadrants),
                    "findings": findings_count, "condensed_features": condensed_features},
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
    if not target_sources:
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
    name, detail = VEHICLE_INFO.get(target, (code, ""))
    return {"target_model": target, "vehicle": {"entity_id": target, "code": code, "name": name, "detail": detail},
            "stages": stages, "next_action": nxt}


VEHICLE_INFO = {
    "bmw:G60": ("BMW 5 Series Sedan", "G60, incl. i5 (BEV) and 530e/550e (PHEV)"),
    "bmw:G68": ("BMW 5 Series Long Wheelbase", "G68, China only"),
    "bmw:G70": ("BMW 7 Series", "G70, incl. i7 (BEV)"),
    "bmw:F70": ("BMW 1 Series", "F70, Europe"),
}


@router.get("/vehicles", summary="Vehicles for the landing page: which one is active and how much data each has")
def vehicles(session: Session = Depends(get_session, scope="function")):
    from parallax.models import Entity

    target = get_settings().target_model
    counts: dict[str, int] = {}
    for subjects, n in session.execute(select(Record.subject_ids, func.count()).where(Record.superseded_by.is_(None))
                                       .group_by(Record.subject_ids)):
        for subject in subjects or ["brand_or_unresolved"]:
            counts[subject] = counts.get(subject, 0) + n
    entities = {e.entity_id: e for e in session.scalars(select(Entity).where(Entity.entity_id.like("bmw:%")))}
    items = []
    for entity_id, (name, detail) in VEHICLE_INFO.items():
        records = counts.get(entity_id, 0)
        items.append({"entity_id": entity_id, "code": entity_id.split(":")[1], "name": name, "detail": detail,
                      "records": records, "in_catalog": entity_id in entities,
                      "status": "active" if entity_id == target else ("data_available" if records else "not_imported")})
    items.append({"entity_id": "brand", "code": "ALL", "name": "Across vehicles", "detail": "Brand-wide and unresolved feedback (e.g. My BMW app)",
                  "records": counts.get("brand_or_unresolved", 0) + counts.get("bmw:brand", 0), "in_catalog": True,
                  "status": "data_available" if counts.get("brand_or_unresolved") else "not_imported"})
    return {"active": target, "items": items}


@router.get("/budgets", summary="Complaints vs. customer budget per simulated requirement (one call for the frequency-vs-importance chart)")
def budgets(market: str | None = Query(None, description="Requirement market filter (US, EU, CN); omit for all"),
            session: Session = Depends(get_session, scope="function")):
    from parallax.agents.roster import active_agents
    from parallax.models import PersonaResponse
    from parallax.requirements import themes_for

    personas = {a.id: a.market for a in active_agents(session, "market_persona")}
    query = select(Requirement).where(Requirement.last_run_id.is_not(None))
    if market:
        query = query.where(Requirement.market == market)
    items = []
    for req in session.scalars(query.order_by(Requirement.id)):
        responses = session.scalars(select(PersonaResponse).where(PersonaResponse.run_id == req.last_run_id,
                                                                  PersonaResponse.requirement_id == req.id)).all()
        by_market: dict[str, list[float]] = {}
        verdicts: dict[str, int] = {}
        for r in responses:
            if r.budget_points is not None:
                by_market.setdefault(personas.get(r.agent_id) or "other", []).append(r.budget_points)
            if r.verdict:
                verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1
        all_points = [b for values in by_market.values() for b in values]
        theme = next((t for t in themes_for(session, req) if t.market == req.market), None)
        items.append({
            "requirement_id": req.id, "title": req.title, "feature_key": req.feature_key, "market": req.market,
            "complaints": theme.pain_review_count if theme else None, "reviews": theme.mention_review_count if theme else None,
            "mean_budget_points_of_100": round(sum(all_points) / len(all_points), 1) if all_points else None,
            "budget_by_market": {m: round(sum(v) / len(v), 1) for m, v in by_market.items()},
            "verdicts": verdicts, "run_id": str(req.last_run_id), "has_budget": bool(all_points),
        })
    return {"market": market, "items": items,
            "note": "complaints = distinct reviews reporting a defect or difficulty; budget = simulated owners' share of 100 points"}
