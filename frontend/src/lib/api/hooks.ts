"use client";

import useSWR, { mutate } from "swr";

import { api, unwrap } from "./client";
import type {
  Agreement,
  AuditEvent,
  AuditPage,
  Decision,
  DecisionResult,
  LlmCall,
  Meta,
  Requirement,
  RequirementDetail,
  Run,
  RunDetail,
  Task,
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
    () =>
      unwrap<LlmCall[]>(
        api.GET("/api/simulations/{run_id}/llm-calls", {
          params: { path: { run_id: runId! }, query: { requirement_id: requirementId } },
        }),
      ),
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
  return unwrap<unknown>(api.POST("/api/requirements/draft", { body: { market, limit } }));
}
