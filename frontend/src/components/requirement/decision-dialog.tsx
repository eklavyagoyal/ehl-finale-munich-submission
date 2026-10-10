"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ToneBadge } from "@/components/tone-badge";
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
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { decide, overrideGate, refreshAll, useMeta } from "@/lib/api/hooks";
import { gateTone, humanize } from "@/lib/format";
import { cn } from "cn";

import { useRequirementContext } from "./context";

type Action = "approve" | "reject" | "challenge" | "defer";

const ACTION_LABEL: Record<string, string> = {
  approve: "Approve",
  reject: "Reject",
  challenge: "Challenge",
  defer: "Postpone",
};

export function DecisionDialog() {
  const router = useRouter();
  const { id, detail, followRun } = useRequirementContext();
  const { data: meta } = useMeta();
  const actions = (meta?.enums.pm_actions ?? ["approve", "reject", "challenge", "defer"]) as Action[];

  const [open, setOpen] = useState(false);
  const [action, setAction] = useState<Action>("approve");
  const [rationale, setRationale] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);

  const recommendation = detail?.recommendation;
  const openGates = Object.entries(detail?.gates ?? {}).filter(([gate, g]) => gate !== "pm_review" && g.value !== "pass");

  async function submit() {
    if (!rationale.trim()) {
      setError("Write a rationale. Every decision needs one.");
      return;
    }
    if (action === "challenge" && !question.trim()) {
      setError("Ask the question the agents should re-examine.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await decide(id, {
        action,
        rationale: rationale.trim(),
        challenge_question: action === "challenge" ? question.trim() : undefined,
      });
      toast.success(`${ACTION_LABEL[action]} recorded for ${id}`);
      await refreshAll();
      setOpen(false);
      setRationale("");
      setQuestion("");
      setBlocked(null);
      if (result.followup_run_id) {
        followRun(result.followup_run_id);
        router.push(`/requirements/${id}/simulation?run=${result.followup_run_id}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setBlocked(e.detail);
        await refreshAll();
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setError(null);
          setBlocked(null);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">Decide</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Decide on {id}</DialogTitle>
          <DialogDescription>
            {recommendation
              ? `The agents suggest “${humanize(recommendation.recommendation)}”. It is a proposal; you decide.`
              : "No agent recommendation yet. You can still decide."}
          </DialogDescription>
        </DialogHeader>

        <div className="-ml-1 flex flex-wrap gap-1" role="radiogroup" aria-label="Decision">
          {actions.map((a) => (
            <button
              key={a}
              type="button"
              role="radio"
              aria-checked={action === a}
              onClick={() => {
                setAction(a);
                setBlocked(null);
              }}
              className={cn(
                "h-8 rounded-lg px-3 text-[13px]",
                action === a ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {ACTION_LABEL[a] ?? humanize(a)}
            </button>
          ))}
        </div>

        {action === "challenge" && (
          <div className="grid gap-2">
            <Label htmlFor="challenge-question">What should the agents re-examine?</Label>
            <Textarea
              id="challenge-question"
              rows={2}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                setError(null);
              }}
              placeholder="Which assumption should the agents test again?"
            />
          </div>
        )}

        <div className="grid gap-2">
          <Label htmlFor="rationale">Rationale</Label>
          <Textarea
            id="rationale"
            rows={3}
            value={rationale}
            onChange={(e) => {
              setRationale(e.target.value);
              setError(null);
            }}
            placeholder="Why do you decide this way?"
            aria-invalid={!!error && !rationale.trim()}
          />
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {blocked && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950">
            <p className="font-medium text-amber-900 dark:text-amber-100">Blocked by a gate</p>
            <p className="mt-0.5 text-amber-900/80 dark:text-amber-100/80">{blocked}</p>
            <div className="mt-3 flex flex-col gap-2">
              {openGates.length === 0 && <p className="text-xs text-muted-foreground">Gates refreshed. Try again.</p>}
              {openGates.map(([gate, g]) => (
                <GateOverride key={gate} requirementId={id} gate={gate} value={g.value} reason={g.reason} />
              ))}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button onClick={submit} disabled={busy}>
            {busy ? "Saving…" : ACTION_LABEL[action]}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function GateOverride({ requirementId, gate, value, reason }: { requirementId: string; gate: string; value: string; reason: string }) {
  const { data: meta } = useMeta();
  const [open, setOpen] = useState(false);
  const [next, setNext] = useState<"pass" | "fail" | "unknown">("pass");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!rationale.trim()) {
      setError("A gate override needs a rationale.");
      return;
    }
    setBusy(true);
    try {
      await overrideGate(requirementId, gate, { value: next, rationale: rationale.trim() });
      toast.success(`Gate ${humanize(gate)} set to ${next}`);
      await refreshAll();
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-md bg-background p-2.5">
      <div className="flex items-center gap-2 text-[13px]">
        <span className="font-medium">{humanize(gate)}</span>
        <ToneBadge tone={gateTone(value)}>{value}</ToneBadge>
        {!open && (
          <Button size="xs" variant="outline" className="ml-auto" onClick={() => setOpen(true)}>
            Override
          </Button>
        )}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{reason}</p>
      {open && (
        <div className="mt-2 grid gap-2">
          <Select value={next} onValueChange={(v) => setNext(v as typeof next)}>
            <SelectTrigger size="sm" className="w-32" aria-label="New gate value">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(meta?.enums.gate_values ?? ["pass", "fail", "unknown"]).map((v) => (
                <SelectItem key={v} value={v}>
                  {v}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Textarea
            rows={2}
            value={rationale}
            onChange={(e) => {
              setRationale(e.target.value);
              setError(null);
            }}
            placeholder="Why do you override this gate?"
            aria-label="Override rationale"
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2">
            <Button size="sm" onClick={save} disabled={busy}>
              {busy ? "Saving…" : "Save override"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
