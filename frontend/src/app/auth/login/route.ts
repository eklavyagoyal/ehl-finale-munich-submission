import { authEnabled, checkPassword, createSession, SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!authEnabled()) return Response.json({ ok: true });
  const body = (await request.json().catch(() => ({}))) as { password?: unknown };
  const password = typeof body.password === "string" ? body.password : "";
  if (!checkPassword(password)) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return Response.json({ detail: "Wrong password" }, { status: 401 });
  }
  const response = Response.json({ ok: true });
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  response.headers.append(
    "set-cookie",
    `${SESSION_COOKIE}=${createSession()}; Path=/; Max-Age=${SESSION_MAX_AGE}; HttpOnly; SameSite=Lax${secure}`,
  );
  return response;
}
