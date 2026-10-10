"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm({ next }: { next: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!password) {
      setError("Enter the password.");
      return;
    }
    setBusy(true);
    setError(null);
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    }).catch(() => null);
    if (response?.ok) {
      window.location.assign(next);
      return;
    }
    setBusy(false);
    setError(response?.status === 401 ? "Wrong password." : "Sign-in failed. Try again.");
  }

  return (
    <form onSubmit={submit} className="flex w-full max-w-xs flex-col gap-5">
      <div className="flex items-center gap-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">P</span>
        <span className="flex flex-col leading-tight">
          <span className="font-semibold">Parallax</span>
          <span className="text-xs text-muted-foreground">Requirements cockpit</span>
        </span>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          autoFocus
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setError(null);
          }}
          aria-invalid={!!error}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      <Button type="submit" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
