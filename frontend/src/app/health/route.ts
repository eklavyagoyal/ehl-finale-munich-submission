// Liveness probe for nexus. No auth and no backend call, so it stays green while the API is down.
export const dynamic = "force-static";

export function GET() {
  return Response.json({ status: "ok" });
}
