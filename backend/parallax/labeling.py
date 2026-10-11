"""Labeler: turns unlabeled feedback (social, competitor, unclassified BMW) into claims with the same
feature vocabulary BMW uses, so every channel lands in one signal count.

Not an agent swarm: a deterministic batch job (N records per call, a bounded worker pool, structured
outputs). Every quote is checked against the record text, feature keys must exist in the catalog, and
every claim is stored as `producer.method = "llm"` with model, prompt version and run id, review status
pending. `calibrate` labels BMW feedback blind and measures agreement with BMW's own VFC labels.
"""

import hashlib
import random
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from parallax.config import get_settings
from parallax.db import session_scope
from parallax.llm.client import LLMClient
from parallax.llm.gate import check_records
from parallax.llm.prompts import SAFETY
from parallax.models import Claim, Feature, Record, SimRun, Source

PROMPT_VERSION = "labeler-v2-fewshot"
FEWSHOT = 30
CHANNEL_SCOPES = {
    "social": {"app_store", "google_play", "youtube", "reddit", "forum"},
    "competitors": {"editorial_review", "forum", "manufacturer_website", "bmw_option_list", "other"},
    "bmw_unclassified": {"bmw_feedback"},
}
ClaimType = Literal["new_request", "discontinued", "competitor_parity", "defect", "praise", "other", "unclear"]


class LabeledClaim(BaseModel):
    feature_key: str | None = Field(description="Key from the catalog, or null if no catalog feature fits.")
    feature_label: str = Field(description="Short feature name (catalog label if a key was chosen).")
    claim_type: ClaimType = Field(description="defect = broken, unreliable or hard to use; new_request = wish for something "
                                              "missing; competitor_parity = 'X has it, BMW should too'; praise = positive.")
    quote: str = Field(description="Exact substring of the record text that supports this claim (original language).")
    summary: str = Field(description="One short English sentence.")
    competitors_mentioned: list[str]


class LabeledRecord(BaseModel):
    record_id: str
    claims: list[LabeledClaim] = Field(description="One claim per specific feature; empty list if nothing concrete.")


class LabelBatch(BaseModel):
    items: list[LabeledRecord]


def _catalog_text(features: list[Feature]) -> str:
    return "\n".join(f"{f.feature_key}: {f.label}" for f in sorted(features, key=lambda f: f.feature_key))


SYSTEM = """\
You label customer feedback about cars (BMW and competitors) for product planning. For each record, list
one claim per SPECIFIC feature the author talks about. Use the feature catalog keys below; choose the most
specific fitting key, or null with a short feature_label when nothing fits. A review can contain several
claims of different types. Vague text ("great car", emojis, app login spam) gets an empty list.
The quote must be copied exactly from the record (original language, no translation, no ellipsis).
{safety}
Match the granularity of BMW's own classification shown in the examples: prefer the key BMW would use
(general keys such as "seats" or "exterior_design" unless a more specific key clearly fits).
EXAMPLES OF BMW'S OWN LABELING (text -> keys)
{examples}
FEATURE CATALOG (key: label)
{catalog}"""


def _user(batch: list[Record]) -> str:
    lines = ["Records:"]
    for record in batch:
        text = (record.text_original or "").replace("\n", " ")[:1200]
        lines.append(f"- record_id={record.record_id} | markets={','.join(record.markets or [])} | text: {text}")
    return "\n".join(lines)


def _clean(value):
    """Postgres text/JSONB cannot store NUL characters, which some scraped texts contain."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    return value


def _claim_rows(batch: list[Record], out: LabelBatch, catalog: dict[str, Feature], model: str, run_id: uuid.UUID) -> tuple[list[dict], dict]:
    by_id = {r.record_id: r for r in batch}
    rows, stats = [], Counter()
    for item in out.items:
        record = by_id.get(item.record_id)
        if record is None:
            stats["unknown_record"] += 1
            continue
        text = record.text_original or ""
        seen = set()
        for claim in item.claims:
            quote = claim.quote.strip()
            if not quote or quote not in text:
                stats["quote_mismatch"] += 1
                continue
            key = claim.feature_key if claim.feature_key in catalog else None
            if claim.feature_key and key is None:
                stats["unknown_feature_key"] += 1
            dedup = (key or claim.feature_label.lower(), claim.claim_type)
            if dedup in seen:
                continue
            seen.add(dedup)
            digest = hashlib.sha256(f"{record.record_id}|{key}|{claim.claim_type}|{quote}".encode()).hexdigest()[:20]
            rows.append(_clean({
                "claim_id": f"llm-{digest}", "record_id": record.record_id, "feature_key": key,
                "feature_label": catalog[key].label if key else claim.feature_label, "claim_type": claim.claim_type,
                "summary": claim.summary, "quotes": [quote], "competitors_mentioned": claim.competitors_mentioned,
                "producer": {"method": "llm", "name": model, "version": PROMPT_VERSION, "run_id": str(run_id)},
                "review_status": "pending", "source_fields": {"labeler": "parallax"}, "derived": False,
            }))
            stats["claims"] += 1
        stats["records_labeled"] += 1
        if not item.claims:
            stats["records_without_claims"] += 1
    return rows, dict(stats)


def candidates(session: Session, scope: str, limit: int | None, min_chars: int = 15) -> list[str]:
    channels = set().union(*CHANNEL_SCOPES.values()) if scope == "all" else CHANNEL_SCOPES[scope]
    labeled = {rid for rid, in session.execute(select(Claim.record_id).where(Claim.derived.is_(False)))}
    derived = {rid for rid, in session.execute(select(Claim.record_id).where(Claim.derived.is_(True)))}
    rows = session.execute(
        select(Record.record_id, Record.text_original, Source.channel, Source.stream)
        .join(Source, Source.source_id == Record.source_id)
        .where(Record.record_kind == "feedback", Record.superseded_by.is_(None), Source.channel.in_(channels))
    ).all()
    ids = []
    for record_id, text, channel, stream in rows:
        if record_id in labeled or len((text or "").strip()) < min_chars:
            continue
        if stream == "bmw" and record_id in derived:
            continue  # BMW feedback already labeled by BMW; only unclassified rows need us
        if scope == "competitors" and stream != "competitors":
            continue
        if scope == "social" and stream != "social":
            continue
        ids.append(record_id)
    ids.sort(key=lambda rid: hashlib.sha256(rid.encode()).hexdigest())  # stable, spread over sources
    allowed = set(check_records(session, ids).allowed)
    ids = [rid for rid in ids if rid in allowed]
    return ids[:limit] if limit else ids


def failed_batches_of(session: Session, run_id: uuid.UUID) -> list[str]:
    """Record ids of labeling batches from an earlier run that produced no stored claim at all
    (a batch of ~40 texts without a single claim means its insert failed)."""
    from parallax.models import LLMCall

    calls = session.scalars(select(LLMCall).where(LLMCall.run_id == run_id, LLMCall.purpose == "labeling")).all()
    labeled = {rid for rid, in session.execute(select(Claim.record_id).where(Claim.derived.is_(False)))}
    retry: list[str] = []
    for call in calls:
        ids = call.input_record_ids or []
        if len(ids) >= 10 and not any(rid in labeled for rid in ids):
            retry.extend(ids)
    return retry


def _progress(run_id: uuid.UUID, **values) -> None:
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.progress = {**(run.progress or {}), **values}


def fewshot_examples(session: Session, exclude: set[str], n: int = FEWSHOT) -> str:
    """BMW feedback with BMW's VFC-derived labels, so our labels share BMW's granularity."""
    by_record: dict[str, set] = defaultdict(set)
    for claim in session.scalars(select(Claim).where(Claim.derived.is_(True), Claim.feature_key.is_not(None))):
        if claim.record_id not in exclude:
            by_record[claim.record_id].add(f"{claim.feature_key} ({claim.claim_type})")
    chosen = sorted(by_record, key=lambda rid: hashlib.sha256(f"fewshot|{rid}".encode()).hexdigest())[:n]
    texts = {r.record_id: (r.text_original or "") for r in session.scalars(select(Record).where(Record.record_id.in_(chosen)))}
    return "\n".join(f'- "{texts.get(rid, "")[:220]}" -> {", ".join(sorted(by_record[rid]))}' for rid in chosen if texts.get(rid))


def run_labeling(run_id: uuid.UUID, llm: LLMClient, record_ids: list[str], batch_size: int = 40, workers: int = 12,
                 persist: bool = True, exclude_from_examples: set[str] | None = None) -> dict:
    settings = get_settings()
    model = settings.model_fast
    with session_scope() as session:
        catalog = {f.feature_key: f for f in session.scalars(select(Feature))}
        examples = fewshot_examples(session, set(exclude_from_examples or ()) | set(record_ids))
    system = SYSTEM.format(safety=SAFETY, catalog=_catalog_text(list(catalog.values())), examples=examples or "(none)")
    batches = [record_ids[i:i + batch_size] for i in range(0, len(record_ids), batch_size)]
    llm.set_budget(run_id, len(batches) + 20)
    totals, done, outputs = Counter(), 0, {}

    def work(ids: list[str]) -> tuple[list[dict], dict]:
        with session_scope() as session:
            batch = list(session.scalars(select(Record).where(Record.record_id.in_(ids))))
            session.expunge_all()

        def mock(rng):
            return LabelBatch(items=[LabeledRecord(record_id=r.record_id, claims=[LabeledClaim(
                feature_key=rng.choice(list(catalog)), feature_label="mock", claim_type=rng.choice(["defect", "praise", "new_request"]),
                quote=(r.text_original or "")[:30], summary="[mock]", competitors_mentioned=[])]) for r in batch])

        out = llm.structured(LabelBatch, system=system, user=_user(batch), model=model, purpose="labeling",
                             prompt_version=PROMPT_VERSION, agent_id="agent:labeler", run_id=run_id,
                             input_record_ids=[r.record_id for r in batch], mock=mock, reasoning_effort="low")
        rows, stats = _claim_rows(batch, out, catalog, model, run_id)
        if persist and rows:
            with session_scope() as session:
                statement = insert(Claim).values(rows)
                session.execute(statement.on_conflict_do_nothing(index_elements=["claim_id"]))
        return rows, stats

    failed_ids: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, ids): ids for ids in batches}
        for future in as_completed(futures):
            try:
                rows, stats = future.result()
                totals.update(stats)
                for row in rows:
                    outputs.setdefault(row["record_id"], []).append(row)
            except Exception as error:  # keep going; failed batches are counted and can be retried
                totals["failed_batches"] += 1
                failed_ids.extend(futures[future])
                _progress(run_id, last_error=repr(error)[:300])
            done += 1
            if done % 5 == 0 or done == len(batches):
                _progress(run_id, stage="labeling", batches_done=done, batches_total=len(batches),
                          **{k: v for k, v in totals.items() if isinstance(v, int)})
    return {"records": len(record_ids), "batches": len(batches), **dict(totals), "failed_record_ids": failed_ids,
            "outputs": outputs}


def calibrate(run_id: uuid.UUID, llm: LLMClient, n: int = 300, workers: int = 16) -> dict:
    """Label BMW feedback blind (not stored) and compare with BMW's own VFC-derived claims."""
    with session_scope() as session:
        bmw = defaultdict(set)
        types = {}
        for claim in session.scalars(select(Claim).where(Claim.derived.is_(True), Claim.feature_key.is_not(None))):
            bmw[claim.record_id].add(claim.feature_key)
            types[(claim.record_id, claim.feature_key)] = claim.claim_type
        pool = sorted(bmw)
    random.Random(42).shuffle(pool)
    sample = pool[:n]
    result = run_labeling(run_id, llm, sample, persist=False, workers=workers, exclude_from_examples=set(sample))
    with session_scope() as session:
        area = {f.feature_key: f.area for f in session.scalars(select(Feature))}
    ours = {rid: {row["feature_key"] for row in rows if row["feature_key"]} for rid, rows in result["outputs"].items()}
    our_types = {(row["record_id"], row["feature_key"]): row["claim_type"] for rows in result["outputs"].values() for row in rows}
    hit = sum(len(bmw[rid] & ours.get(rid, set())) for rid in sample)
    bmw_total = sum(len(bmw[rid]) for rid in sample)
    our_total = sum(len(ours.get(rid, set())) for rid in sample)
    any_overlap = sum(bool(bmw[rid] & ours.get(rid, set())) for rid in sample)
    matched = [(rid, key) for rid in sample for key in bmw[rid] & ours.get(rid, set())]
    type_agree = sum(types[m] == our_types.get(m) for m in matched)
    bmw_areas = {rid: {area.get(k) for k in bmw[rid]} - {None} for rid in sample}
    our_areas = {rid: {area.get(k) for k in ours.get(rid, set())} - {None} for rid in sample}
    area_hit = sum(len(bmw_areas[rid] & our_areas[rid]) for rid in sample)
    area_bmw = sum(len(bmw_areas[rid]) for rid in sample)
    area_ours = sum(len(our_areas[rid]) for rid in sample)
    disagreements = [{"record_id": rid, "bmw": sorted(bmw[rid]), "ours": sorted(ours.get(rid, set()))}
                     for rid in sample if not bmw[rid] & ours.get(rid, set())][:15]
    return {
        "sample": len(sample),
        "recall_vs_bmw": round(hit / bmw_total, 3) if bmw_total else None,
        "precision_vs_bmw": round(hit / our_total, 3) if our_total else None,
        "records_with_at_least_one_match": round(any_overlap / len(sample), 3) if sample else None,
        "claim_type_agreement_on_matches": round(type_agree / len(matched), 3) if matched else None,
        "area_recall_vs_bmw": round(area_hit / area_bmw, 3) if area_bmw else None,
        "area_precision_vs_bmw": round(area_hit / area_ours, 3) if area_ours else None,
        "note": "BMW's VFC labels are one reference, not ground truth; our labeler may find extra valid features.",
        "examples_without_match": disagreements,
    }


def start(session: Session, kind: str, actor_id: str, options: dict) -> SimRun:
    from parallax.audit import record_event

    run = SimRun(kind=kind, status="queued", requirement_ids=[], requested_by=actor_id, config={"options": options,
                 "model": get_settings().model_fast, "prompt_version": PROMPT_VERSION}, progress={"stage": "queued"})
    session.add(run)
    session.flush()
    record_event(session, category="ai", actor_id=actor_id, action=f"{kind}.start", entity_type="sim_run",
                 entity_id=str(run.id), run_id=run.id, after=options)
    return run


def execute(run_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    from parallax.audit import record_event
    from parallax.llm.client import get_llm

    llm = get_llm()
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.started_at = "running", datetime.now(timezone.utc)
        kind, options, actor = run.kind, run.config.get("options", {}), run.requested_by
    try:
        workers = max(1, min(64, int(options.get("workers", 24))))
        if kind == "calibration":
            summary = calibrate(run_id, llm, int(options.get("n", 300)), workers)
        else:
            with session_scope() as session:
                if options.get("retry_run_id"):
                    ids = failed_batches_of(session, uuid.UUID(options["retry_run_id"]))
                else:
                    ids = options.get("record_ids") or candidates(session, options.get("scope", "social"), options.get("limit"))
            _progress(run_id, stage="labeling", candidates=len(ids))
            summary = run_labeling(run_id, llm, ids, workers=workers)
            summary.pop("outputs", None)
        status, error = ("partial" if summary.get("failed_batches") else "completed"), None
    except Exception as exc:
        summary, status, error = {}, "failed", repr(exc)[:2000]
    summary.pop("outputs", None)
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.error, run.finished_at = status, error, datetime.now(timezone.utc)
        run.progress = {**(run.progress or {}), "stage": "done", "result": summary}
        record_event(session, category="ai", actor_id=actor, action=f"{kind}.{status}", entity_type="sim_run",
                     entity_id=str(run_id), run_id=run_id, after={k: v for k, v in summary.items() if k != "examples_without_match"},
                     rationale=error)
