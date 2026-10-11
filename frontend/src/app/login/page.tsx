import { redirect } from "next/navigation";

import { LoginForm } from "@/components/login-form";
import { authEnabled } from "@/lib/session";

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const next = (await searchParams).next;
  const target = typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/";
  if (!authEnabled()) redirect(target);
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <LoginForm next={target} />
    </main>
  );
}
