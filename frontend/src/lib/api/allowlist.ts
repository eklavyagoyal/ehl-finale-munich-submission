// Endpoints the cockpit may reach through the /bff proxy. Everything else is refused with 403,
// so the public frontend cannot be used to call admin endpoints (ingest, policy, agents) with the
// server token. Paths are relative to /api; "*" matches exactly one segment.
// scripts/check-allowlist.ts verifies that every api.<METHOD>("/api/...") call in src/ is covered.
export const ALLOWED: ReadonlyArray<readonly [method: string, path: string]> = [
  ["GET", "health"],
  ["GET", "meta"],
  ["GET", "tasks"],
  ["GET", "requirements"],
  ["GET", "requirements/*"],
  ["GET", "requirements/*/audit"],
  ["GET", "requirements/*/versions"],
  ["PATCH", "requirements/*"],
  ["POST", "requirements/*/decision"],
  ["POST", "requirements/*/gates/*"],
  ["POST", "requirements/draft"],
  ["GET", "simulations/*"],
  ["GET", "simulations/*/llm-calls"],
  ["POST", "simulations"],
  ["GET", "audit"],
  ["GET", "learning/decisions"],
  ["GET", "learning/agreement"],
  ["GET", "coverage"],
  ["GET", "sources"],
  ["GET", "sources/*"],
  ["POST", "sources/*/review"],
  ["GET", "records"],
  ["GET", "records/*"],
  ["GET", "claims"],
  ["GET", "themes"],
  ["GET", "themes/*"],
  ["POST", "themes/build"],
];

export function isAllowed(method: string, segments: string[]): boolean {
  return ALLOWED.some(([m, path]) => {
    if (m !== method) return false;
    const parts = path.split("/");
    return parts.length === segments.length && parts.every((part, i) => part === "*" || part === segments[i]);
  });
}
