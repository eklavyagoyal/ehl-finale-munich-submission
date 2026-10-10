import { SESSION_COOKIE } from "@/lib/session";

export const dynamic = "force-dynamic";

export function POST() {
  const response = Response.json({ ok: true });
  response.headers.append("set-cookie", `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
  return response;
}
