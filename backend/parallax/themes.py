"""Deterministic theme signals: distinct reviews per feature, per market bucket and cohort.

Counting follows the research contract: one review counts once per feature, cohorts keep
dataset/channel/subject/market/sampling apart, shares are within-cohort collected-review shares
(not customer prevalence), and other BMW models' records are excluded from the target scope.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.models import Claim, Entity, Feature, Record, Source, Theme
from parallax.policy import active_policy, market_bucket

REQUEST_TYPES = {"new_request", "discontinued", "competitor_parity"}
PAIN_TYPES = {"defect"}


@dataclass
class _Acc:
    parents: set = field(default_factory=set)
    competitor: set = field(default_factory=set)
    brand: set = field(default_factory=set)
    direct: set = field(default_factory=set)
    by_type: dict = field(default_factory=lambda: defaultdict(set))
    pain: set = field(default_factory=set)
    channels: set = field(default_factory=set)
    cohort_parents: dict = field(default_factory=lambda: defaultdict(set))
    eligible: set = field(default_factory=set)
    derived: set = field(default_factory=set)
    pending: set = field(default_factory=set)


def target_scope(session: Session, target_model: str) -> tuple[set[str], set[str]]:
    entities = session.scalars(select(Entity)).all()
    bmw_models = {e.entity_id for e in entities if e.type == "vehicle_model" and e.entity_id.startswith("bmw:")}
    relevant = {target_model} | {e.entity_id for e in entities if e.type == "vehicle_group" and target_model in (e.members or [])}
    return bmw_models, relevant


def subject_scope(subjects: set[str], target_model: str, relevant: set[str], proxies: set[str] = frozenset()) -> str:
    if target_model in subjects:
        return "direct"
    if subjects & relevant:
        return "group"
    if subjects & proxies:
        return "proxy"
    if any(s.startswith("competitor:") for s in subjects):
        return "competitor"
    return "brand_or_unresolved"


def llm_eligible(source: Source, allow_unreviewed: bool) -> bool:
    if allow_unreviewed:
        return source.review_status != "rejected" and source.external_llm is not False
    return source.review_status == "accepted" and source.external_llm is True


def demand_score(anchors: list[dict], reviews: int, max_share: float, channels: int) -> float:
    for anchor in anchors:
        if reviews >= anchor["min_reviews"] and max_share >= anchor["min_cohort_share"] and channels >= anchor["min_channels"]:
            return float(anchor["score"])
    return 0.0


def impact_score(anchors: dict, acc: _Acc, texts: dict[str, str]) -> float | None:
    total = len(acc.parents)
    if not total:
        return None
    requests = set().union(*(acc.by_type.get(t, set()) for t in REQUEST_TYPES))
    praise = acc.by_type.get("praise", set())
    if len(acc.pain) / total >= 0.5:
        score = anchors["pain_majority"]
    elif len(requests) / total >= 0.5:
        score = anchors["request_majority"]
    elif len(praise) / total >= 0.6:
        score = anchors["praise_majority"]
    else:
        score = anchors["mixed"]
    markers = [m.lower() for m in anchors.get("severity_markers", [])]
    if any(any(m in (texts.get(r) or "").lower() for m in markers) for r in acc.pain):
        score += anchors.get("severity_bonus", 0.0)
    return min(5.0, score)


def build_themes(session: Session, *, target_model: str, include_examples: bool = False,
                 allow_unreviewed_for_llm: bool = False, include_pending_claims: bool | None = None) -> dict:
    policy = active_policy(session).document
    ext = policy["parallax"]
    statuses = set(ext["theme_claim_statuses"])
    if include_pending_claims:
        statuses.add("pending")
    bmw_models, relevant = target_scope(session, target_model)
    proxies = {model for models in ext.get("market_proxies", {}).values() for model in models}

    rows = session.execute(
        select(Record, Source).join(Source, Source.source_id == Record.source_id)
        .where(Record.record_kind == "feedback", Record.superseded_by.is_(None), Source.review_status != "rejected")
    ).all()
    retained: dict[str, tuple[Record, Source]] = {}
    for record, source in rows:
        if source.is_example and not include_examples:
            continue
        subjects = set(record.subject_ids or [])
        if subjects & bmw_models and not subjects & (relevant | proxies):
            continue  # assigned only to another BMW model
        retained[record.record_id] = (record, source)

    cohort_of: dict[str, tuple] = {}
    cohort_size: dict[tuple, int] = defaultdict(int)
    buckets_of: dict[str, set[str]] = {}
    texts: dict[str, str] = {}
    for record_id, (record, source) in retained.items():
        key = (source.dataset_key, source.channel, tuple(sorted(record.subject_ids or [])),
               tuple(sorted(record.markets or [])), source.sampling.get("method"), source.sampling.get("query"))
        cohort_of[record_id] = key
        cohort_size[key] += 1
        buckets_of[record_id] = {market_bucket(policy, m) for m in (record.markets or [])}
        texts[record_id] = record.text_original or ""

    claims = [
        claim for claim in session.scalars(
            select(Claim).where(Claim.feature_key.is_not(None), Claim.review_status != "rejected")
        ).all()
        if claim.record_id in retained
    ]

    acc: dict[tuple[str | None, str], _Acc] = defaultdict(_Acc)
    for claim in claims:
        parent = claim.record_id
        record, source = retained[parent]
        scope = subject_scope(set(record.subject_ids or []), target_model, relevant, proxies)
        for bucket in [None, *buckets_of[parent]]:
            a = acc[(bucket, claim.feature_key)]
            if claim.review_status not in statuses:
                a.pending.add(parent)
                continue
            if scope == "competitor":
                a.competitor.add(parent)
                continue
            if scope == "brand_or_unresolved":
                a.brand.add(parent)  # e.g. My BMW app reviews: shown as brand-wide context, not G60 demand
                continue
            a.parents.add(parent)
            if target_model in (record.subject_ids or []):
                a.direct.add(parent)
            a.by_type[claim.claim_type].add(parent)
            if claim.claim_type in PAIN_TYPES or (claim.source_fields or {}).get("FeedbackType") == "Difficult to Use":
                a.pain.add(parent)
            a.channels.add(source.channel)
            a.cohort_parents[cohort_of[parent]].add(parent)
            if llm_eligible(source, allow_unreviewed_for_llm):
                a.eligible.add(parent)
            if claim.derived:
                a.derived.add(parent)

    features = {f.feature_key: f for f in session.scalars(select(Feature)).all()}
    snapshot_id = uuid.uuid4()
    created = 0
    min_cohort = ext.get("min_cohort_size_for_share", 0)
    for (bucket, feature_key), a in acc.items():
        if not a.parents and not a.pending and not a.competitor and not a.brand:
            continue
        cohorts = []
        for key, parents in a.cohort_parents.items():
            dataset, channel, subjects, markets, method, query = key
            cohorts.append({
                "dataset_key": dataset, "channel": channel, "subject_ids": list(subjects), "markets": list(markets),
                "collection_method": method, "query": query, "feedback_review_count": cohort_size[key],
                "mention_review_count": len(parents), "share": len(parents) / cohort_size[key],
            })
        cohorts.sort(key=lambda c: -c["mention_review_count"])
        max_share = max((c["share"] for c in cohorts if c["feedback_review_count"] >= min_cohort), default=0.0)
        requests = set().union(*(a.by_type.get(t, set()) for t in REQUEST_TYPES))
        feature = features.get(feature_key)
        session.add(Theme(
            snapshot_id=snapshot_id, target_model=target_model, market=bucket, feature_key=feature_key,
            label=feature.label if feature else feature_key, area=feature.area if feature else None,
            mention_review_count=len(a.parents), direct_review_count=len(a.direct),
            pending_claim_review_count=len(a.pending - a.parents), request_review_count=len(requests),
            competitor_review_count=len(a.competitor), competitor_record_ids=sorted(a.competitor)[:500],
            brand_review_count=len(a.brand), brand_record_ids=sorted(a.brand)[:500],
            pain_review_count=len(a.pain), praise_review_count=len(a.by_type.get("praise", set())),
            counts_by_claim_type={k: len(v) for k, v in sorted(a.by_type.items())},
            channels=sorted(a.channels), cohorts=cohorts, max_cohort_share=max_share,
            record_ids=sorted(a.parents), llm_eligible_record_count=len(a.eligible),
            derived_from_labels=len(a.derived),
            demand_score=demand_score(ext["demand_anchors"], len(a.parents), max_share, len(a.channels)),
            impact_score=impact_score(ext["impact_anchors"], a, texts),
        ))
        created += 1
    session.flush()
    return {
        "snapshot_id": str(snapshot_id), "themes": created, "retained_feedback_records": len(retained),
        "claims_considered": len(claims), "claim_statuses_counted": sorted(statuses),
        "basis": "Distinct collected reviews per feature; within-cohort shares; not customer prevalence.",
    }


def latest_snapshot_id(session: Session, target_model: str) -> uuid.UUID | None:
    return session.scalars(
        select(Theme.snapshot_id).where(Theme.target_model == target_model).order_by(Theme.id.desc()).limit(1)
    ).first()
