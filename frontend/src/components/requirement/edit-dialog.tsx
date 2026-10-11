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
import { Textarea } from "@/components/ui/textarea";
import { editRequirement, refreshAll } from "@/lib/api/hooks";
import type { Requirement } from "@/lib/api/types";
import { humanize } from "@/lib/format";

const KANO = ["must_be", "performance", "attractive", "indifferent", "reverse", "unclear"];

interface Draft {
  title: string;
  description: string;
  customer_problem: string;
  acceptance_criteria: string;
  kano_class: string;
  benchmark_target: string;
}

function toDraft(r: Requirement): Draft {
  return {
    title: r.title,
    description: r.description,
    customer_problem: r.customer_problem,
    acceptance_criteria: r.acceptance_criteria.join("\n"),
    kano_class: r.kano_class ?? "unclear",
    benchmark_target: r.benchmark_target ?? "",
  };
}

// PATCH only what changed; the backend stores a new version and audits it.
export function EditDialog({ requirement }: { requirement: Requirement }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(() => toDraft(requirement));
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
    setError(null);
  }

  async function save() {
    const before = toDraft(requirement);
    const changes: Record<string, unknown> = {};
    for (const key of Object.keys(draft) as (keyof Draft)[]) {
      if (draft[key] === before[key]) continue;
      if (key === "acceptance_criteria") {
        changes[key] = draft[key].split("\n").map((s) => s.trim()).filter(Boolean);
      } else if (key === "benchmark_target") {
        changes[key] = draft[key].trim() || null;
      } else {
        changes[key] = draft[key];
      }
    }
    if (Object.keys(changes).length === 0) {
      setError("Change something first.");
      return;
    }
    if (!rationale.trim()) {
      setError("Every edit needs a rationale.");
      return;
    }
    setBusy(true);
    try {
      await editRequirement(requirement.id, changes, rationale.trim());
      toast.success(`Saved version ${requirement.version + 1}`);
      await refreshAll();
      setRationale("");
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setDraft(toDraft(requirement));
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit {requirement.id}</DialogTitle>
          <DialogDescription>Creates version {requirement.version + 1}. The change and your rationale go into the timeline.</DialogDescription>
        </DialogHeader>
        <div className="grid max-h-[60vh] gap-4 overflow-y-auto pr-1">
          <div className="grid gap-2">
            <Label htmlFor="edit-title">Title</Label>
            <Input id="edit-title" value={draft.title} onChange={(e) => set("title", e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="edit-description">Description</Label>
            <Textarea id="edit-description" rows={3} value={draft.description} onChange={(e) => set("description", e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="edit-problem">Customer problem</Label>
            <Textarea id="edit-problem" rows={2} value={draft.customer_problem} onChange={(e) => set("customer_problem", e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="edit-criteria">Acceptance criteria, one per line</Label>
            <Textarea id="edit-criteria" rows={3} value={draft.acceptance_criteria} onChange={(e) => set("acceptance_criteria", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-kano">Kano class</Label>
              <Select value={draft.kano_class} onValueChange={(v) => set("kano_class", v)}>
                <SelectTrigger id="edit-kano" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KANO.map((k) => (
                    <SelectItem key={k} value={k}>
                      {humanize(k)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-benchmark">Benchmark target</Label>
              <Input id="edit-benchmark" value={draft.benchmark_target} onChange={(e) => set("benchmark_target", e.target.value)} placeholder="Range of at least 600 km WLTP" />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="edit-rationale">Rationale</Label>
            <Textarea id="edit-rationale" rows={2} value={rationale} onChange={(e) => { setRationale(e.target.value); setError(null); }} placeholder="Why this change?" />
          </div>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save version"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
