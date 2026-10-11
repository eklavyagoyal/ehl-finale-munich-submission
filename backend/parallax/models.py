"""Postgres schema.

Five layers:
  evidence     sources / records / claims / catalogs, exactly as the research contract v1 ships them
  themes       deterministic per-feature, per-market signal counts computed from the evidence
  requirements the eight brief fields, versioned, with linked evidence, criterion ratings and gates
  simulation   agents (personas, departments, judges), runs, steps and every agent output
  governance   PM decisions, append-only audit events, LLM call log, policy versions, lessons
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from parallax.db import Base

TS = DateTime(timezone=True)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# --------------------------------------------------------------------------- evidence


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(40))  # batches | packet
    input_path: Mapped[str] = mapped_column(Text)
    input_sha256: Mapped[dict] = mapped_column(JSONB, default=dict)
    counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Source(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(240), index=True)
    stream: Mapped[str] = mapped_column(String(40))
    channel: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(TS)
    collector: Mapped[str] = mapped_column(Text)
    is_example: Mapped[bool] = mapped_column(Boolean)
    normalized_record_count: Mapped[int] = mapped_column(Integer)
    sampling: Mapped[dict] = mapped_column(JSONB)
    provenance: Mapped[dict] = mapped_column(JSONB)
    artifact: Mapped[dict] = mapped_column(JSONB)
    export_permissions: Mapped[dict] = mapped_column(JSONB)
    # Mirrors export_permissions.external_llm so the LLM gate can filter in SQL.
    external_llm: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), index=True)
    ingest_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingest_runs.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (
        Index("ix_records_subjects", "subject_ids", postgresql_using="gin"),
        Index("ix_records_markets", "markets", postgresql_using="gin"),
    )

    record_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), index=True)
    dedup_key: Mapped[str] = mapped_column(String(240), index=True)
    record_kind: Mapped[str] = mapped_column(String(40), index=True)
    locator: Mapped[dict] = mapped_column(JSONB)
    content_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_datetime: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    subject_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    markets: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    text_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    translation_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    availability: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Set when a later snapshot of the same (dataset_key, dedup_key) observation exists.
    superseded_by: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("records.record_id"), index=True)
    feature_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    feature_label: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    quotes: Mapped[list] = mapped_column(JSONB)
    competitors_mentioned: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    producer: Mapped[dict] = mapped_column(JSONB)
    review_status: Mapped[str] = mapped_column(String(20), index=True)
    source_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    # True for claims Parallax derived from BMW's own VFC labels (no contract claim existed).
    derived: Mapped[bool] = mapped_column(Boolean, default=False)


class RecordTriage(Base):
    """Per online review: the columns BMW's feedback export has per row (vehicle, engine type), plus author and
    relevance. Produced by parallax.triage; one row per record, latest prompt version wins."""

    __tablename__ = "record_triage"

    record_id: Mapped[str] = mapped_column(ForeignKey("records.record_id"), primary_key=True)
    target_model: Mapped[str] = mapped_column(String(60))
    vehicle: Mapped[str] = mapped_column(String(30), index=True)
    engine: Mapped[str] = mapped_column(String(20))
    author: Mapped[str] = mapped_column(String(20), index=True)
    relevant: Mapped[bool] = mapped_column(Boolean, index=True)
    reason: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(20))  # llm | rule
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(40))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Feature(Base):
    __tablename__ = "features"

    feature_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origin: Mapped[str | None] = mapped_column(Text, nullable=True)


class Entity(Base):
    __tablename__ = "entities"

    entity_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(Text)
    target: Mapped[bool] = mapped_column(Boolean, default=False)
    members: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


# --------------------------------------------------------------------------- themes


class Theme(Base):
    """Deterministic signal for one feature in one market (market NULL = all markets pooled)."""

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    target_model: Mapped[str] = mapped_column(String(60))
    market: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    feature_key: Mapped[str] = mapped_column(String(200), index=True)
    label: Mapped[str] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mention_review_count: Mapped[int] = mapped_column(Integer)
    # Reviews whose subject is the target model itself (vs. combined group, brand-wide or unresolved).
    direct_review_count: Mapped[int] = mapped_column(Integer)
    pending_claim_review_count: Mapped[int] = mapped_column(Integer, default=0)
    # Reviews about competitor models: competitive context, never counted as target-model demand.
    competitor_review_count: Mapped[int] = mapped_column(Integer, default=0)
    competitor_record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    # Brand-wide or unresolved feedback (e.g. My BMW app reviews): context, never target-model demand.
    brand_review_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    need_review_count: Mapped[int] = mapped_column(Integer, default=0)  # distinct reviews with a pain or a wish
    owner_review_count: Mapped[int] = mapped_column(Integer, default=0)  # BMW feedback + online reviews triaged as owner
    request_review_count: Mapped[int] = mapped_column(Integer)
    pain_review_count: Mapped[int] = mapped_column(Integer)
    praise_review_count: Mapped[int] = mapped_column(Integer)
    counts_by_claim_type: Mapped[dict] = mapped_column(JSONB)
    channels: Mapped[list[str]] = mapped_column(ARRAY(Text))
    cohorts: Mapped[list] = mapped_column(JSONB)
    max_cohort_share: Mapped[float] = mapped_column(Float)
    record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text))
    llm_eligible_record_count: Mapped[int] = mapped_column(Integer)
    derived_from_labels: Mapped[int] = mapped_column(Integer, default=0)
    demand_score: Mapped[float] = mapped_column(Float)
    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Finding(Base):
    """A concrete customer problem/wish/praise inside a theme (e.g. CarPlay: "drops during the drive").
    The LLM proposes the grouping and assigns reviews; counts are computed in code from the assignments."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_model: Mapped[str] = mapped_column(String(60))
    market: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    feature_key: Mapped[str] = mapped_column(String(200), index=True)
    theme_label: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))  # pain | request | praise | mixed
    record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text))
    review_count: Mapped[int] = mapped_column(Integer)
    share_of_theme: Mapped[float] = mapped_column(Float)
    quotes: Mapped[list] = mapped_column(JSONB)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


# --------------------------------------------------------------------------- requirements


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # REQ-G60-0001
    target_model: Mapped[str] = mapped_column(String(60))
    market: Mapped[str | None] = mapped_column(String(10), nullable=True)
    feature_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    theme_id: Mapped[int | None] = mapped_column(ForeignKey("themes.id"), nullable=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    customer_problem: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[list] = mapped_column(JSONB, default=list)
    evidence_level: Mapped[str] = mapped_column(String(40), default="unassessed")
    evidence_level_explanation: Mapped[str] = mapped_column(Text, default="")
    assumptions: Mapped[list] = mapped_column(JSONB, default=list)
    uncertainties: Mapped[list] = mapped_column(JSONB, default=list)
    planning_horizon: Mapped[str] = mapped_column(String(60), default="successor_vehicle_3_to_5_years")
    status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)
    priority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    prioritization_rationale: Mapped[str] = mapped_column(Text, default="")
    suggested_next_action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Structuring (classic step 4): AI proposes a Kano class and a benchmark target; the PM confirms or edits.
    kano_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kano_rationale: Mapped[str] = mapped_column(Text, default="")
    benchmark_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(120))
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class RequirementVersion(Base):
    __tablename__ = "requirement_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[str] = mapped_column(String(120))
    change_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class RequirementEvidence(Base):
    __tablename__ = "requirement_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("records.record_id"))
    claim_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    relation: Mapped[str] = mapped_column(String(20))  # supporting | contradicting | context
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    added_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class CriterionRating(Base):
    """One rater's view on one decision-model criterion. Several ratings per criterion are normal."""

    __tablename__ = "criterion_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    criterion: Mapped[str] = mapped_column(String(40))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # observed | estimated | simulated | assumed
    rater_type: Mapped[str] = mapped_column(String(20))  # code | persona | department | research | pm
    rater_id: Mapped[str] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class GateState(Base):
    """Gate history; the latest row per (requirement, gate) is the current state."""

    __tablename__ = "gate_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    gate: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(String(10))  # pass | fail | unknown
    owner: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text, default="")
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


# --------------------------------------------------------------------------- agents & simulation


class Agent(Base):
    """Registry of every simulated actor: market personas, departments, judges, workers."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)  # persona:us-bev-early-adopter
    kind: Mapped[str] = mapped_column(String(30), index=True)
    display_name: Mapped[str] = mapped_column(Text)
    market: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vehicle: Mapped[str | None] = mapped_column(String(60), nullable=True)
    powertrain: Mapped[str | None] = mapped_column(String(20), nullable=True)
    segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    spec: Mapped[dict] = mapped_column(JSONB)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    details_status: Mapped[str] = mapped_column(String(20), default="skeleton")
    validation_status: Mapped[str] = mapped_column(String(30), default="not_validated")
    validation_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    spec: Mapped[dict] = mapped_column(JSONB)
    actor_id: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class SimRun(Base):
    __tablename__ = "sim_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(30))  # simulation | validation | generation | followup
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    requirement_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    challenge_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(120))
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class SimStep(Base):
    __tablename__ = "sim_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    requirement_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stage: Mapped[str] = mapped_column(String(30))
    agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class PersonaResponse(Base):
    __tablename__ = "persona_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    agent_version: Mapped[int] = mapped_column(Integer)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    engine: Mapped[str] = mapped_column(String(20))
    response_text: Mapped[str] = mapped_column(Text)
    stance: Mapped[str] = mapped_column(String(20))
    ssr_distribution: Mapped[list[float]] = mapped_column(ARRAY(Float))
    ssr_mean: Mapped[float] = mapped_column(Float)
    importance_0_5: Mapped[float] = mapped_column(Float)
    market_fit_0_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Forced trade-off: share of a fixed 100-point budget (vs. other proposals and "keep the price down").
    budget_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)  # must_have | nice_to_have | dont_care | against
    concerns: Mapped[list] = mapped_column(JSONB, default=list)
    info_requests: Mapped[list] = mapped_column(JSONB, default=list)
    grounding_record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class DepartmentMemo(Base):
    __tablename__ = "department_memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    agent_version: Mapped[int] = mapped_column(Integer)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    stance: Mapped[str] = mapped_column(String(20))
    memo: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class ResearchRequest(Base):
    __tablename__ = "research_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    requested_by: Mapped[str] = mapped_column(String(120))
    question: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    verification: Mapped[dict] = mapped_column(JSONB, default=dict)
    verdict: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class Synthesis(Base):
    __tablename__ = "syntheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    content: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(80))
    vote: Mapped[str] = mapped_column(String(20))  # approve | reject | investigate | defer
    rationale: Mapped[str] = mapped_column(Text)
    key_points: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Recommendation(Base):
    """The panel's recommendation to the PM. Never a decision."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    recommendation: Mapped[str] = mapped_column(String(20))
    tally: Mapped[dict] = mapped_column(JSONB)
    minority_report: Mapped[list] = mapped_column(JSONB, default=list)
    # Challenger agent: the strongest case against the panel's outcome (advisory, shown to the PM).
    challenge: Mapped[dict] = mapped_column(JSONB, default=dict)
    score_snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


# --------------------------------------------------------------------------- governance


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document: Mapped[dict] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[str] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class PMDecision(Base):
    __tablename__ = "pm_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    action: Mapped[str] = mapped_column(String(20))  # approve | reject | challenge | defer
    rationale: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(String(120))
    requirement_version: Mapped[int] = mapped_column(Integer)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("recommendations.id"), nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agreed_with_ai: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Full learning snapshot: ratings, gates, votes, persona/department stances, policy + agent versions.
    snapshot: Mapped[dict] = mapped_column(JSONB)
    followup_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Lesson(Base):
    """PM rationale distilled for reuse: past decisions on similar features inform future runs."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("pm_decisions.id"))
    requirement_id: Mapped[str] = mapped_column(String(40))
    feature_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    area: Mapped[str | None] = mapped_column(String(80), nullable=True)
    market: Mapped[str | None] = mapped_column(String(10), nullable=True)
    action: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class AuditEvent(Base):
    """Append-only; a database trigger rejects UPDATE and DELETE."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=_uuid)
    occurred_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)  # change|decision|ai|access|evidence|system
    actor_type: Mapped[str] = mapped_column(String(20))  # human | agent | system
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    purpose: Mapped[str] = mapped_column(String(60))
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(80))
    prompt_sha256: Mapped[str] = mapped_column(String(64))
    input_record_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    request: Mapped[dict] = mapped_column(JSONB)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


AUDIT_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION audit_events_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
"""
