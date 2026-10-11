"use client";

import useSWR, { mutate } from "swr";

import { api, unwrap } from "./client";
import type {
  Agreement,
  AuditEvent,
  AuditPage,
  Coverage,
  Decision,
  DecisionResult,
  LlmCall,
  Meta,
  Pipeline,
  Requirement,
  RequirementDetail,
  RecordPage,
  SourceDetail,
  Run,
  RunDetail,
  RunResults,
  SignalKind,
  SignalPage,
  Source,
  Task,
  Theme,
  ThemePage,
  Trace,
  Budgets,
  CoverageScope,
  SignalDetail,
  SignalMap,
  TriageSample,
  TriageSummary,
  ProcessingFlow,
  DecisionsOverview,
  Weights,
  VehiclePage,
  Version,
  Council,
  Conversation,
} from "./types";

const ACTIVE_RUN = new Set(["queued", "running"]);

export function useMeta() {
  return useSWR("meta", () => unwrap<Meta>(api.GET("/api/meta")), { revalidateOnFocus: false });
}

// The tasks counter sits on every page, so it polls slowly.
export function useTasks() {
  return useSWR("tasks", () => unwrap<Task[]>(api.GET("/api/tasks")), { refreshInterval: 30000 });
}

// /pipeline aggregates over every claim on each call: fetched on demand, never polled.
export function usePipeline() {
  return useSWR("pipeline", () => unwrap<Pipeline>(api.GET("/api/pipeline")), { revalidateOnFocus: false });
}

export function useSignals(market: string | null, kind: SignalKind | "all", limit = 15) {
  return useSWR(["signals", market ?? "pooled", kind, limit], () =>
    unwrap<SignalPage>(api.GET("/api/signals", { params: { query: { market: market ?? undefined, kind, limit } } })),
  );
}

export function useVehicles() {
  return useSWR("vehicles", () => unwrap<VehiclePage>(api.GET("/api/vehicles")), { revalidateOnFocus: false });
}

export function useTrace(id: string | undefined) {
  return useSWR(id ? ["trace", id] : null, () =>
    unwrap<Trace>(api.GET("/api/requirements/{requirement_id}/trace", { params: { path: { requirement_id: id! } } })),
  );
}

export function useCouncil(id: string | undefined) {
  return useSWR(id ? ["council", id] : null, () =>
    unwrap<Council>(api.GET("/api/requirements/{requirement_id}/council", { params: { path: { requirement_id: id! } } })),
  );
}

// Councils of several simulated requirements for the signals chart. Bounded by the simulated
// requirements in view (a handful), never polled. An aggregate endpoint would replace this.
export function useCouncils(ids: string[]) {
  return useSWR(ids.length ? ["councils", ids.join(",")] : null, async () => {
    // One failing council must not empty the chart: keep the ones that loaded, count the rest.
    const settled = await Promise.allSettled(
      ids.map((id) => unwrap<Council>(api.GET("/api/requirements/{requirement_id}/council", { params: { path: { requirement_id: id } } }))),
    );
    const loaded = settled.flatMap((r) => (r.status === "fulfilled" ? [r.value] : []));
    const failed = settled.filter((r) => r.status === "rejected") as PromiseRejectedResult[];
    if (loaded.length === 0 && failed.length) throw failed[0].reason;
    return { byId: new Map(loaded.map((c) => [c.requirement_id, c])), failed: failed.length };
  }, { revalidateOnFocus: false });
}

// Can be large (TinyTroupe transcripts): fetched once per run and status, never polled.
export function useConversation(runId: string | null | undefined, status?: string) {
  return useSWR(runId ? ["conversation", runId, status ?? ""] : null, () =>
    unwrap<Conversation>(api.GET("/api/simulations/{run_id}/conversation", { params: { path: { run_id: runId! } } })),
    { revalidateOnFocus: false },
  );
}

export async function condenseSignals(markets: (string | null)[]) {
  return unwrap<{ run_id: string; status: string }>(
    api.POST("/api/signals/condense", { body: { markets, kinds: ["pain", "request", "strength"], limit: 8 } }),
  );
}

export function useTheme(id: number | null | undefined) {
  return useSWR(id != null ? ["theme", id] : null, () =>
    unwrap<Theme>(api.GET("/api/themes/{theme_id}", { params: { path: { theme_id: id! } } })),
  );
}

// The run list refreshes every 5 s while any run is still going.
export function useRuns(limit = 20) {
  return useSWR(["runs", limit], () => unwrap<Run[]>(api.GET("/api/simulations", { params: { query: { limit } } })), {
    refreshInterval: (data) => (data?.some((r) => ACTIVE_RUN.has(r.status)) ? 5000 : 0),
  });
}

export function useRunResults(runId: string | null | undefined) {
  return useSWR(runId ? ["run-results", runId] : null, () =>
    unwrap<RunResults>(api.GET("/api/simulations/{run_id}/results", { params: { path: { run_id: runId! } } })),
  );
}

// Every model call of a run in one request (no payloads); polled every 3 s while the run is live.
export function useRunCalls(runId: string | null | undefined, live: boolean) {
  return useSWR(
    runId ? ["run-calls", runId] : null,
    async () => {
      const calls = await unwrap<(Omit<LlmCall, "agent_id"> & { agent_id: string | null })[]>(
        api.GET("/api/simulations/{run_id}/llm-calls", { params: { path: { run_id: runId! } } }),
      );
      return calls.map((c) => ({ ...c, agent_id: c.agent_id ?? "agent:unknown" })) as LlmCall[];
    },
    { refreshInterval: live ? 3000 : 0 },
  );
}

export interface RequirementQuery {
  sort?: "priority" | "score" | "created" | "updated";
  status?: string;
  market?: string;
}

export function useRequirements(query: RequirementQuery = {}) {
  return useSWR(["requirements", query.sort, query.status, query.market], () =>
    unwrap<Requirement[]>(
      api.GET("/api/requirements", {
        params: { query: { sort: query.sort ?? "priority", status: query.status, market: query.market } },
      }),
    ),
  );
}

export function useRequirement(id: string | undefined) {
  return useSWR(id ? ["requirement", id] : null, () =>
    unwrap<RequirementDetail>(
      api.GET("/api/requirements/{requirement_id}", { params: { path: { requirement_id: id! } } }),
    ),
  );
}

// Polls every 3 s while the run is queued or running, then stops.
export function useRun(runId: string | null | undefined) {
  return useSWR(
    runId ? ["run", runId] : null,
    () => unwrap<RunDetail>(api.GET("/api/simulations/{run_id}", { params: { path: { run_id: runId! } } })),
    { refreshInterval: (data) => (data && ACTIVE_RUN.has(data.run.status) ? 3000 : 0) },
  );
}

export function useLlmCalls(runId: string | null | undefined, requirementId: string, live: boolean) {
  return useSWR(
    runId ? ["llm-calls", runId, requirementId] : null,
    async () => {
      const calls = await unwrap<(Omit<LlmCall, "agent_id"> & { agent_id: string | null })[]>(
        api.GET("/api/simulations/{run_id}/llm-calls", {
          params: { path: { run_id: runId! }, query: { requirement_id: requirementId } },
        }),
      );
      return calls.map((c) => ({ ...c, agent_id: c.agent_id ?? "agent:unknown" })) as LlmCall[];
    },
    { refreshInterval: live ? 3000 : 0 },
  );
}

export function useAudit(category?: string) {
  return useSWR(["audit", category ?? "all"], () =>
    unwrap<AuditPage>(api.GET("/api/audit", { params: { query: { category, limit: 100 } } })),
    { refreshInterval: 10000 },
  );
}

export function useRequirementAudit(id: string) {
  return useSWR(["requirement-audit", id], () =>
    unwrap<AuditEvent[]>(
      api.GET("/api/requirements/{requirement_id}/audit", { params: { path: { requirement_id: id } } }),
    ),
  );
}

export function useVersions(id: string) {
  return useSWR(["versions", id], () =>
    unwrap<Version[]>(
      api.GET("/api/requirements/{requirement_id}/versions", { params: { path: { requirement_id: id } } }),
    ),
  );
}

export function useLearningDecisions() {
  return useSWR("learning-decisions", () => unwrap<Decision[]>(api.GET("/api/learning/decisions")));
}

export function useAgreement() {
  return useSWR("learning-agreement", () => unwrap<Agreement[]>(api.GET("/api/learning/agreement")));
}

// After any write, refetch everything that is mounted. The app is small enough for this to stay cheap.
export function refreshAll() {
  return mutate(() => true);
}

export async function startRun(requirementIds: string[], challenge?: string) {
  return unwrap<Run>(
    // persona_scope "market": owners answer only for their own market, like the regional sales departments.
    api.POST("/api/simulations", { body: { requirement_ids: requirementIds, challenge: challenge || null, persona_scope: "market" } }),
  );
}

export async function decide(
  id: string,
  body: { action: "approve" | "reject" | "challenge" | "defer"; rationale: string; challenge_question?: string },
) {
  return unwrap<DecisionResult>(
    api.POST("/api/requirements/{requirement_id}/decision", {
      params: { path: { requirement_id: id } },
      body: { ...body, challenge_question: body.challenge_question || null },
    }),
  );
}

export async function overrideGate(id: string, gate: string, body: { value: "pass" | "fail" | "unknown"; rationale: string }) {
  return unwrap<unknown>(
    api.POST("/api/requirements/{requirement_id}/gates/{gate}", {
      params: { path: { requirement_id: id, gate } },
      body,
    }),
  );
}

export async function editRequirement(id: string, changes: Record<string, unknown>, rationale: string) {
  return unwrap<Requirement>(
    api.PATCH("/api/requirements/{requirement_id}", {
      params: { path: { requirement_id: id } },
      body: { changes, rationale },
    }),
  );
}

export async function buildThemes() {
  return unwrap<unknown>(api.POST("/api/themes/build", { body: { include_examples: false, include_pending_claims: false } }));
}

export async function draftRequirements(market: string | null, limit: number, featureKeys?: string[]) {
  return unwrap<{ created: unknown[]; skipped_existing?: unknown[]; dropped_invalid_citations?: number }>(
    api.POST("/api/requirements/draft", { body: { market, limit, feature_keys: featureKeys?.length ? featureKeys : null } }),
  );
}

// Default: the vehicle's own records. Other scopes (competitor, other_models, brand) are drill-downs.
export function useCoverage(scope?: CoverageScope) {
  return useSWR(scope ? ["coverage", scope] : "coverage", () =>
    unwrap<Coverage>(api.GET("/api/coverage", { params: { query: scope ? { scope } : {} } })),
  );
}

// min_reviews: the backend hides signals under 5 reviews by default (noise); 1 shows all of them.
export function useSignalMap(market: string | null, minReviews?: number) {
  return useSWR(["signal-map", market ?? "pooled", minReviews ?? "default"], () =>
    unwrap<SignalMap>(api.GET("/api/signals/map", { params: { query: { market: market ?? undefined, min_reviews: minReviews } } })),
  );
}

export function useSignalDetail(featureKey: string | null, market: string | null) {
  return useSWR(featureKey ? ["signal-detail", featureKey, market ?? "pooled"] : null, () =>
    unwrap<SignalDetail>(
      api.GET("/api/signals/{feature_key}", { params: { path: { feature_key: featureKey! }, query: { market: market ?? undefined } } }),
    ),
  );
}

export function useWeights() {
  return useSWR("weights", () => unwrap<Weights>(api.GET("/api/weights")), { revalidateOnFocus: false });
}

export function useDecisionsOverview() {
  return useSWR("overview-decisions", () => unwrap<DecisionsOverview>(api.GET("/api/overview/decisions")));
}

// All data before any vehicle: streams → not relevant / this vehicle / other models / competitors / brand-wide.
export function useOverviewFlow() {
  return useSWR("overview-flow", () => unwrap<ProcessingFlow>(api.GET("/api/overview/flow")), { revalidateOnFocus: false });
}

export function useTriageSummary() {
  return useSWR("triage-summary", () => unwrap<TriageSummary>(api.GET("/api/triage/summary")), { revalidateOnFocus: false });
}

export function useTriageSample(open: boolean, n = 30) {
  return useSWR(open ? ["triage-sample", n] : null, () => unwrap<TriageSample>(api.GET("/api/triage/sample", { params: { query: { n } } })));
}

export function useBudgets(market: string | null) {
  return useSWR(["budgets", market ?? "pooled"], () =>
    unwrap<Budgets>(api.GET("/api/budgets", { params: { query: { market: market ?? undefined } } })),
  );
}

export function useSources() {
  return useSWR("sources", () => unwrap<Source[]>(api.GET("/api/sources")));
}

export function useRecords(query: {
  q?: string;
  market?: string;
  bucket?: string;
  scope?: "target" | "all";
  channel?: string;
  ids?: string[];
  offset?: number;
}) {
  return useSWR(["records", query.q, query.market, query.bucket, query.scope, query.channel, query.ids?.join(","), query.offset], () =>
    unwrap<RecordPage>(
      api.GET("/api/records", {
        params: {
          query: {
            q: query.q || undefined,
            market: query.market,
            bucket: query.bucket,
            scope: query.scope,
            channel: query.channel,
            ids: query.ids?.length ? query.ids : undefined,
            limit: 50,
            offset: query.offset ?? 0,
          },
        },
      }),
    ),
  );
}

export function useSource(id: string) {
  return useSWR(["source", id], () =>
    unwrap<SourceDetail>(api.GET("/api/sources/{source_id}", { params: { path: { source_id: id } } })),
  );
}

export function useThemes(market: string | undefined) {
  return useSWR(["themes", market ?? "pooled"], () =>
    unwrap<ThemePage>(api.GET("/api/themes", { params: { query: { market, limit: 200 } } })),
  );
}

export async function reviewSource(id: string, status: "accepted" | "rejected" | "pending", notes: string) {
  return unwrap<unknown>(
    api.POST("/api/sources/{source_id}/review", {
      params: { path: { source_id: id } },
      body: { review_status: status, external_llm: null, notes },
    }),
  );
}
