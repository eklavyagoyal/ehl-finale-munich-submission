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
  Requirement,
  RequirementDetail,
  RecordPage,
  SourceDetail,
  Run,
  RunDetail,
  Source,
  Task,
  ThemePage,
  Version,
} from "./types";

const ACTIVE_RUN = new Set(["queued", "running"]);

export function useMeta() {
  return useSWR("meta", () => unwrap<Meta>(api.GET("/api/meta")), { revalidateOnFocus: false });
}

export function useTasks() {
  return useSWR("tasks", () => unwrap<Task[]>(api.GET("/api/tasks")), { refreshInterval: 5000 });
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

// Polls every 1.5 s while the run is queued or running, then stops.
export function useRun(runId: string | null | undefined) {
  return useSWR(
    runId ? ["run", runId] : null,
    () => unwrap<RunDetail>(api.GET("/api/simulations/{run_id}", { params: { path: { run_id: runId! } } })),
    { refreshInterval: (data) => (data && ACTIVE_RUN.has(data.run.status) ? 1500 : 0) },
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
    { refreshInterval: live ? 1500 : 0 },
  );
}

export function useAudit(category?: string) {
  return useSWR(["audit", category ?? "all"], () =>
    unwrap<AuditPage>(api.GET("/api/audit", { params: { query: { category, limit: 100 } } })),
    { refreshInterval: 4000 },
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
    api.POST("/api/simulations", { body: { requirement_ids: requirementIds, challenge: challenge || null } }),
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

export async function draftRequirements(market: string | null, limit: number) {
  return unwrap<{ created: unknown[]; skipped_existing?: unknown[]; dropped_invalid_citations?: number }>(
    api.POST("/api/requirements/draft", { body: { market, limit } }),
  );
}

export function useCoverage() {
  return useSWR("coverage", () => unwrap<Coverage>(api.GET("/api/coverage")));
}

export function useSources() {
  return useSWR("sources", () => unwrap<Source[]>(api.GET("/api/sources")));
}

export function useRecords(query: { q?: string; market?: string; channel?: string; ids?: string[]; offset?: number }) {
  return useSWR(["records", query.q, query.market, query.channel, query.ids?.join(","), query.offset], () =>
    unwrap<RecordPage>(
      api.GET("/api/records", {
        params: {
          query: {
            q: query.q || undefined,
            market: query.market,
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

// Counts records per (channel, market) exactly as tagged; one small request per cell, limit=1.
export function useGapMatrix(channels: string[], markets: string[]) {
  return useSWR(
    channels.length && markets.length ? ["gaps", channels.join(","), markets.join(",")] : null,
    async () => {
      const cells = await Promise.all(
        channels.flatMap((channel) =>
          markets.map(async (market) => {
            const page = await unwrap<RecordPage>(api.GET("/api/records", { params: { query: { channel, market, limit: 1 } } }));
            return [`${channel}|${market}`, page.total] as const;
          }),
        ),
      );
      return new Map<string, number>(cells);
    },
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
