import { createHmac, timingSafeEqual } from "node:crypto";

// Optional password gate. It is active only when PARALLAX_WEB_PASSWORD is set (nexus env); without it
// the cockpit stays open as before. The session cookie is an expiry signed with HMAC-SHA256, and the
// key includes the password, so changing the password signs everyone out.
export const SESSION_COOKIE = "parallax_session";
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7;

export function authEnabled(): boolean {
  return Boolean(process.env.PARALLAX_WEB_PASSWORD);
}

function key(): string {
  return `${process.env.PARALLAX_WEB_SESSION_SECRET ?? ""}:${process.env.PARALLAX_WEB_PASSWORD ?? ""}`;
}

function sign(payload: string): string {
  return createHmac("sha256", key()).update(payload).digest("base64url");
}

function same(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

export function createSession(): string {
  const expires = String(Math.floor(Date.now() / 1000) + SESSION_MAX_AGE);
  return `${expires}.${sign(expires)}`;
}

export function verifySession(value: string | undefined): boolean {
  if (!authEnabled()) return true;
  if (!value) return false;
  const [expires, signature] = value.split(".");
  if (!expires || !signature || !same(signature, sign(expires))) return false;
  return Number(expires) > Date.now() / 1000;
}

export function checkPassword(input: string): boolean {
  const expected = process.env.PARALLAX_WEB_PASSWORD ?? "";
  if (!expected) return false;
  const digest = (s: string) => createHmac("sha256", "parallax-password").update(s).digest("hex");
  return same(digest(input), digest(expected));
}
