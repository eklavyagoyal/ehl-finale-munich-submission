"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { buildThemes, condenseSignals, draftRequirements, refreshAll, useRun } from "@/lib/api/hooks";
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

// "Update" on the Processing page: recount the signals (code, cheap) or condense findings (model, runs in
// the background with a confirm step). The menu follows a running condense and refreshes when it is done.
export function UpdateMenu() {
  const [rebuilding, setRebuilding] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useRun(runId);
  const status = run.data?.run.status;
  const condensing = !!runId && (!status || status === "queued" || status === "running");
  const settled = useRef<string | null>(null);

  useEffect(() => {
    if (!runId || !status || status === "queued" || status === "running" || settled.current === runId) return;
    settled.current = runId;
    if (status === "completed") toast.success("Findings condensed");
    else toast.warning(`Condensing ${status}${run.data?.run.error ? `: ${run.data.run.error}` : ""}`);
    void refreshAll();
  }, [runId, status, run.data?.run.error]);

  async function rebuild() {
    setRebuilding(true);
    try {
      await buildThemes();
      toast.success("Signals recounted from the accepted evidence");
      await refreshAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setRebuilding(false);
    }
  }

  async function condense() {
    setBusy(true);
    try {
      const result = await condenseSignals(["US", "EU", "CN", null]);
      setRunId(result.run_id);
      setConfirm(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="sm" variant="outline" disabled={rebuilding}>
            {rebuilding ? "Recounting…" : condensing ? (status === "queued" ? "Waiting…" : "Condensing…") : "Update"}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => void rebuild()}>Recount signals</DropdownMenuItem>
          <DropdownMenuItem disabled={condensing} onSelect={() => setConfirm(true)}>
            Condense findings…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Condense findings</DialogTitle>
            <DialogDescription>
              A model groups the reviews behind the top 8 signals per kind into concrete findings, for the US, Europe, China and all markets.
              The counts come from code. This uses the model budget and runs in the background.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={condense} disabled={busy}>
              {busy ? "Starting…" : "Condense"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
