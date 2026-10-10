"""Import research contract v1 data into Postgres.

Two inputs are accepted:
  * a batch root (research/batches or any subfolder), validated with the contract validator
  * a context packet (outputs/research/<run>/context.json) built by build_research_context.py

Imports are idempotent upserts keyed by the contract IDs. Review status and permissions are
copied as delivered; changing them later goes through the evidence-review API (audited).
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from parallax.audit import record_event
from parallax.contract import ContractPaths, LoadedBatches, json_file, load_batches
from parallax.models import Claim, Entity, Feature, IngestRun, PolicyVersion, Record, Source
from parallax.policy import default_policy_document, publish_policy

CHUNK = 1000


def _chunks(rows: list[dict], size: int = CHUNK) -> Iterable[list[dict]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _upsert(session: Session, model, rows: list[dict], key: str) -> None:
    for chunk in _chunks(rows):
        statement = insert(model).values(chunk)
        updatable = {c: statement.excluded[c] for c in chunk[0] if c != key}
        session.execute(statement.on_conflict_do_update(index_elements=[key], set_=updatable))


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def source_row(source: dict, ingest_run_id) -> dict:
    return {
        "source_id": source["source_id"],
        "dataset_key": source["dataset_key"],
        "stream": source["stream"],
        "channel": source["channel"],
        "title": source["title"],
        "locator": source["locator"],
        "collected_at": _parse_dt(source["collected_at"]),
        "collector": source["collector"],
        "is_example": source["is_example"],
        "normalized_record_count": source["normalized_record_count"],
        "sampling": source["sampling"],
        "provenance": source["provenance"],
        "artifact": source["artifact"],
        "export_permissions": source["export_permissions"],
        "external_llm": source["export_permissions"]["external_llm"],
        "review_status": source["review_status"],
        "ingest_run_id": ingest_run_id,
    }


def record_row(record: dict) -> dict:
    return {
        "record_id": record["record_id"],
        "source_id": record["source_id"],
        "dedup_key": record["dedup_key"],
        "record_kind": record["record_kind"],
        "locator": record["locator"],
        "content_date": record["content_date"],
        "content_datetime": _parse_dt(record["content_datetime"]),
        "subject_ids": record["subject_ids"],
        "markets": record["markets"],
        "text_original": record["text_original"],
        "language": record["language"],
        "translation_en": record["translation_en"],
        "metric": record["metric"],
        "availability": record["availability"],
        "source_fields": record["source_fields"],
        "superseded_by": None,
    }


def claim_row(claim: dict, derived: bool = False) -> dict:
    return {
        "claim_id": claim["claim_id"],
        "record_id": claim["record_id"],
        "feature_key": claim["feature_key"],
        "feature_label": claim["feature_label"],
        "claim_type": claim["claim_type"],
        "summary": claim["summary"],
        "quotes": claim["quotes"],
        "competitors_mentioned": claim["competitors_mentioned"],
        "producer": claim["producer"],
        "review_status": claim["review_status"],
        "source_fields": claim["source_fields"],
        "derived": derived,
    }


# ---------------------------------------------------------------- BMW VFC labels -> derived claims

FEEDBACK_TYPE_TO_CLAIM = {"likes": "praise", "wants": "new_request", "defect": "defect", "difficult to use": "other"}


def _norm(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def derive_claims_from_labels(records: dict[str, dict], claimed_record_ids: set[str], features: list[dict]) -> list[dict]:
    """BMW feedback arrives pre-classified (VFC level2 topic + Feedback Type). When a feedback record
    has no contract claim, map its VFC topic to the feature catalog and emit a derived, pending claim.

    The pairing follows label order: each "Vfc level2 Name" opens a group; "Feedback Type" and
    "Vfc level3 Name" attach to the current group.
    """
    by_label = {_norm(f.get("label", "")): f["feature_key"] for f in features}
    derived = []
    for record in records.values():
        if record["record_kind"] != "feedback" or record["record_id"] in claimed_record_ids:
            continue
        labels = (record.get("source_fields") or {}).get("original_labels") or []
        groups: list[dict] = []
        pending_type = None
        for label in labels:
            name, value = label.get("name", ""), label.get("value")
            if name == "Vfc level2 Name":
                groups.append({"topic": value, "type": pending_type, "nature": None})
                pending_type = None
            elif name == "Feedback Type":
                if groups and groups[-1]["type"] is None:
                    groups[-1]["type"] = value
                else:
                    pending_type = value
            elif name == "Vfc level3 Name" and groups:
                groups[-1]["nature"] = value
        seen: set[str] = set()
        text = record["text_original"] or ""
        for group in groups:
            topic = group["topic"]
            feature_key = by_label.get(_norm(topic)) if topic else None
            if not feature_key or feature_key in seen or not text:
                continue
            seen.add(feature_key)
            feedback_type = (group["type"] or "").strip()
            claim_type = FEEDBACK_TYPE_TO_CLAIM.get(feedback_type.lower(), "unclear")
            digest = hashlib.sha256(f"{record['record_id']}|{feature_key}".encode()).hexdigest()[:16]
            derived.append({
                "claim_id": f"vfc-{digest}",
                "record_id": record["record_id"],
                "feature_key": feature_key,
                "feature_label": topic,
                "claim_type": claim_type,
                "summary": f"BMW VFC classification: {topic} / {group['nature'] or 'n/a'} ({feedback_type or 'no type'}).",
                "quotes": [text[:400]],
                "competitors_mentioned": [],
                "producer": {"method": "provided_unknown", "name": "BMW VFC classification", "version": None, "run_id": None},
                "review_status": "pending",
                "source_fields": {"FeedbackType": feedback_type or None, "VfcLevel3": group["nature"]},
            })
    return derived


# ---------------------------------------------------------------- import


def _mark_superseded(session: Session) -> int:
    """Latest snapshot per (dataset_key, dedup_key) wins, by source collection time."""
    rows = session.execute(
        select(Record.record_id, Record.dedup_key, Source.dataset_key, Source.collected_at)
        .join(Source, Source.source_id == Record.source_id)
    ).all()
    latest: dict[tuple[str, str], tuple] = {}
    for record_id, dedup_key, dataset_key, collected_at in rows:
        key = (dataset_key, dedup_key)
        if key not in latest or (collected_at, record_id) > (latest[key][1], latest[key][0]):
            latest[key] = (record_id, collected_at)
    session.execute(update(Record).values(superseded_by=None))
    superseded = 0
    for record_id, dedup_key, dataset_key, _ in rows:
        winner = latest[(dataset_key, dedup_key)][0]
        if winner != record_id:
            session.execute(update(Record).where(Record.record_id == record_id).values(superseded_by=winner))
            superseded += 1
    return superseded


def import_documents(session: Session, data: LoadedBatches, *, kind: str, input_path: str, actor_id: str,
                     decision_model: dict | None) -> IngestRun:
    run = IngestRun(kind=kind, input_path=input_path, input_sha256=data.fingerprints, actor_id=actor_id)
    session.add(run)
    session.flush()

    features = data.catalogs["features"]["features"]
    entities = data.catalogs["entities"]["entities"]
    if features:
        _upsert(session, Feature, [
            {"feature_key": f["feature_key"], "label": f.get("label", f["feature_key"]), "area": f.get("area"),
             "origin": f.get("origin")} for f in features
        ], "feature_key")
    if entities:
        _upsert(session, Entity, [
            {"entity_id": e["entity_id"], "type": e["type"], "label": e["label"], "target": bool(e.get("target")),
             "members": e.get("members", [])} for e in entities
        ], "entity_id")
    if data.sources:
        _upsert(session, Source, [source_row(s, run.id) for s in data.sources.values()], "source_id")
    if data.records:
        _upsert(session, Record, [record_row(r) for r in data.records.values()], "record_id")
    if data.claims:
        _upsert(session, Claim, [claim_row(c) for c in data.claims.values()], "claim_id")

    claimed = set(session.scalars(select(Claim.record_id).where(Claim.derived.is_(False))).all())
    derived = derive_claims_from_labels(data.records, claimed, features)
    if derived:
        _upsert(session, Claim, [claim_row(c, derived=True) for c in derived], "claim_id")
    superseded = _mark_superseded(session)

    run.counts = {
        "sources": len(data.sources), "records": len(data.records), "claims": len(data.claims),
        "derived_claims": len(derived), "features": len(features), "entities": len(entities),
        "superseded_records": superseded,
    }
    if decision_model is not None:
        current = session.scalars(select(PolicyVersion).where(PolicyVersion.active.is_(True))).first()
        if current is None or current.document.get("decision_model") != decision_model:
            document = default_policy_document(decision_model)
            if current is not None:
                document["parallax"] = current.document.get("parallax", document["parallax"])
            publish_policy(session, document, actor_id, f"decision-model.json imported from {input_path}")
    record_event(
        session, category="evidence", actor_id=actor_id, action="evidence.import", entity_type="ingest_run",
        entity_id=str(run.id), after=run.counts, meta={"kind": kind, "input_path": input_path},
    )
    return run


def import_batches(session: Session, batch_root: Path, research_root: Path, actor_id: str) -> IngestRun:
    paths = ContractPaths(research_root)
    data = load_batches(batch_root, paths)
    decision_model = json_file(paths.decision_model) if paths.decision_model.exists() else None
    return import_documents(session, data, kind="batches", input_path=str(batch_root), actor_id=actor_id,
                            decision_model=decision_model)


def import_packet(session: Session, packet_path: Path, actor_id: str) -> IngestRun:
    """A packet is already validated and filtered by the research exporter."""
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    data = LoadedBatches(
        sources={s["source_id"]: s for s in packet["sources"]},
        records={r["record_id"]: r for r in packet["records"]},
        claims={c["claim_id"]: c for c in packet["claims"]},
        catalogs=packet["catalogs"],
        fingerprints=packet["run_manifest"]["input_sha256"],
    )
    run = import_documents(session, data, kind="packet", input_path=str(packet_path), actor_id=actor_id,
                           decision_model=packet.get("decision_policy"))
    run.warnings = [{"packet_run_id": packet["run_manifest"]["run_id"], "coverage": packet.get("coverage", {})}]
    return run
