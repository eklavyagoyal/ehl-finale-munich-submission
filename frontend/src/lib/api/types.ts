import type { components } from "./schema";

// Response shapes of the Parallax API. Flat models come straight from the generated OpenAPI types
// (schema.d.ts); interfaces below refine the JSON blobs the spec leaves as generic objects.
type Schemas = components["schemas"];

export type Task = Schemas["TaskOut"];
export type Rating = Schemas["RatingOut"];
// agent_id is nullable in the spec; the hook fills "agent:unknown" so every call has a lane.
export type LlmCall = Omit<Schemas["LLMCallOut"], "agent_id"> & { agent_id: string };
export type EvidenceLink = Schemas["EvidenceOut"];
export type SourceSummary = Schemas["SourceSummaryOut"];
export type ClaimSummary = Schemas["ClaimSummaryOut"];

export type GateValue = "pass" | "fail" | "unknown";
export type RatingStatus = "observed" | "estimated" | "simulated" | "assumed" | "unknown" | string;

export interface Requirement {
  id: string;
  target_model: string;
  market: string | null;
  feature_key: string | null;
  theme_id: number | null;
  title: string;
  description: string;
  customer_problem: string;
  acceptance_criteria: string[];
  evidence_level: string;
  evidence_level_explanation: string;
  assumptions: string[];
  uncertainties: string[];
  planning_horizon: string;
  status: string;
  priority_rank: number | null;
  score: number | null;
  score_low: number | null;
  score_high: number | null;
  prioritization_rationale: string;
  suggested_next_action: string | null;
  kano_class: string | null;
  kano_rationale: string | null;
  benchmark_target: string | null;
  version: number;
  created_by: string;
  last_run_id: string | null;
  created_at: string;
  updated_at: string;
  gates: Record<string, GateValue>;
  ai_recommendation: string | null;
}


export interface GateDetail {
  value: GateValue;
  owner: string;
  reason: string;
  reference: string | null;
  at: string;
}

export interface CriterionScore {
  criterion: string;
  weight: number;
  score: number | null;
  low: number | null;
  high: number | null;
  status: RatingStatus;
  raters: string[];
  rating_ids: number[];
}



export interface Synthesis {
  run_id: string;
  content: {
    headline?: string;
    conflicts?: { between: string; description: string }[];
    assumptions?: string[];
    market_views?: { market: string; summary: string; observed_evidence?: string; simulated_importance_0_5?: number }[];
    internal_view?: string;
    research_view?: string;
    evidence_vs_simulation?: string;
    suggested_requirement_edit?: unknown;
    clinic_questions?: string[];
  };
}

export interface Challenge {
  counter_position?: string;
  strongest_arguments?: string[];
  overlooked_segments?: string[];
  evidence_that_would_change_the_call?: string[];
  risk_if_outcome_is_wrong?: string;
}

export interface Recommendation {
  run_id: string;
  recommendation: string;
  tally: { counts: Record<string, number>; reason?: string; gate_cap?: string | null };
  minority_report: { judge?: string; agent_id?: string; vote?: string; rationale?: string }[];
  challenge: Challenge | null;
}

export interface Vote {
  run_id?: string;
  agent_id: string;
  model: string;
  vote: string;
  rationale: string;
  key_points?: string[];
  created_at: string;
}

export interface PersonaResponse {
  run_id?: string;
  agent_id: string;
  response_text: string;
  stance: string;
  ssr_mean?: number;
  importance_0_5?: number;
  market_fit_0_5?: number;
  concerns?: string[];
  info_requests?: unknown[];
  grounding_record_ids?: string[];
  created_at: string;
}

export interface DepartmentMemo {
  run_id?: string;
  agent_id: string;
  stance: string;
  memo: {
    summary?: string;
    effort_band?: string;
    risks?: string[];
    conditions?: string[];
    criterion_ratings?: { criterion: string; low: number; high: number; rationale: string }[];
  };
  created_at: string;
}

export interface ResearchItem {
  requested_by: string;
  question: string;
  rationale?: string;
  status?: string;
  verdict?: string;
  findings?: { claim?: string; source_url?: string; source_title?: string; answer_summary?: string }[];
  created_at?: string;
}

export interface Decision {
  id: number;
  requirement_id: string;
  action: string;
  rationale: string;
  actor_id: string;
  ai_recommendation: string | null;
  agreed_with_ai: boolean | null;
  created_at: string;
}

export interface RequirementDetail {
  requirement: Requirement;
  gates: Record<string, GateDetail>;
  scores: {
    criteria: Record<string, CriterionScore>;
    score_low: number | null;
    score_high: number | null;
    score_midpoint: number | null;
    unknown_criteria: string[];
    uncertain_criteria: string[];
    formula?: string;
    note?: string;
  };
  ratings: Rating[];
  evidence: EvidenceLink[];
  latest_run_id: string | null;
  synthesis: Synthesis | null;
  recommendation: Recommendation | null;
  votes: Vote[];
  persona_responses: PersonaResponse[];
  department_memos: DepartmentMemo[];
  research: ResearchItem[];
  decisions: Decision[];
}

export interface Run {
  id: string;
  kind: string;
  status: "queued" | "running" | "completed" | "partial" | "failed" | string;
  requirement_ids: string[];
  parent_run_id: string | null;
  challenge_question: string | null;
  requested_by: string;
  progress: { stage?: string; completed_stages?: string[]; errors?: unknown[] } | null;
  error: string | null;
  llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunStep {
  id: number;
  requirement_id: string | null;
  stage: string;
  agent_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunDetail {
  run: Run;
  steps: RunStep[];
}


export interface AuditEvent {
  id: number;
  event_id: string;
  occurred_at: string;
  category: string;
  actor_type: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  requirement_id: string | null;
  run_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  rationale: string | null;
  meta: Record<string, unknown> | null;
}

export interface AuditPage {
  total: number;
  items: AuditEvent[];
}

export interface Version {
  id: number;
  version: number;
  actor_id: string;
  change_reason: string | null;
  created_at: string;
}

export interface Agreement {
  agent_id: string;
  display_name: string;
  decisions: number;
  agreements: number;
  agreement_rate: number | null;
}

export interface Meta {
  version: string;
  llm_mode: string;
  target_model: string;
  markets: string[];
  counts: Record<string, number>;
  enums: {
    requirement_status: string[];
    pm_actions: string[];
    gates: string[];
    gate_values: string[];
    rating_status: string[];
    evidence_level: string[];
    recommendation: string[];
  };
}

export interface DecisionResult {
  decision: Decision;
  followup_run_id: string | null;
  requirement: Requirement;
}

export interface Source {
  source_id: string;
  dataset_key: string;
  stream: string;
  channel: string;
  title: string;
  locator: string | null;
  collected_at: string | null;
  collector: string | null;
  is_example: boolean;
  normalized_record_count: number;
  sampling: { method?: string; limitations?: string[]; retrieved_count?: number } | null;
  provenance: { origin?: string; verification?: string; notes?: string } | null;
  external_llm: boolean;
  review_status: "pending" | "accepted" | "rejected" | string;
  ingest_run_id?: string | null;
  updated_at?: string | null;
}

export interface EvidenceRecord {
  record_id: string;
  source_id: string;
  record_kind: string;
  markets: string[];
  subject_ids: string[];
  text_original: string | null;
  translation_en: string | null;
  language: string | null;
  content_date: string | null;
  channel: string;
  locator: Record<string, unknown>;
}

export interface RecordPage {
  total: number;
  items: EvidenceRecord[];
}

export interface Theme {
  id: number;
  market: string | null;
  feature_key: string;
  label: string;
  area: string;
  mention_review_count: number;
  direct_review_count: number;
  request_review_count: number;
  pain_review_count: number;
  praise_review_count: number;
  competitor_review_count: number;
  channels: string[];
  counts_by_claim_type?: Record<string, number>;
  record_ids?: string[];
  derived_from_labels?: number;
  demand_score?: number;
  cohorts?: {
    channel: string;
    markets: string[];
    dataset_key: string;
    subject_ids?: string[];
    collection_method?: string | null;
    mention_review_count: number;
    feedback_review_count?: number;
    share?: number;
  }[];
}

export interface ThemePage {
  snapshot_id: string | null;
  items: Theme[];
}

export interface Coverage {
  records_by_channel: { stream: string; channel: string; review_status: string; external_llm: boolean; records: number }[];
  records_by_market: { market: string | null; records: number }[];
  claims: { review_status: string; derived_from_bmw_labels: boolean; claims: number }[];
  // Channel x market counts in one response; a record tagged with two markets counts in both.
  // Optional because older API builds do not return it.
  records_by_channel_market?: { stream: string; channel: string; market: string; records: number }[];
  llm_rule: string;
}

export interface SourceDetail {
  source: Source & {
    sampling: { method?: string; complete?: boolean; retrieved_count?: number; query?: string | null; date_start?: string | null; date_end?: string | null; limitations?: string[] } | null;
    provenance: { origin?: string; verification?: string; notes?: string } | null;
    export_permissions: { git?: boolean; external_llm?: boolean; notes?: string } | null;
    ingest_run_id: string | null;
    updated_at: string | null;
  };
  summary: SourceSummary;
  records: number;
  claims: { review_status: string; derived_from_bmw_labels: boolean; count: number }[];
  claim_producers: { method: string | null; name: string | null; count: number }[];
}

// GET /api/pipeline: the start page, one card per stage of the PM's path.
export type StageKey = "sources" | "processing" | "signals" | "experts" | "decision";
export type StageStatus = "todo" | "in_progress" | "done";

interface StageBase {
  title: string;
  question: string;
  status: StageStatus;
}

export interface SourcesStage extends StageBase {
  key: "sources";
  counts: {
    sources: number;
    records: number;
    pending_review: number;
    by_stream: { stream: string; label: string; records: number }[];
  };
  last_import: string | null;
}

export interface ProcessingStage extends StageBase {
  key: "processing";
  counts: {
    // Only records of kind "feedback"; records_without_claims is measured against this number.
    feedback_records: number;
    records_with_claims: number;
    records_without_claims: number;
    claims_by_status: Record<string, number>;
    // "BMW labels", or the producer method: llm, human, provided_unknown, unknown.
    claims_by_producer: Record<string, number>;
  };
}

export interface SignalsStage extends StageBase {
  key: "signals";
  counts: { features_with_evidence: number; by_kind: Record<string, number> };
  top_pains: string[];
  top_strengths: string[];
  top_requests: string[];
}

export interface ExpertsStage extends StageBase {
  key: "experts";
  counts: { requirements: number; runs_by_status: Record<string, number> };
}

export interface DecisionStage extends StageBase {
  key: "decision";
  counts: { by_status: Record<string, number> };
}

export type PipelineStage = SourcesStage | ProcessingStage | SignalsStage | ExpertsStage | DecisionStage;

export interface Pipeline {
  target_model: string;
  stages: PipelineStage[];
  next_action: { stage: StageKey; label: string; action?: string };
}

// GET /api/signals: theme counts read as pains, strengths and requests.
export type SignalKind = "pain" | "strength" | "request" | "mixed";

export interface Signal {
  theme_id: number;
  feature_key: string;
  label: string;
  area: string | null;
  market: string | null;
  kind: SignalKind;
  reviews: number;
  direct_reviews: number;
  pain: number;
  requests: number;
  praise: number;
  competitor_reviews: number;
  channels: string[];
  demand_0_5: number;
  impact_0_5: number | null;
  sample_quotes: { record_id: string; text: string }[];
  has_requirement: boolean;
  // Findings: the LLM groups reviews into concrete issues, the counts come from code.
  condensed?: boolean;
  findings?: Finding[];
}

export interface Finding {
  id: number;
  title: string;
  description: string;
  kind: string;
  reviews: number;
  share_of_theme: number;
  quotes: { record_id: string; text: string }[];
  record_ids: string[];
}

export interface SignalPage {
  snapshot_id: string | null;
  market: string | null;
  basis?: string;
  items: Signal[];
}

// GET /api/simulations/{id}/results: every agent output of a run, per requirement.
export interface RunResults {
  run: Run;
  requirements: Record<
    string,
    {
      persona_responses: PersonaResponse[];
      department_memos: DepartmentMemo[];
      research: ResearchItem[];
      ratings: Rating[];
      synthesis: Synthesis[];
      votes: Vote[];
      recommendation: Recommendation[];
    }
  >;
}

// GET /api/vehicles: the landing page.
export interface Vehicle {
  entity_id: string;
  code: string;
  name: string;
  detail: string;
  records: number;
  in_catalog: boolean;
  status: "active" | "data_available" | "not_imported";
}

export interface VehiclePage {
  active: string;
  items: Vehicle[];
}

// GET /api/requirements/{id}/trace: the decision path, one aggregated step per stage.
export type TraceBasis = "evidence" | "simulation" | "assumption" | "mixed" | "human" | "none";
export type TraceEffect = "supports" | "against" | "neutral";

export interface TraceAgent {
  id: string;
  name: string;
  kind: "code" | "agent" | "persona" | "department" | "judge" | "human" | string;
}

export interface TraceTension {
  topic?: string | null;
  customers_say?: string | null;
  company_says?: string | null;
  resolution_options?: string[];
  description?: string | null;
}

export interface TraceDriver {
  source: string;
  statement: string;
  effect: TraceEffect;
  weight?: "high" | "medium" | "low";
}

export interface TraceStep {
  key: string;
  order: number;
  title: string;
  question?: string;
  agents?: TraceAgent[];
  basis: TraceBasis;
  inputs?: Record<string, unknown>;
  // Shape depends on the step key; see the renderers in decision-path.tsx.
  output?: unknown;
  why?: string | null;
  effect: TraceEffect;
  caveat?: string;
  tensions?: TraceTension[];
  drill_down?: string;
}

export interface Trace {
  requirement_id: string;
  title: string;
  market: string | null;
  legend: Record<string, string>;
  steps: TraceStep[];
}

// GET /api/requirements/{id}/council: customer council by market vs company council.
export interface CouncilPersona {
  agent_id: string;
  name: string | null;
  display_name: string;
  vehicle: string | null;
  powertrain: string | null;
  verdict: string | null;
  budget_points: number | null;
  importance_0_5: number | null;
  stance: string;
  quote: string;
  concerns: string[] | null;
  validation_status: string | null;
}

export interface CouncilMarket {
  personas: CouncilPersona[];
  summary: {
    personas: number;
    verdicts: Record<string, number>;
    mean_budget_points_of_100: number | null;
    mean_importance_0_5: number | null;
  };
}

export interface CouncilDepartment {
  agent_id: string;
  display_name: string;
  market: string | null;
  verdict: string | null;
  main_argument: string | null;
  strongest_counterargument?: string | null;
  cost_view?: string | null;
  effort_band?: string | null;
  risks?: string[];
}

export interface Council {
  requirement_id: string;
  run_id: string | null;
  status: "simulated" | "not_simulated";
  title?: string;
  question_to_owners?: string | null;
  customers?: { by_market: Record<string, CouncilMarket>; view?: string | null };
  company?: { departments: CouncilDepartment[]; view?: string | null; verdicts: Record<string, number> };
  tensions?: TraceTension[];
  headline?: string | null;
  research?: { requested_by: string; question: string; verdict: string | null }[];
  challenger?: Challenge | null;
  judges?: { agent_id: string; model: string; vote: string; rationale: string }[];
  recommendation?: string | null;
}

// GET /api/simulations/{id}/conversation: who was asked what, and every answer.
export interface ConversationOwner {
  agent_id: string;
  name: string | null;
  display_name: string;
  market: string | null;
  country: string | null;
  vehicle: string | null;
  powertrain: string | null;
  segment?: string | null;
  environment?: Record<string, string>;
  validation_status?: string | null;
  engine?: string | null;
  grounding_records: number;
  transcript?: string | null;
  answers: {
    requirement_id: string;
    requirement_title?: string | null;
    reaction: string;
    stance: string;
    importance_0_5: number | null;
    class_fit_0_5: number | null;
    concerns: string[] | null;
    would_need_to_know: unknown[] | null;
  }[];
}

export interface ConversationDepartment {
  agent_id: string;
  display_name: string;
  market: string | null;
  role?: string | null;
  answers: { requirement_id: string; stance: string; summary?: string | null; effort_band?: string | null; risks?: string[] | null }[];
}

export interface Conversation {
  run: { id: string; status: string; stage?: string | null; challenge_question?: string | null; engine?: string | null };
  order: string[];
  question_to_owners: string | null;
  owners_by_market: Record<string, ConversationOwner[]>;
  departments: ConversationDepartment[];
}
