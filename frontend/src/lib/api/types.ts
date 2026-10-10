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
  demand_score?: number;
}

export interface ThemePage {
  snapshot_id: string | null;
  items: Theme[];
}

export interface Coverage {
  records_by_channel: { stream: string; channel: string; review_status: string; external_llm: boolean; records: number }[];
  records_by_market: { market: string | null; records: number }[];
  claims: { review_status: string; derived_from_bmw_labels: boolean; claims: number }[];
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
