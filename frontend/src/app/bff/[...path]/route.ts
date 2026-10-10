import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

import { ACTOR_COOKIE, sanitizePm } from "@/lib/actor";

// Server-side proxy to the Parallax API. The browser only ever talks to /bff; the token stays here.
// /bff/requirements and /bff/api/requirements both map to ${PARALLAX_API_URL}/api/requirements,
// because the generated client uses the spec's /api/... paths.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const SAFE_SEGMENT = /^[A-Za-z0-9._:~@-]+$/;

async function proxy(request: NextRequest, context: RouteContext<"/bff/[...path]">) {
  const { path } = await context.params;
  const segments = path[0] === "api" ? path.slice(1) : path;
  if (segments.length === 0 || segments.some((s) => s === "." || s === ".." || !SAFE_SEGMENT.test(s))) {
    return Response.json({ detail: "Invalid API path" }, { status: 400 });
  }

  const base = process.env.PARALLAX_API_URL?.replace(/\/+$/, "");
  if (!base) {
    return Response.json({ detail: "PARALLAX_API_URL is not configured on the frontend server" }, { status: 500 });
  }

  const target = new URL(`${base}/api/${segments.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers({ accept: request.headers.get("accept") ?? "application/json" });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const token = process.env.PARALLAX_API_TOKEN;
  if (token) headers.set("authorization", `Bearer ${token}`);
  const jar = await cookies();
  headers.set("x-actor", `pm:${sanitizePm(jar.get(ACTOR_COOKIE)?.value)}`);

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(target, { method: request.method, headers, body, cache: "no-store", redirect: "manual" });
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    console.error(`[bff] ${request.method} ${target.pathname} failed: ${reason}`);
    return Response.json({ detail: `Backend not reachable (${reason})` }, { status: 502 });
  }

  const out = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) out.set("content-type", upstreamType);
  out.set("cache-control", "no-store");
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
