// The PM identity travels as a cookie; the BFF turns it into `X-Actor: pm:<name>`.
export const ACTOR_COOKIE = "parallax_pm";
export const DEFAULT_PM = "luis";

const NAME = /^[a-z0-9][a-z0-9_-]{0,31}$/;

export function sanitizePm(value: string | undefined | null): string {
  const name = (value ?? "").trim().toLowerCase();
  return NAME.test(name) ? name : DEFAULT_PM;
}

export function writePmCookie(name: string) {
  document.cookie = `${ACTOR_COOKIE}=${encodeURIComponent(sanitizePm(name))}; path=/; max-age=31536000; samesite=lax`;
}
