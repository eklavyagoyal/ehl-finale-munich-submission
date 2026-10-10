"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { buildThemes, draftRequirements, refreshAll } from "@/lib/api/hooks";
import type { Signal } from "@/lib/api/types";

// The AI drafts one candidate requirement per selected signal, with cited quotes. The PM reviews every draft.
export function DraftSelectedDialog({ market, selected, onDone }: { market: string | null; selected: Signal[]; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const keys = selected.map((s) => s.feature_key);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      // The drafter caps by limit after filtering to the selected features, so limit = selection size.
      const result = await draftRequirements(market, Math.min(Math.max(keys.length, 1), 30), keys);
      const created = result?.created?.length ?? 0;
      if (created > 0) toast.success(`${created} new requirement draft${created === 1 ? "" : "s"}`);
      else toast.info("No new drafts: the selected signals already have a requirement, or their evidence is not accepted yet.");
      await refreshAll();
      setOpen(false);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" disabled={keys.length === 0}>
          Draft requirements{keys.length > 0 ? ` (${keys.length})` : ""}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Draft requirements</DialogTitle>
          <DialogDescription>
            The drafter writes one candidate requirement per signal for {market ?? "all markets pooled"}, citing the reviews behind it. You review
            every draft under Decision.
          </DialogDescription>
        </DialogHeader>
        <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto text-sm">
          {selected.map((s) => (
            <li key={s.feature_key} className="flex justify-between gap-3">
              <span className="truncate">{s.label}</span>
              <span className="text-muted-foreground tabular-nums">{s.reviews} reviews</span>
            </li>
          ))}
        </ul>
        {keys.length > 30 && <p className="text-sm text-muted-foreground">Only the first 30 are drafted in one go.</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button onClick={run} disabled={busy}>
            {busy ? "Drafting…" : "Draft"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Recomputes the deterministic signals (counts per feature × market) from accepted evidence.
export function RebuildSignalsButton() {
  const [busy, setBusy] = useState(false);
  async function rebuild() {
    setBusy(true);
    try {
      await buildThemes();
      toast.success("Signals rebuilt from the accepted evidence");
      await refreshAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Button size="sm" variant="outline" onClick={rebuild} disabled={busy}>
      {busy ? "Rebuilding…" : "Rebuild signals"}
    </Button>
  );
}
