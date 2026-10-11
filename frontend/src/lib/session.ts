import { createHmac, scryptSync, timingSafeEqual } from "node:crypto";

// PM sign-in without backend changes. The signed-in name becomes the X-Actor (pm:<name>).
// Modes, by env on the frontend server:
//   PARALLAX_WEB_USERS="luis:scrypt:<salt>:<hash>,lisa:<plain password>"  → one account per PM
//   PARALLAX_WEB_USER_LUIS=<password>                                     → one account per variable
//                                                                           (nexus can generate these)
//   PARALLAX_WEB_PASSWORD=<shared password>                              → any name, one shared password
//   neither                                                              → open, name from the settings dialog
// The session cookie is "<name>.<expiry>.<HMAC-SHA256>"; the key includes the secret and the account
// config, so changing a password signs everyone out.
export const SESSION_COOKIE = "parallax_session";
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7;

const NAME = /^[a-z0-9][a-z0-9_-]{0,31}$/;
const USER_VAR = /^PARALLAX_WEB_USER_([A-Za-z0-9_-]+)$/;

// PARALLAX_WEB_USER_<NAME> variables, sorted by key so the signing key is stable.
function userVars(): [string, string][] {
  return Object.entries(process.env)
    .filter((e): e is [string, string] => USER_VAR.test(e[0]) && Boolean(e[1]?.trim()))
    .sort(([a], [b]) => a.localeCompare(b));
}

function accounts(): Map<string, string> | null {
  const map = new Map<string, string>();
  for (const entry of (process.env.PARALLAX_WEB_USERS ?? "").split(/[,\n]/)) {
    const item = entry.trim();
    const colon = item.indexOf(":");
    if (colon < 1) continue;
    const name = item.slice(0, colon).trim().toLowerCase();
    const secret = item.slice(colon + 1).trim();
    if (NAME.test(name) && secret) map.set(name, secret);
  }
  for (const [key, value] of userVars()) {
    const name = USER_VAR.exec(key)![1].toLowerCase();
    if (NAME.test(name)) map.set(name, value.trim());
  }
  return map.size > 0 ? map : null;
}

export type AuthMode = "accounts" | "shared" | "off";

export function authMode(): AuthMode {
  if (accounts()) return "accounts";
  if (process.env.PARALLAX_WEB_PASSWORD) return "shared";
  return "off";
}

export function authEnabled(): boolean {
  return authMode() !== "off";
}

function key(): string {
  const { PARALLAX_WEB_SESSION_SECRET: s = "", PARALLAX_WEB_USERS: u = "", PARALLAX_WEB_PASSWORD: p = "" } = process.env;
  const vars = userVars().map(([k, v]) => `${k}=${v}`);
  return [s, u, p, ...vars].join("\u0000");
}

function sign(payload: string): string {
  return createHmac("sha256", key()).update(payload).digest("base64url");
}

function same(a: Buffer, b: Buffer): boolean {
  return a.length === b.length && timingSafeEqual(a, b);
}

function digest(value: string): Buffer {
  return createHmac("sha256", "parallax-password").update(value).digest();
}

function matches(stored: string, input: string): boolean {
  if (stored.startsWith("scrypt:")) {
    const [, salt, hash] = stored.split(":");
    if (!salt || !hash) return false;
    return same(scryptSync(input, Buffer.from(salt, "hex"), 32), Buffer.from(hash, "hex"));
  }
  return same(digest(input), digest(stored));
}

// Returns the normalised PM name on success, null otherwise.
export function checkLogin(name: string, password: string): string | null {
  const pm = name.trim().toLowerCase();
  if (!NAME.test(pm) || !password) return null;
  const mode = authMode();
  if (mode === "accounts") {
    const stored = accounts()!.get(pm);
    // Compare against a dummy when the account is unknown so timing does not reveal names.
    const ok = matches(stored ?? "scrypt:00:00", password);
    return stored && ok ? pm : null;
  }
  if (mode === "shared") return matches(process.env.PARALLAX_WEB_PASSWORD!, password) ? pm : null;
  return null;
}

export function createSession(pm: string): string {
  const payload = `${pm}.${Math.floor(Date.now() / 1000) + SESSION_MAX_AGE}`;
  return `${payload}.${sign(payload)}`;
}

export function readSession(value: string | undefined): { pm: string } | null {
  if (!value) return null;
  const [pm, expires, signature] = value.split(".");
  if (!pm || !expires || !signature || !NAME.test(pm)) return null;
  if (!same(Buffer.from(signature), Buffer.from(sign(`${pm}.${expires}`)))) return null;
  if (Number(expires) <= Date.now() / 1000) return null;
  if (authMode() === "accounts" && !accounts()!.has(pm)) return null;
  return { pm };
}

export function verifySession(value: string | undefined): boolean {
  return !authEnabled() || readSession(value) !== null;
}
