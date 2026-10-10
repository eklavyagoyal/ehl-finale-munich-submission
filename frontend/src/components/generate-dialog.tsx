"use client";

import { Sparkles } from "lucide-react";
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

// Rebuilds the theme signals from the current evidence, then lets the AI draft candidate requirements.
export function GenerateDialog({ variant = "outline" }: { variant?: "outline" | "default" }) {
  const { data: meta } = useMeta();
  const [open, setOpen] = useState(false);
  const [market, setMarket] = useState("US");
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
      await buildThemes();
      await draftRequirements(market === "all" ? null : market, count);
      toast.success("New requirement drafts are ready");
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
        <Button variant={variant} size="sm">
          <Sparkles data-icon="inline-start" />
          Generate
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Generate requirements</DialogTitle>
          <DialogDescription>
            Rebuilds the signals from the imported evidence, then the AI drafts candidates. You review every draft.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="gen-market">Market</Label>
            <Select value={market} onValueChange={setMarket}>
              <SelectTrigger id="gen-market" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(meta?.markets ?? ["US", "EU", "CN"]).map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
                <SelectItem value="all">All markets pooled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="gen-limit">How many</Label>
            <Input id="gen-limit" inputMode="numeric" value={limit} onChange={(e) => setLimit(e.target.value)} />
          </div>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button onClick={run} disabled={busy}>
            {busy ? "Drafting…" : "Draft requirements"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
