import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Browser-side client. Every call goes to the same-origin BFF (/bff/api/...), never to the backend.
export const api = createClient<paths>({ baseUrl: "/bff" });

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
}

const HINTS: Record<number, string> = {
  401: "The frontend server is not authorised against the API (token or proxy misconfigured).",
  403: "Only a PM can do this.",
  409: "A gate blocks this action.",
  422: "The input is not valid.",
};

function detailOf(status: number, error: unknown): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => [d.loc?.slice(1).join("."), d.msg].filter(Boolean).join(": "))
      .join("; ");
  }
  if (typeof error === "string" && error) return error;
  return HINTS[status] ?? `Request failed (${status})`;
}

// openapi-fetch returns {data, error, response}; turn non-2xx into an ApiError carrying the backend's detail.
export async function unwrap<T>(call: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) throw new ApiError(response.status, detailOf(response.status, error));
  return data as T;
}
