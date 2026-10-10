"use client";

import { Settings } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/states";
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
import { sanitizePm, writePmCookie } from "@/lib/actor";
import { refreshAll, useMeta } from "@/lib/api/hooks";

const NAME = /^[a-z0-9][a-z0-9_-]{0,31}$/;

export function SettingsDialog({
  pm,
  onPmChange,
  canSignOut,
}: {
  pm: string;
  onPmChange: (name: string) => void;
  canSignOut: boolean;
}) {
  const router = useRouter();
  const { data: meta, error } = useMeta();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(pm);
  const [invalid, setInvalid] = useState(false);

  async function signOut() {
    await fetch("/auth/logout", { method: "POST" }).catch(() => null);
    router.replace("/login");
    router.refresh();
  }

  function save() {
    const value = name.trim().toLowerCase();
    if (!NAME.test(value)) {
      setInvalid(true);
      return;
    }
    writePmCookie(value);
    onPmChange(sanitizePm(value));
    void refreshAll();
    toast.success(`You now act as pm:${value}`);
    setOpen(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setName(pm);
          setInvalid(false);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Settings" className="text-muted-foreground">
          <Settings />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Who you are in the audit trail, and which backend this cockpit talks to.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="pm-name">Your name</Label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">pm:</span>
            <Input
              id="pm-name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setInvalid(false);
              }}
              aria-invalid={invalid}
            />
          </div>
          <p className={invalid ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
            {invalid
              ? "Use lowercase letters, digits, - or _ (up to 32 characters)."
              : "Every decision, edit and override is signed with this name."}
          </p>
        </div>

        <div className="grid gap-1.5 border-t pt-4 text-sm">
          <p className="text-[13px] text-muted-foreground">Backend</p>
          {error && <ErrorState error={error} />}
          {meta && (
            <dl className="grid grid-cols-[130px_minmax(0,1fr)] gap-y-1 text-[13px]">
              <dt className="text-muted-foreground">Status</dt>
              <dd>Connected · v{meta.version}</dd>
              <dt className="text-muted-foreground">Model mode</dt>
              <dd>{meta.llm_mode}</dd>
              <dt className="text-muted-foreground">Target vehicle</dt>
              <dd>{meta.target_model.replace(/^bmw:/, "")}</dd>
              <dt className="text-muted-foreground">Markets</dt>
              <dd>{meta.markets.join(", ")}</dd>
              <dt className="text-muted-foreground">Contents</dt>
              <dd>
                {Object.entries(meta.counts)
                  .map(([k, v]) => `${v} ${k}`)
                  .join(" · ")}
              </dd>
            </dl>
          )}
        </div>

        <DialogFooter>
          {canSignOut && (
            <Button variant="ghost" className="mr-auto" onClick={signOut}>
              Sign out
            </Button>
          )}
          <Button onClick={save}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
