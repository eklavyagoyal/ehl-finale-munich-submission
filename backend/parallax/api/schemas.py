"""Response models, so the OpenAPI spec carries typed responses for the frontend's generated client."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Out(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ------------------------------------------------------------------ requirements


class RequirementOut(Out):
    id: str
    target_model: str
    market: str | None
    feature_key: str | None
    theme_id: int | None
    title: str
    description: str
    customer_problem: str
    acceptance_criteria: list[Any]
    evidence_level: str
    evidence_level_explanation: str
    assumptions: list[Any]
    uncertainties: list[Any]
    planning_horizon: str
    status: str
    priority_rank: int | None
    score: float | None
    score_low: float | None
    score_high: float | None
    prioritization_rationale: str
    suggested_next_action: str | None
    kano_class: str | None
    kano_rationale: str
    benchmark_target: str | None
    version: int
    created_by: str
    last_run_id: str | None
    created_at: datetime
    updated_at: datetime
    gates: dict[str, str]
    ai_recommendation: str | None
    progress: list[dict[str, Any]] = []


class GateOut(Out):
    value: str
    owner: str
    reason: str
    reference: str | None
    at: datetime | None


class CriterionOut(Out):
    criterion: str
    weight: float
    score: float | None
    low: float
    high: float
    status: str
    raters: list[str]
    rating_ids: list[int]


class ScoresOut(Out):
    criteria: dict[str, CriterionOut]
    score_low: float
    score_high: float
    score_midpoint: float
    unknown_criteria: list[str]
    uncertain_criteria: list[str]
    formula: str | None
    note: str


class RatingOut(Out):
    id: int
    requirement_id: str
    run_id: str | None
    criterion: str
    score: float | None
    low: float | None
    high: float | None
    status: str
    rater_type: str
    rater_id: str
    rationale: str
    evidence_ids: list[str]
    created_at: datetime


class EvidenceRecordOut(Out):
    text: str | None
    translation_en: str | None
    language: str | None = None
    markets: list[str]
    subject_ids: list[str]
    source_id: str
    locator: dict[str, Any]
    content_date: str | None = None
    record_kind: str | None = None


class SourceSummaryOut(Out):
    """Where the evidence comes from: stream (bmw/competitors/social), channel, collector, origin, review, LLM permission."""
    source_id: str
    stream: str
    channel: str
    title: str
    collector: str
    collected_at: datetime | None
    dataset_key: str
    origin: str | None
    verification: str | None
    review_status: str
    external_llm: bool | None
    is_example: bool
    sampling_method: str | None
    sampling_complete: bool | None
    limitations: list[Any]


class ClaimSummaryOut(Out):
    """Who interpreted the record: human, LLM (model + run) or BMW's own VFC classification."""
    claim_id: str
    feature_key: str | None
    feature_label: str
    claim_type: str
    summary: str
    quotes: list[Any]
    review_status: str
    derived_from_bmw_labels: bool
    producer_method: str | None
    producer_name: str | None
    producer_version: str | None
    producer_run_id: str | None


class EvidenceOut(Out):
    id: int
    requirement_id: str
    record_id: str
    claim_id: str | None
    relation: str
    quote: str | None
    quote_verified: bool
    added_by: str
    created_at: datetime
    record: EvidenceRecordOut
    source: SourceSummaryOut | None = None
    claims: list[ClaimSummaryOut] = []


class SynthesisRowOut(Out):
    id: int
    run_id: str
    requirement_id: str
    content: dict[str, Any]
    created_at: datetime


class RecommendationOut(Out):
    id: int
    run_id: str
    requirement_id: str
    recommendation: str
    tally: dict[str, Any]
    minority_report: list[Any]
    challenge: dict[str, Any]
    score_snapshot: dict[str, Any]
    created_at: datetime


class VoteOut(Out):
    id: int
    run_id: str
    requirement_id: str
    agent_id: str
    model: str
    vote: str
    rationale: str
    key_points: list[Any]
    created_at: datetime


class PersonaResponseOut(Out):
    id: int
    run_id: str
    agent_id: str
    agent_version: int
    requirement_id: str
    engine: str
    response_text: str
    stance: str
    ssr_distribution: list[float]
    ssr_mean: float
    importance_0_5: float
    market_fit_0_5: float | None
    concerns: list[Any]
    info_requests: list[Any]
    grounding_record_ids: list[str]
    created_at: datetime


class DepartmentMemoRowOut(Out):
    id: int
    run_id: str
    agent_id: str
    agent_version: int
    requirement_id: str
    stance: str
    memo: dict[str, Any]
    created_at: datetime


class ResearchRequestOut(Out):
    id: int
    run_id: str
    requirement_id: str
    requested_by: str
    question: str
    rationale: str
    status: str
    findings: list[Any]
    sources: list[Any]
    verification: dict[str, Any]
    verdict: str | None
    created_at: datetime
    updated_at: datetime


class DecisionOut(Out):
    id: int
    requirement_id: str
    action: str
    rationale: str
    actor_id: str
    requirement_version: int
    recommendation_id: int | None
    ai_recommendation: str | None
    agreed_with_ai: bool | None
    followup_run_id: str | None
    created_at: datetime


class RequirementDetailOut(Out):
    requirement: RequirementOut
    gates: dict[str, GateOut]
    scores: ScoresOut
    ratings: list[RatingOut]
    evidence: list[EvidenceOut]
    latest_run_id: str | None
    synthesis: SynthesisRowOut | None
    recommendation: RecommendationOut | None
    votes: list[VoteOut]
    persona_responses: list[PersonaResponseOut]
    department_memos: list[DepartmentMemoRowOut]
    research: list[ResearchRequestOut]
    decisions: list[DecisionOut]


class DecisionResultOut(Out):
    decision: DecisionOut
    followup_run_id: str | None
    requirement: RequirementOut


# ------------------------------------------------------------------ tasks, runs, calls, audit


class TaskOut(Out):
    kind: str  # decide | simulate | running | review_evidence
    label: str
    requirement_id: str | None = None
    requirement_ids: list[str] | None = None
    title: str | None = None
    market: str | None = None
    ai_recommendation: str | None = None
    score: float | None = None
    score_low: float | None = None
    score_high: float | None = None
    failed_gates: list[str] | None = None
    run_id: str | None = None
    stage: str | None = None
    count: int | None = None


class RunOut(Out):
    id: str
    kind: str
    status: str
    requirement_ids: list[str]
    config: dict[str, Any]
    parent_run_id: str | None
    challenge_question: str | None
    requested_by: str
    progress: dict[str, Any]
    error: str | None
    llm_calls: int
    input_tokens: int
    output_tokens: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class StepOut(Out):
    id: int
    run_id: str
    requirement_id: str | None
    stage: str
    agent_id: str | None
    status: str
    detail: dict[str, Any]
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class RunDetailOut(Out):
    run: RunOut
    steps: list[StepOut]


class LLMCallOut(Out):
    id: int
    run_id: str | None
    agent_id: str | None
    requirement_id: str | None
    purpose: str
    provider: str
    model: str
    prompt_version: str
    prompt_sha256: str
    input_record_ids: list[str]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    status: str
    error: str | None
    created_at: datetime
    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None


class AuditEventOut(Out):
    id: int
    event_id: str
    occurred_at: datetime
    category: str
    actor_type: str
    actor_id: str
    action: str
    entity_type: str | None
    entity_id: str | None
    requirement_id: str | None
    run_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    rationale: str | None
    meta: dict[str, Any]


class AuditPageOut(Out):
    total: int
    items: list[AuditEventOut]
