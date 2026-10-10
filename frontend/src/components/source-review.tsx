"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { refreshAll, reviewSource } from "@/lib/api/hooks";
import type { Tone } from "@/lib/format";

export const REVIEW_TONE: Record<string, Tone> = { accepted: "green", rejected: "red", pending: "amber" };

// Evidence acceptance (separate from approving requirements). A note is required for the audit trail.
export function SourceReview({ sourceId, title, status }: { sourceId: string; title: string; status: string }) {
  const [deciding, setDeciding] = useState<"accepted" | "rejected" | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    if (!deciding) return;
    if (!note.trim()) {
      toast.error("Add a short note why.");
      return;
    }
    setBusy(true);
    try {
      await reviewSource(sourceId, deciding, note.trim());
      toast.success(`${title}: ${deciding}`);
      await refreshAll();
      setDeciding(null);
      setNote("");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (deciding) {
    return (
      <span className="flex items-center gap-1.5">
        <Input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={deciding === "accepted" ? "Why can it be used?" : "Why rejected?"}
          aria-label="Review note"
          className="h-7 w-44"
          autoFocus
        />
        <Button size="xs" onClick={save} disabled={busy}>
          {busy ? "…" : "Save"}
        </Button>
        <Button size="xs" variant="ghost" onClick={() => setDeciding(null)}>
          Cancel
        </Button>
      </span>
    );
  }
  return (
    <span className="flex justify-end gap-1">
      {status !== "accepted" && (
        <Button size="xs" variant="outline" onClick={() => setDeciding("accepted")}>
          Accept
        </Button>
      )}
      {status !== "rejected" && (
        <Button size="xs" variant="ghost" onClick={() => setDeciding("rejected")}>
          Reject
        </Button>
      )}
    </span>
  );
}
