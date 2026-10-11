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
from parallax.signals import (CHANNEL_LABELS, classify, explain_kind, finding_order, latest_findings, market_prior, need_share,
                              quadrant, ranked_themes, size, smoothed_need_share)
from parallax.themes import latest_snapshot_id

router = APIRouter(prefix="/api", tags=["pipeline"])

STREAM_LABELS = {"bmw": "BMW", "social": "Social media", "competitors": "Competitors"}
EXPERT_RUN_KINDS = ("simulation", "followup")


FINDING_KINDS = {"pain": {"pain"}, "request": {"request"}, "strength": {"praise"}}
OUTCOMES = {"approved": "change_coming", "rejected": "declined"}
FLOW_COLUMNS = {"bmw": 0, "online": 0, "excluded": 1, "bmw_labels": 1, "ai_labeler": 1, "no_topic": 1, "signals": 2,
                "findings": 3, "requirements": 4, "change_coming": 5, "declined": 5, "open": 5}


def _finding(f: Finding, signal_kind: str | None = None) -> dict:
    matches = signal_kind not in FINDING_KINDS or f.kind in FINDING_KINDS[signal_kind]
    return {"id": f.id, "title": f.title, "description": f.description, "kind": f.kind, "reviews": f.review_count,
            "share_of_theme": f.share_of_theme, "quotes": f.quotes, "record_ids": f.record_ids[:200],
            "matches_signal": matches}


def _ordered_findings(findings: list[Finding], kind: str) -> list[dict]:
    """Findings of the signal's own kind first (a pain card leads with pains, not with praise), then by size."""
    return sorted((_finding(f, kind) for f in findings), key=finding_order(kind))


def _signal(theme: Theme, kind: str, texts: dict[str, str], drafted: set, findings: list[Finding] | None,
            thresholds: dict, prior: float | None = None) -> dict:
    ordered = _ordered_findings(findings or [], kind)
    return {
        "theme_id": theme.id, "feature_key": theme.feature_key, "label": theme.label, "area": theme.area,
        "market": theme.market, "kind": kind, "reviews": theme.mention_review_count,
        "direct_reviews": theme.direct_review_count, "pain": theme.pain_review_count,
        "requests": theme.request_review_count, "praise": theme.praise_review_count,
        "need": theme.need_review_count, "need_share": need_share(theme), "quadrant": quadrant(theme, thresholds, prior),
        "weighted_reviews": round(size(theme), 1),
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
    prior = market_prior(list(session.scalars(select(Theme).where(
        Theme.snapshot_id == snapshot, Theme.mention_review_count > 0,
        (Theme.market == market) if market else Theme.market.is_(None)))))
    return {"snapshot_id": str(snapshot), "market": market,
            "basis": "Distinct collected reviews per feature; pain = defects and hard-to-use reports; not customer prevalence. "
                     "Findings: the LLM groups reviews, counts come from code.",
            "items": [_signal(t, k, texts, drafted, findings.get(t.feature_key), thresholds, prior) for t, k in themes]}


QUADRANTS = [
    {"key": "act", "label": "Act", "hint": "Many reviews, mostly problems or wishes"},
    {"key": "protect", "label": "Protect", "hint": "Many reviews, mostly praise or neutral"},
    {"key": "watch", "label": "Watch", "hint": "Few reviews, mostly problems or wishes"},
    {"key": "background", "label": "Background", "hint": "Few reviews, mostly praise or neutral"},
]


@router.get("/signals/map", summary="Every signal of a market on one four-field map: reviews (x) vs share of problems and wishes (y)")
def signal_map(market: str | None = Query(None, description="US, EU, CN or omit for all markets pooled"),
               min_reviews: int = Query(5, ge=1, description="Hide signals with fewer reviews (noise)"),
               session: Session = Depends(get_session, scope="function")):
    settings = get_settings()
    snapshot = latest_snapshot_id(session, settings.target_model)
    thresholds = _thresholds(session)
    axes = {
        "x": {"key": "weighted_reviews", "label": "Weighted reviews", "scale": "log", "threshold": thresholds["frequent_min_reviews"],
              "center_on_threshold": True, "low_label": "Few reviews", "high_label": "Many reviews",
              "hint": "How many owners mention it, weighted by source",
              "detail": "Distinct collected reviews of this vehicle that mention the feature, each counted with its evidence "
                        "weight (BMW feedback 1.0, online reviews 0.5 x author, less for emoji-laden or very short texts; "
                        "see /api/weights). Collected reviews, not customer prevalence."},
        "y": {"key": "need_share", "label": "Problems & wishes", "scale": "linear", "min": 0, "max": 1,
              "threshold": thresholds["need_share_threshold"], "center_on_threshold": True,
              "low_label": "Mostly praise", "high_label": "Mostly problems & wishes",
              "hint": "Share of those reviews reporting a problem or a wish",
              "detail": "Problem = defect or hard to use; wish = new request, discontinued feature or competitor parity. "
                        "The rest is praise or neutral mentions. Plotted with "
                        f"{thresholds.get('smoothing_reviews', 5)} pseudo-reviews at the market average, so small signals sit "
                        "closer to the middle instead of lining up at 0 %, 50 % or 100 %; need_share_raw is the plain share."},
    }
    if snapshot is None:
        return {"snapshot_id": None, "market": market, "axes": axes, "quadrants": QUADRANTS, "items": []}
    query = select(Theme).where(Theme.snapshot_id == snapshot, Theme.mention_review_count > 0)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    themes = list(session.scalars(query))
    prior = market_prior(themes)
    strength = thresholds.get("smoothing_reviews", 5)
    shown = [t for t in themes if t.mention_review_count >= min_reviews]
    drafted = {}
    for r in session.scalars(select(Requirement).where(Requirement.target_model == settings.target_model)):
        drafted.setdefault((r.feature_key, r.market), []).append(r.id)
    findings = latest_findings(session, market, [t.feature_key for t in shown])
    items = []
    for t in sorted(shown, key=lambda t: -size(t)):
        kind = classify(t)
        items.append({
            "theme_id": t.id, "feature_key": t.feature_key, "label": t.label, "area": t.area, "kind": kind,
            "reviews": t.mention_review_count, "weighted_reviews": round(size(t), 1),
            "need_share": smoothed_need_share(t, prior, strength),
            "need_share_raw": need_share(t, weighted=False), "quadrant": quadrant(t, thresholds, prior),
            "pain": t.pain_review_count, "requests": t.request_review_count, "praise": t.praise_review_count,
            "findings": sum(f.kind in FINDING_KINDS.get(kind, {f.kind}) for f in findings.get(t.feature_key, [])),
            "requirement_ids": drafted.get((t.feature_key, t.market), []),
        })
    counts = Counter(i["quadrant"] for i in items)
    return {"snapshot_id": str(snapshot), "market": market, "axes": axes, "market_average_need_share": round(prior, 3),
            "quadrants": [{**q, "signals": counts.get(q["key"], 0)} for q in QUADRANTS],
            "hidden_below_min_reviews": len(themes) - len(shown), "items": items}


@router.get("/signals/snapshots", summary="Signal snapshots (one per rebuild), newest first: the 'before' and 'after' points for comparisons")
def signal_snapshots(limit: int = Query(20, le=100), session: Session = Depends(get_session, scope="function")):
    target = get_settings().target_model
    rows = session.execute(
        select(Theme.snapshot_id, func.min(Theme.created_at), func.count(),
               func.sum(Theme.mention_review_count).filter(Theme.market.is_(None)))
        .where(Theme.target_model == target).group_by(Theme.snapshot_id)
        .order_by(func.min(Theme.created_at).desc()).limit(limit)).all()
    return {"items": [{"snapshot_id": str(sid), "created_at": at.isoformat() if at else None, "themes": n,
                       "pooled_mentions": int(m or 0)} for sid, at, n, m in rows]}


@router.get("/signals/compare", summary="What changed between two signal snapshots (default: the latest against the one before)")
def signal_compare(before: str | None = None, after: str | None = None,
                   market: str | None = Query(None, description="US, EU, CN or omit for pooled"),
                   top: int = Query(10, ge=3, le=50), session: Session = Depends(get_session, scope="function")):
    snaps = signal_snapshots(limit=2, session=session)["items"]
    after = after or (snaps[0]["snapshot_id"] if snaps else None)
    before = before or (snaps[1]["snapshot_id"] if len(snaps) > 1 else None)
    if not after or not before:
        raise HTTPException(404, "need two signal snapshots to compare")
    thresholds = _thresholds(session)

    def load(snapshot: str) -> dict[str, Theme]:
        query = select(Theme).where(Theme.snapshot_id == snapshot, Theme.mention_review_count > 0)
        query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
        return {t.feature_key: t for t in session.scalars(query)}

    old, new = load(before), load(after)
    rank = lambda themes: {k: i for i, k in enumerate(sorted(themes, key=lambda k: -themes[k].mention_review_count), 1)}
    old_rank, new_rank = rank(old), rank(new)
    frequent = thresholds["frequent_min_reviews"]

    def stats(themes: dict[str, Theme]) -> dict:
        return {"signals": len(themes), "reviews": sum(t.mention_review_count for t in themes.values()),
                "frequent_signals": sum(t.mention_review_count >= frequent for t in themes.values()),
                "multi_channel_signals": sum(len(t.channels or []) >= 2 for t in themes.values())}

    old_top = {k for k, r in old_rank.items() if r <= top}
    new_top = {k for k, r in new_rank.items() if r <= top}
    changes = []
    for key in set(old) | set(new):
        o, n = old.get(key), new.get(key)
        delta = (n.mention_review_count if n else 0) - (o.mention_review_count if o else 0)
        if delta or (o is None) != (n is None):
            changes.append({"feature_key": key, "label": (n or o).label, "before": o.mention_review_count if o else 0,
                            "after": n.mention_review_count if n else 0, "delta": delta,
                            "rank_before": old_rank.get(key), "rank_after": new_rank.get(key),
                            "channels_after": n.channels if n else [], "new": o is None})
    changes.sort(key=lambda c: -abs(c["delta"]))
    return {"before": before, "after": after, "market": market,
            "summary": {"before": stats(old), "after": stats(new), "top": top,
                        "top_unchanged": len(old_top & new_top), "entered_top": sorted(new_top - old_top),
                        "left_top": sorted(old_top - new_top)},
            "changes": changes[:100]}


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
    market_themes = list(session.scalars(select(Theme).where(
        Theme.snapshot_id == snapshot, Theme.mention_review_count > 0,
        (Theme.market == market) if market else Theme.market.is_(None))))
    prior = market_prior(market_themes)
    q = next(x for x in QUADRANTS if x["key"] == quadrant(theme, thresholds, prior))
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
        {"key": "weighted", "label": "Weighted", "short": f"{reviews} reviews → {size(theme):.0f} weighted",
         "detail": "Each review counts with its evidence weight: BMW feedback 1.0; online reviews 0.5, times 1.0 when the "
                   "author owns the car, 0.8 when unclear, 0.6 when not; times 0.95 with emojis and 0.9 under 40 characters. "
                   "The weights are a PM policy (GET /api/weights); the raw count stays visible.",
         "data": {"weighted_reviews": round(size(theme), 1), "weighted_need_share": need_share(theme)}},
        {"key": "classified", "label": "Classified", "short": explain_kind(theme),
         "detail": "Rule, first match wins: pain from 40 % problems; wish from 30 % wishes; strength from 60 % praise with "
                   "under 15 % problems; otherwise mixed. Problems = defects and 'difficult to use'.",
         "data": {"kind": kind}},
        {"key": "placed", "label": "Placed", "short": f"{q['label']}: {size(theme):.0f} weighted reviews, {round(100 * need_share(theme))} % problems or wishes",
         "detail": f"Frequent from {thresholds['frequent_min_reviews']} reviews; mostly problems from "
                   f"{round(100 * thresholds['need_share_threshold'])} % problems or wishes. Small signals are pulled "
                   f"toward the market average ({round(100 * prior)} %) by {thresholds.get('smoothing_reviews', 5)} "
                   "pseudo-reviews before placing. Thresholds live in the policy.",
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


def _processing_flow(session: Session, scope: VehicleScope, by_bmw: set, by_ai: set) -> tuple[dict, set]:
    """Left-to-right flow of the vehicle's reviews (link values = reviews): where they come from, what triage kept,
    who found the topic, what became signals and findings. Returns the flow and the reviews excluded by triage."""
    from parallax.models import RecordTriage

    policy = active_policy(session).document["parallax"]
    triage_filter = policy.get("triage_filter", {})
    stream_of = dict(session.execute(
        select(Record.record_id, Source.stream).join(Source, Source.source_id == Record.source_id)
        .where(scope.target_filter(), Record.record_kind == "feedback", Record.superseded_by.is_(None))).all())
    flagged = {rid for rid, relevant, vehicle in session.execute(
        select(RecordTriage.record_id, RecordTriage.relevant, RecordTriage.vehicle)
        .join(Record, Record.record_id == RecordTriage.record_id).where(scope.target_filter()))
        if stream_of.get(rid) not in (None, "bmw") and (
            (triage_filter.get("exclude_not_relevant", True) and not relevant)
            or vehicle in triage_filter.get("exclude_vehicles", []))}
    triaged = session.scalar(select(func.count()).select_from(RecordTriage).join(Record, Record.record_id == RecordTriage.record_id)
                             .where(scope.target_filter())) or 0
    excluded = flagged if triage_filter.get("enabled") else set()
    bmw_ids = {rid for rid, stream in stream_of.items() if stream == "bmw"}
    online_ids = set(stream_of) - bmw_ids
    labeled_bmw, labeled_ai = by_bmw - excluded, (by_ai - by_bmw) - excluded
    in_findings = set()
    for ids in session.scalars(select(Finding.record_ids).where(Finding.target_model == scope.target_model)):
        in_findings.update(ids or [])
    tagged = labeled_bmw | labeled_ai
    code = scope.target_model.split(":")[-1]
    online_detail = (f"YouTube comments, app-store and forum reviews collected under the {code}. Triage checked "
                     f"{triaged:,} of them for vehicle, author and relevance; {len(flagged):,} are not relevant or about "
                     "another car. " + ("They are excluded from the signals." if excluded else
                                         "They still count until the PM switches the triage filter on."))
    nodes = [
        {"key": "bmw", "label": "BMW feedback", "count": len(bmw_ids), "unit": "reviews", "weight": "×1.0",
         "hint": "Owners, through BMW channels",
         "detail": "BMW's own feedback export: every row comes with vehicle, engine type, country and, for most rows, "
                   "BMW's topic and feedback type."},
        {"key": "online", "label": "Online reviews", "count": len(online_ids), "unit": "reviews", "weight": "×0.5 × author",
         "hint": f"{len(flagged):,} flagged by triage" if triaged else "Not triaged yet", "detail": online_detail},
    ]
    links = []
    if excluded:
        nodes.append({"key": "excluded", "label": "Excluded", "count": len(excluded), "unit": "reviews",
                      "hint": "Not relevant or another car", "detail": online_detail})
        links.append({"source": "online", "target": "excluded", "value": len(excluded & online_ids)})
    nodes += [
        {"key": "bmw_labels", "label": "BMW labels", "count": len(labeled_bmw), "unit": "reviews",
         "hint": "Topic from BMW's classification", "detail": "BMW's VFC topic and feedback type, used as they are."},
        {"key": "ai_labeler", "label": "AI labeler", "count": len(labeled_ai), "unit": "reviews",
         "hint": "Topic found by our labeler",
         "detail": "gpt-5-mini with BMW examples assigns catalog features and feedback type; every claim needs a verbatim "
                   "quote from the review."},
        {"key": "no_topic", "label": "No topic", "count": 0, "unit": "reviews", "hint": "No catalog feature found",
         "detail": "Mostly reviews that name no catalog feature (e.g. 'great car'); also texts under 15 characters and "
                   "claims dropped because their quote did not match."},
        {"key": "signals", "label": "Signals", "count": 0, "unit": "signals", "hint": "One per feature, counted by code",
         "detail": "Each review counts once per feature and market; the feature is classified as pain, wish, strength or mixed."},
        {"key": "findings", "label": "Findings", "count": 0, "unit": "findings", "hint": "Concrete statements for the top signals",
         "detail": "The AI groups the reviews of a top signal into 2-5 concrete statements; counts and quotes come from code."},
    ]
    for source_key, ids in (("bmw", bmw_ids), ("online", online_ids - excluded)):
        links += [{"source": source_key, "target": "bmw_labels", "value": len(ids & labeled_bmw)},
                  {"source": source_key, "target": "ai_labeler", "value": len(ids & labeled_ai)},
                  {"source": source_key, "target": "no_topic", "value": len(ids - tagged)}]
    links += [{"source": "bmw_labels", "target": "signals", "value": len(labeled_bmw)},
              {"source": "ai_labeler", "target": "signals", "value": len(labeled_ai)},
              {"source": "signals", "target": "findings", "value": len(tagged & in_findings)}]
    # Findings -> requirements -> the PM's decision: how much of the customer voice turns into change.
    from parallax.models import RequirementEvidence

    requirements = list(session.scalars(select(Requirement).where(Requirement.target_model == scope.target_model)))
    evidence: dict[str, set] = {}
    for requirement_id, record_id in session.execute(
            select(RequirementEvidence.requirement_id, RequirementEvidence.record_id)
            .where(RequirementEvidence.requirement_id.in_([r.id for r in requirements]))):
        evidence.setdefault(requirement_id, set()).add(record_id)
    outcome_reviews: dict[str, set] = {"change_coming": set(), "declined": set(), "open": set()}
    outcome_count: Counter = Counter()
    for r in requirements:
        outcome = OUTCOMES.get(r.status, "open")
        outcome_count[outcome] += 1
        outcome_reviews[outcome] |= evidence.get(r.id, set()) & tagged & in_findings
    outcome_reviews["declined"] -= outcome_reviews["change_coming"]
    outcome_reviews["open"] -= outcome_reviews["change_coming"] | outcome_reviews["declined"]
    behind = set().union(*outcome_reviews.values())
    nodes += [
        {"key": "requirements", "label": "Requirements", "count": len(requirements), "unit": "requirements",
         "hint": "Drafted from findings", "detail": "Requirements drafted from the findings; the band is the reviews linked "
                                                    "to them as evidence."},
        {"key": "change_coming", "label": "Change coming", "count": outcome_count["change_coming"], "unit": "requirements",
         "hint": "Approved by the PM for the successor", "detail": "Requirements the PM approved for the next generation."},
        {"key": "declined", "label": "Declined", "count": outcome_count["declined"], "unit": "requirements",
         "hint": "Rejected by the PM", "detail": "Requirements the PM rejected, with the rationale in the timeline."},
        {"key": "open", "label": "Open", "count": outcome_count["open"], "unit": "requirements",
         "hint": "Waiting for councils or your decision", "detail": "Proposed, in review, challenged or postponed."},
    ]
    links += [{"source": "findings", "target": "requirements", "value": len(behind)}]
    links += [{"source": "requirements", "target": k, "value": len(v)} for k, v in outcome_reviews.items()]
    counts = {n["key"]: n for n in nodes}
    counts["no_topic"]["count"] = len((set(stream_of) - excluded) - tagged)
    for node in nodes:  # left-to-right position, explicit so nodes without bands (count 0) still sit in their column
        node["column"] = FLOW_COLUMNS[node["key"]]
    return {"nodes": nodes, "links": [l for l in links if l["value"] > 0], "link_unit": "reviews",
            "triage": {"triaged": triaged, "flagged": len(flagged), "filter_enabled": bool(excluded)}}, excluded


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
    claim_status, producers = Counter(), Counter()
    for record_id, derived, status, producer, feature_key in session.execute(
            select(Claim.record_id, Claim.derived, Claim.review_status, Claim.producer, Claim.feature_key)
            .join(Record, Record.record_id == Claim.record_id)
            .where(scope.target_filter(), Record.record_kind == "feedback", Record.superseded_by.is_(None))):
        claim_status[status] += 1
        producers["BMW labels" if derived else (producer or {}).get("method", "unknown")] += 1
        if status == "accepted" and feature_key:
            (by_bmw if derived else by_ai).add(record_id)
    pending_claims = claim_status.get("pending", 0)
    flow, excluded = _processing_flow(session, scope, by_bmw, by_ai)
    by_bmw -= excluded
    by_ai -= excluded
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
    pooled_prior = market_prior(pooled)
    quadrants = Counter(quadrant(t, thresholds, pooled_prior) for t in pooled)
    for node in flow["nodes"]:
        node["count"] = {"signals": len(pooled), "findings": findings_count}.get(node["key"], node["count"])
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
                    "claims_by_status": dict(claim_status), "claims_by_producer": dict(producers),
                    "records_by_producer": {"BMW labels": len(by_bmw), "AI labeler": len(by_ai)}},
         "funnel": funnel,
         "flow": flow,
         "gap": {"count": max(0, target_feedback - tagged), **_text(
             "No topic", "No catalog feature found",
             "Mostly reviews that name no catalog feature (e.g. 'great car', dealer experience); also texts under 15 "
             "characters and claims dropped because their quote did not match the review. They stay searchable but feed "
             "no signal.")},
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


@router.get("/overview/flow", summary="All data, before any vehicle: streams -> triage -> which vehicle it belongs to")
def overview_flow(session: Session = Depends(get_session, scope="function")):
    from parallax.models import RecordTriage

    scope = VehicleScope(session, None)
    stream_n, dropped, unchecked = Counter(), Counter(), Counter()
    to_scope: Counter = Counter()
    for stream, kind, subjects, relevant, n in session.execute(
            select(Source.stream, Record.record_kind, Record.subject_ids, RecordTriage.relevant, func.count())
            .join(Record, Record.source_id == Source.source_id)
            .outerjoin(RecordTriage, RecordTriage.record_id == Record.record_id)
            .where(Record.superseded_by.is_(None))
            .group_by(Source.stream, Record.record_kind, Record.subject_ids, RecordTriage.relevant)):
        stream_n[stream] += n
        if stream != "bmw" and kind == "feedback" and relevant is False:
            dropped[stream] += n
            continue
        if stream != "bmw" and kind == "feedback" and relevant is None:
            unchecked[stream] += n
        to_scope[(stream, scope.of(subjects))] += n
    code = scope.target_model.split(":")[-1]
    nodes = [{"key": s_, "label": STREAM_LABELS.get(s_, s_), "count": n, "unit": "records",
              "hint": {"bmw": "Feedback, study and sales from BMW", "social": "YouTube, app stores, forums",
                       "competitors": "Editorial reviews, forums, spec sheets"}.get(s_, ""), "detail": ""}
             for s_, n in stream_n.most_common()]
    nodes.append({"key": "not_relevant", "label": "Not relevant", "count": sum(dropped.values()), "unit": "records",
                  "hint": "Triage: nothing about the car", "detail": "Online reviews that triage marked as not relevant "
                  "(greetings, spam, off-topic). " + triage_note()})
    labels = {"target": f"{code}", "other_models": "Other BMW models", "competitor": "Competitors", "brand": "Brand-wide"}
    hints = {"target": "Collected under this vehicle or its group", "other_models": "e.g. 7 Series, 1 Series",
             "competitor": "Non-BMW vehicles", "brand": "No vehicle, e.g. My BMW app reviews"}
    for key in SCOPES:
        nodes.append({"key": key, "label": labels[key], "count": sum(n for (st, sc), n in to_scope.items() if sc == key),
                      "unit": "records", "hint": hints[key], "detail": SCOPE_LABELS[key]})
    for node in nodes:
        node["column"] = 0 if node["key"] in stream_n else 1
    links = [{"source": st, "target": "not_relevant", "value": n} for st, n in dropped.items()]
    links += [{"source": st, "target": sc, "value": n} for (st, sc), n in to_scope.items()]
    return {"nodes": nodes, "links": [l for l in links if l["value"] > 0], "link_unit": "records",
            "unchecked_online": sum(unchecked.values()),
            "note": "BMW records are owner data by source and are not triaged. " + triage_note()}


@router.get("/weights", summary="Every weight Parallax uses, in one place: evidence, owner markets, decision criteria")
def weights(session: Session = Depends(get_session, scope="function")):
    policy = active_policy(session)
    ext = policy.document["parallax"]
    evidence = ext.get("evidence_weights", {})
    markets = ext["persona_weighting"]["market_weights"]
    total = sum(markets.values()) or 1
    return {
        "policy_version": policy.id,
        "evidence": {
            "rule": "weight of one review = source × author (online only) × text",
            "source": [{"key": k, "label": STREAM_LABELS.get(k, k), "weight": v} for k, v in evidence.get("source", {}).items()],
            "author": [{"key": k, "label": {"owner": "Owner", "unclear": "Not stated", "not_owner": "Not an owner"}.get(k, k),
                        "weight": v} for k, v in evidence.get("author", {}).items()],
            "text": [{"key": "emoji", "label": "Contains emojis", "weight": evidence.get("emoji_factor", 1.0)},
                     {"key": "short", "label": f"Under {evidence.get('short_text', {}).get('max_chars', 0)} characters",
                      "weight": evidence.get("short_text", {}).get("factor", 1.0)}],
            "used_for": "Signal map (x = weighted reviews, y = weighted share of problems and wishes) and quadrants. "
                        "Raw counts stay visible; the demand score keeps raw counts.",
        },
        "owners": {
            "rule": "owner weight = market share of planned 2030 volume / owners in that market × validation multiplier",
            "markets": [{"key": k, "weight": round(v / total, 2), "volume_2030": v} for k, v in markets.items()],
            "validation": ext["persona_weighting"]["validation_multipliers"],
            "basis": ext["persona_weighting"].get("market_weight_basis"),
            "used_for": "Simulated impact and vehicle-market-fit ratings from the customer council.",
        },
        "criteria": [{"key": c["key"], "weight": c["weight"], "meaning": c.get("meaning")}
                     for c in policy.document.get("decision_model", {}).get("criteria", [])],
        "criteria_used_for": "Score = weighted sum of the six criteria (0-100); simulated and assumed ratings only widen the range.",
        "company_council": "No numeric weight: departments give arguments, conditions and criterion ranges, not votes that are added up.",
    }


@router.get("/overview/decisions", summary="Start page: per vehicle where the pipeline stands and which decisions are open or made")
def overview_decisions(session: Session = Depends(get_session, scope="function")):
    from parallax.models import PMDecision, Recommendation

    target = get_settings().target_model
    requirements = list(session.scalars(select(Requirement)))
    latest_rec = {}
    for rec in session.scalars(select(Recommendation).order_by(Recommendation.id)):
        latest_rec[rec.requirement_id] = rec.recommendation
    vehicles = []
    for entity_id, (name, detail) in VEHICLE_INFO.items():
        mine = [r for r in requirements if r.target_model == entity_id]
        snapshot = latest_snapshot_id(session, entity_id)
        signals = session.scalar(select(func.count()).select_from(Theme).where(
            Theme.snapshot_id == snapshot, Theme.market.is_(None), Theme.mention_review_count > 0)) if snapshot else 0
        outcomes = Counter(OUTCOMES.get(r.status, "open") for r in mine)
        vehicles.append({
            "entity_id": entity_id, "code": entity_id.split(":")[-1], "name": name, "detail": detail,
            "status": "active" if entity_id == target else "coming", "signals": signals or 0,
            "requirements": len(mine), "councils_run": sum(1 for r in mine if r.last_run_id),
            "ai_suggests": dict(Counter(latest_rec[r.id] for r in mine if r.id in latest_rec)),
            "decisions": {k: outcomes.get(k, 0) for k in ("change_coming", "declined", "open")},
            "last_activity": max((r.updated_at for r in mine), default=None),
        })
    needs = [r for r in requirements if r.status == "in_review"]
    needs.sort(key=lambda r: (r.priority_rank or 999, r.id))
    decisions = list(session.scalars(select(PMDecision).order_by(PMDecision.id.desc()).limit(10)))
    titles = {r.id: r.title for r in requirements}
    all_decisions = list(session.scalars(select(PMDecision)))
    rated = [d for d in all_decisions if d.agreed_with_ai is not None]
    return {
        "vehicles": vehicles,
        "needs_decision": [{"requirement_id": r.id, "title": r.title, "vehicle": r.target_model.split(":")[-1], "market": r.market,
                            "ai_suggests": latest_rec.get(r.id), "score_low": r.score_low, "score_high": r.score_high,
                            "priority_rank": r.priority_rank} for r in needs],
        "recent_decisions": [{"requirement_id": d.requirement_id, "title": titles.get(d.requirement_id), "action": d.action,
                              "by": d.actor_id, "at": d.created_at.isoformat(), "agreed_with_ai": d.agreed_with_ai}
                             for d in decisions],
        "agreement_with_ai": {"decisions": len(rated), "agreed": sum(1 for d in rated if d.agreed_with_ai)},
    }


def triage_note() -> str:
    from parallax.triage import VALIDATION_NOTE

    return VALIDATION_NOTE


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
    # Same scope rule as the pipeline: a vehicle's records include its groups (e.g. "5 Series"), so the card
    # number equals the number on the vehicle's start page.
    rows = session.execute(select(Record.subject_ids, func.count()).where(Record.superseded_by.is_(None))
                           .group_by(Record.subject_ids)).all()
    scopes = {entity_id: VehicleScope(session, entity_id) for entity_id in VEHICLE_INFO}
    counts: Counter = Counter()
    brand = 0
    for subjects, n in rows:
        for entity_id, scope in scopes.items():
            if scope.of(subjects) == "target":
                counts[entity_id] += n
        brand += n if scopes[target].of(subjects) == "brand" else 0
    entities = {e.entity_id: e for e in session.scalars(select(Entity).where(Entity.entity_id.like("bmw:%")))}
    items = []
    for entity_id, (name, detail) in VEHICLE_INFO.items():
        records = counts.get(entity_id, 0)
        items.append({"entity_id": entity_id, "code": entity_id.split(":")[1], "name": name, "detail": detail,
                      "records": records, "in_catalog": entity_id in entities,
                      "status": "active" if entity_id == target else ("data_available" if records else "not_imported")})
    items.append({"entity_id": "brand", "code": "ALL", "name": "Across vehicles", "detail": "Brand-wide and unresolved feedback (e.g. My BMW app)",
                  "records": brand, "in_catalog": True, "status": "data_available" if brand else "not_imported"})
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
