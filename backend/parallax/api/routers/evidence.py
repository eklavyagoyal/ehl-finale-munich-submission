"""Evidence: ingest, sources, records, claims, coverage, themes."""

import tempfile
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from parallax import decisions, ingest, themes
from parallax.api.common import actor, human_actor, not_found, row
from parallax.config import get_settings
from parallax.db import get_session
from parallax.llm.gate import check_records
from parallax.provenance import source_summary
from parallax.models import Claim, IngestRun, Record, Source, Theme

router = APIRouter(prefix="/api", tags=["evidence"])


class IngestIn(BaseModel):
    kind: Literal["batches", "packet"] = "batches"
    path: str
    research_root: str | None = None


@router.post("/ingest", summary="Import research-contract batches or a context packet")
def run_ingest(body: IngestIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    path = Path(body.path).expanduser()
    if not path.exists():
        raise HTTPException(400, f"{path} does not exist")
    try:
        if body.kind == "packet":
            run = ingest.import_packet(session, path, who)
        else:
            research_root = Path(body.research_root).expanduser() if body.research_root else get_settings().research_root
            run = ingest.import_batches(session, path, research_root, who)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return row(run)


@router.post("/ingest/upload", summary="Upload a zip of a research folder (schema.json, catalog/, decision-model.json, batches/)")
def upload_ingest(file: UploadFile = File(...), session: Session = Depends(get_session), who: str = Depends(actor)):
    """How data reaches a deployed backend: `python -m parallax.cli push-research ../research --url ... --token ...`."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        archive = root / "upload.zip"
        with archive.open("wb") as out:
            while chunk := file.file.read(1 << 20):
                out.write(chunk)
        extract = root / "x"
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                target = (extract / member.filename).resolve()
                if not target.is_relative_to(extract.resolve()):
                    raise HTTPException(400, "zip contains paths outside the archive")
            zf.extractall(extract)
        schemas = sorted(extract.rglob("schema.json"), key=lambda p: len(p.parts))
        if not schemas:
            raise HTTPException(422, "zip must contain the research contract (schema.json, catalog/, batches/)")
        research_root = schemas[0].parent
        batch_root = research_root / "batches" if (research_root / "batches").exists() else research_root
        try:
            run = ingest.import_batches(session, batch_root, research_root, who)
        except ValueError as error:
            raise HTTPException(422, str(error))
        run.input_path = f"upload:{file.filename}"
        return row(run)


@router.get("/ingest-runs")
def ingest_runs(session: Session = Depends(get_session)):
    return [row(r) for r in session.scalars(select(IngestRun).order_by(IngestRun.created_at.desc())).all()]


@router.get("/sources")
def list_sources(stream: str | None = None, channel: str | None = None, review_status: str | None = None,
                 session: Session = Depends(get_session)):
    query = select(Source)
    if stream:
        query = query.where(Source.stream == stream)
    if channel:
        query = query.where(Source.channel == channel)
    if review_status:
        query = query.where(Source.review_status == review_status)
    return [row(s) for s in session.scalars(query.order_by(Source.source_id)).all()]


@router.get("/sources/{source_id}", summary="One source with provenance, sampling, permissions and claim counts")
def get_source(source_id: str, session: Session = Depends(get_session)):
    source = session.get(Source, source_id)
    if source is None:
        raise not_found("source", source_id)
    records = session.scalar(select(func.count()).select_from(Record).where(Record.source_id == source_id,
                                                                           Record.superseded_by.is_(None)))
    claim_rows = session.execute(
        select(Claim.review_status, Claim.derived, func.count()).join(Record, Record.record_id == Claim.record_id)
        .where(Record.source_id == source_id).group_by(Claim.review_status, Claim.derived)
    ).all()
    from collections import Counter

    producer_counts = Counter(
        (p.get("method"), p.get("name")) for p in session.scalars(
            select(Claim.producer).join(Record, Record.record_id == Claim.record_id).where(Record.source_id == source_id))
    )
    producers = [(m, nm, n) for (m, nm), n in producer_counts.most_common()]
    return {
        "source": row(source), "summary": source_summary(source), "records": records,
        "claims": [{"review_status": s, "derived_from_bmw_labels": d, "count": n} for s, d, n in claim_rows],
        "claim_producers": [{"method": m, "name": nm, "count": n} for m, nm, n in producers],
    }


class SourceReviewIn(BaseModel):
    review_status: Literal["pending", "accepted", "rejected"]
    external_llm: bool | None
    notes: str


@router.post("/sources/{source_id}/review", summary="Evidence acceptance (separate from requirement approval)")
def review_source(source_id: str, body: SourceReviewIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    source = session.get(Source, source_id)
    if source is None:
        raise not_found("source", source_id)
    decisions.review_source(session, source, review_status=body.review_status, external_llm=body.external_llm,
                            notes=body.notes, actor_id=human_actor(who))
    return row(source)


class BulkReviewIn(SourceReviewIn):
    stream: str | None = None
    channel: str | None = None
    dataset_key: str | None = None
    include_claims: bool = False


@router.post("/sources/review-bulk")
def review_sources_bulk(body: BulkReviewIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    if not (body.stream or body.channel or body.dataset_key):
        raise HTTPException(400, "filter by stream, channel or dataset_key")
    return decisions.review_sources_bulk(session, stream=body.stream, channel=body.channel, dataset_key=body.dataset_key,
                                         review_status=body.review_status, external_llm=body.external_llm,
                                         notes=body.notes, actor_id=human_actor(who), include_claims=body.include_claims)


@router.get("/records")
def list_records(feature_key: str | None = None, market: str | None = None, channel: str | None = None,
                 kind: str | None = None, q: str | None = None, ids: list[str] | None = Query(default=None),
                 limit: int = Query(50, le=500), offset: int = 0, session: Session = Depends(get_session)):
    query = select(Record, Source.channel).join(Source, Source.source_id == Record.source_id).where(Record.superseded_by.is_(None))
    if ids:
        query = query.where(Record.record_id.in_(ids))
    if feature_key:
        query = query.where(Record.record_id.in_(select(Claim.record_id).where(Claim.feature_key == feature_key)))
    if market:
        query = query.where(Record.markets.contains([market]))  # uses the GIN index
    if channel:
        query = query.where(Source.channel == channel)
    if kind:
        query = query.where(Record.record_kind == kind)
    if q:
        query = query.where(or_(Record.text_original.ilike(f"%{q}%"), Record.translation_en.ilike(f"%{q}%")))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(Record.record_id).limit(limit).offset(offset)).all()
    return {"total": total, "items": [{**row(r), "channel": ch} for r, ch in rows]}


@router.get("/records/{record_id}")
def get_record(record_id: str, session: Session = Depends(get_session)):
    record = session.get(Record, record_id)
    if record is None:
        raise not_found("record", record_id)
    source = session.get(Source, record.source_id)
    claims = session.scalars(select(Claim).where(Claim.record_id == record_id)).all()
    gate = check_records(session, [record_id])
    return {"record": row(record), "source": row(source), "claims": [row(c) for c in claims],
            "llm_gate": gate.as_meta()}


@router.get("/claims")
def list_claims(feature_key: str | None = None, claim_type: str | None = None, review_status: str | None = None,
                derived: bool | None = None, limit: int = Query(100, le=1000), offset: int = 0,
                session: Session = Depends(get_session)):
    query = select(Claim)
    if feature_key:
        query = query.where(Claim.feature_key == feature_key)
    if claim_type:
        query = query.where(Claim.claim_type == claim_type)
    if review_status:
        query = query.where(Claim.review_status == review_status)
    if derived is not None:
        query = query.where(Claim.derived.is_(derived))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(query.order_by(Claim.claim_id).limit(limit).offset(offset)).all()
    return {"total": total, "items": [row(c) for c in items]}


class ClaimReviewIn(BaseModel):
    review_status: Literal["pending", "accepted", "rejected"]
    notes: str


@router.post("/claims/{claim_id}/review")
def review_claim(claim_id: str, body: ClaimReviewIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    claim = session.get(Claim, claim_id)
    if claim is None:
        raise not_found("claim", claim_id)
    decisions.review_claim(session, claim, body.review_status, body.notes, human_actor(who))
    return row(claim)


@router.get("/coverage", summary="What evidence exists, by channel / market / review state / LLM permission")
def coverage(session: Session = Depends(get_session)):
    by_channel = session.execute(
        select(Source.stream, Source.channel, Source.review_status, Source.external_llm, func.count(Record.record_id))
        .join(Record, Record.source_id == Source.source_id).where(Record.superseded_by.is_(None))
        .group_by(Source.stream, Source.channel, Source.review_status, Source.external_llm)
    ).all()
    markets = session.execute(
        select(func.unnest(Record.markets).label("market"), func.count()).where(Record.superseded_by.is_(None))
        .group_by("market").order_by(func.count().desc())
    ).all()
    claims = session.execute(select(Claim.review_status, Claim.derived, func.count()).group_by(Claim.review_status, Claim.derived)).all()
    market = func.unnest(Record.markets).label("market")
    cross = session.execute(
        select(Source.stream, Source.channel, market, func.count())
        .join(Record, Record.source_id == Source.source_id).where(Record.superseded_by.is_(None))
        .group_by(Source.stream, Source.channel, market)
    ).all()
    return {
        "records_by_channel": [{"stream": s, "channel": c, "review_status": r, "external_llm": e, "records": n}
                               for s, c, r, e, n in by_channel],
        "records_by_market": [{"market": m, "records": n} for m, n in markets],
        "claims": [{"review_status": r, "derived_from_bmw_labels": d, "claims": n} for r, d, n in claims],
        # Channel x market matrix in one query, so clients never fan out one request per cell.
        "records_by_channel_market": [{"stream": s, "channel": c, "market": m, "records": n} for s, c, m, n in cross],
        "llm_rule": "Only accepted sources with external_llm == true reach an external model.",
    }


class ThemeBuildIn(BaseModel):
    target_model: str | None = None
    include_examples: bool = False
    include_pending_claims: bool = False


@router.post("/themes/build", summary="Recompute deterministic theme signals from current evidence")
def build_themes(body: ThemeBuildIn, session: Session = Depends(get_session), who: str = Depends(actor)):
    from parallax.audit import record_event

    settings = get_settings()
    result = themes.build_themes(session, target_model=body.target_model or settings.target_model,
                                 include_examples=body.include_examples,
                                 allow_unreviewed_for_llm=settings.allow_unreviewed_evidence_for_llm,
                                 include_pending_claims=body.include_pending_claims)
    record_event(session, category="system", actor_id=who, action="themes.build", entity_type="theme_snapshot",
                 entity_id=result["snapshot_id"], after=result)
    return result


@router.get("/themes")
def list_themes(market: str | None = Query(None, description="US, EU, CN, RoW, or omit for pooled"),
                area: str | None = None, min_demand: float = 0, snapshot_id: str | None = None,
                limit: int = Query(100, le=1000), session: Session = Depends(get_session)):
    settings = get_settings()
    snap = snapshot_id or themes.latest_snapshot_id(session, settings.target_model)
    if snap is None:
        return {"snapshot_id": None, "items": []}
    query = select(Theme).where(Theme.snapshot_id == snap, Theme.demand_score >= min_demand)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    if area:
        query = query.where(Theme.area == area)
    items = session.scalars(query.order_by(Theme.demand_score.desc(), Theme.mention_review_count.desc()).limit(limit)).all()
    return {"snapshot_id": str(snap), "items": [row(t, exclude={"record_ids"}) | {"record_count": len(t.record_ids)} for t in items]}


@router.get("/themes/{theme_id}")
def get_theme(theme_id: int, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    if theme is None:
        raise not_found("theme", theme_id)
    return row(theme)
