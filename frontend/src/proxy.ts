import { type NextRequest, NextResponse } from "next/server";

import { authEnabled, SESSION_COOKIE, verifySession } from "@/lib/session";

const OPEN = new Set(["/login", "/auth/login", "/health"]);

// Sends visitors without a valid session to /login once a password is configured.
// The BFF checks the session again itself, so this is only the first line.
export function proxy(request: NextRequest) {
  if (!authEnabled()) return NextResponse.next();
  const { pathname, search } = request.nextUrl;
  if (OPEN.has(pathname)) return NextResponse.next();
  if (verifySession(request.cookies.get(SESSION_COOKIE)?.value)) return NextResponse.next();
  if (pathname.startsWith("/bff/")) return NextResponse.json({ detail: "Sign in first" }, { status: 401 });
  const login = new URL("/login", request.url);
  if (pathname !== "/") login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
