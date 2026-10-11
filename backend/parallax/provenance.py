"""Provenance summaries: where a piece of evidence comes from and who interpreted it."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.models import Claim, Source


def source_summary(source: Source) -> dict:
    return {
        "source_id": source.source_id, "stream": source.stream, "channel": source.channel, "title": source.title,
        "collector": source.collector, "collected_at": source.collected_at.isoformat() if source.collected_at else None,
        "dataset_key": source.dataset_key, "origin": source.provenance.get("origin"),
        "verification": source.provenance.get("verification"), "review_status": source.review_status,
        "external_llm": source.external_llm, "is_example": source.is_example,
        "sampling_method": source.sampling.get("method"), "sampling_complete": source.sampling.get("complete"),
        "limitations": source.sampling.get("limitations", []),
    }


def claim_summary(claim: Claim) -> dict:
    producer = claim.producer or {}
    return {
        "claim_id": claim.claim_id, "feature_key": claim.feature_key, "feature_label": claim.feature_label,
        "claim_type": claim.claim_type, "summary": claim.summary, "quotes": claim.quotes,
        "review_status": claim.review_status, "derived_from_bmw_labels": claim.derived,
        "producer_method": producer.get("method"), "producer_name": producer.get("name"),
        "producer_version": producer.get("version"), "producer_run_id": producer.get("run_id"),
    }


def sources_for(session: Session, source_ids: set[str]) -> dict[str, dict]:
    if not source_ids:
        return {}
    return {s.source_id: source_summary(s) for s in session.scalars(select(Source).where(Source.source_id.in_(list(source_ids))))}


def claims_for(session: Session, record_ids: set[str], feature_key: str | None = None) -> dict[str, list[dict]]:
    if not record_ids:
        return {}
    query = select(Claim).where(Claim.record_id.in_(list(record_ids)))
    if feature_key:
        query = query.where(Claim.feature_key == feature_key)
    out: dict[str, list[dict]] = {}
    for claim in session.scalars(query):
        out.setdefault(claim.record_id, []).append(claim_summary(claim))
    return out
