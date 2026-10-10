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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { buildThemes, draftRequirements, refreshAll, useMeta } from "@/lib/api/hooks";

// The AI drafts candidate requirements from the strongest signals that have no requirement yet.
export function DraftDialog({ defaultMarket = "US" }: { defaultMarket?: string }) {
  const { data: meta } = useMeta();
  const [open, setOpen] = useState(false);
  const [market, setMarket] = useState(defaultMarket);
  const [limit, setLimit] = useState("5");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    const count = Number(limit);
    if (!Number.isInteger(count) || count < 1 || count > 30) {
      setError("Enter a number between 1 and 30.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await draftRequirements(market === "pooled" ? null : market, count);
      const created = result?.created?.length ?? 0;
      if (created > 0) toast.success(`${created} new requirement draft${created === 1 ? "" : "s"}`);
      else toast.info("No new drafts: every strong signal already has a requirement, or there is no accepted evidence yet.");
      await refreshAll();
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Draft requirements</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Draft requirements</DialogTitle>
          <DialogDescription>
            The drafter turns the strongest signals of one market into candidate requirements with cited quotes. You review every draft.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="draft-market">Market</Label>
            <Select value={market} onValueChange={setMarket}>
              <SelectTrigger id="draft-market" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(meta?.markets ?? ["US", "EU", "CN"]).map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
                <SelectItem value="pooled">All markets pooled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="draft-limit">At most</Label>
            <Input id="draft-limit" inputMode="numeric" value={limit} onChange={(e) => setLimit(e.target.value)} />
          </div>
        </div>
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
