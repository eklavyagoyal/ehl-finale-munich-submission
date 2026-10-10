import { authEnabled, checkLogin, createSession, SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!authEnabled()) return Response.json({ ok: true });
  const body = (await request.json().catch(() => ({}))) as { name?: unknown; password?: unknown };
  const pm = checkLogin(typeof body.name === "string" ? body.name : "", typeof body.password === "string" ? body.password : "");
  if (!pm) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return Response.json({ detail: "Name or password is wrong" }, { status: 401 });
  }
  const response = Response.json({ ok: true, pm });
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  response.headers.append(
    "set-cookie",
    `${SESSION_COOKIE}=${createSession(pm)}; Path=/; Max-Age=${SESSION_MAX_AGE}; HttpOnly; SameSite=Lax${secure}`,
  );
  return response;
}
