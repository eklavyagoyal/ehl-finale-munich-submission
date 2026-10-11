"use client";

import { Clock, FileText, LayoutGrid, Play, Route, Scale, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { ToneBadge } from "@/components/tone-badge";
import { Button } from "@/components/ui/button";
import { refreshAll, startRun, useRequirementAudit, useRun } from "@/lib/api/hooks";
import { humanize, statusTone } from "@/lib/format";
import { cn } from "cn";

import { useRequirementContext } from "./context";
import { DecisionDialog } from "./decision-dialog";
import { EditDialog } from "./edit-dialog";
import { OriginTrail } from "./origin-trail";
import { RunProgress } from "./run-progress";

export function RequirementShell({ children }: { children: React.ReactNode }) {
  const { id, detail, error, isLoading, runId } = useRequirementContext();
  const { data: audit } = useRequirementAudit(id);
  const pathname = usePathname();
  const base = `/requirements/${encodeURIComponent(id)}`;
  const requirement = detail?.requirement;

  const tabs = [
    { href: base, label: "Decision path", icon: Route },
    { href: `${base}/councils`, label: "Councils", icon: Scale },
    { href: `${base}/overview`, label: "Overview", icon: LayoutGrid },
    { href: `${base}/simulation`, label: "Simulation", icon: Users },
    { href: `${base}/evidence`, label: "Evidence", icon: FileText, count: detail?.evidence.length },
    { href: `${base}/timeline`, label: "Timeline", icon: Clock, count: audit?.length },
  ];

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Decision", href: "/requirements" }, { label: id }]}
        market={requirement ? { value: requirement.market } : undefined}
      />

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows rows={3} />}

      {requirement && (
        <>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-[22px] font-semibold tracking-tight">{requirement.title}</h1>
            <ToneBadge tone={statusTone(requirement.status)}>{humanize(requirement.status)}</ToneBadge>
            <div className="ml-auto flex items-center gap-1.5">
              <RunButton />
              <EditDialog requirement={requirement} />
              <DecisionDialog />
            </div>
          </div>
          <OriginTrail requirement={requirement} />
          <RunProgress runId={runId} />

          <nav aria-label="Requirement views" className="-ml-2.5 mt-4 flex flex-wrap gap-1">
            {tabs.map((tab) => {
              const active = tab.href === base ? pathname === base : pathname.startsWith(tab.href);
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex h-8 items-center gap-2 rounded-lg px-2.5 text-[13px]",
                    active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <tab.icon className="size-[15px]" strokeWidth={1.5} aria-hidden />
                  {tab.label}
                  {tab.count !== undefined && <span className="font-normal text-muted-foreground/70">{tab.count}</span>}
                </Link>
              );
            })}
          </nav>

          <div className="mt-7">{children}</div>
        </>
      )}
    </>
  );
}

export function RunButton() {
  const router = useRouter();
  const { id, runId, followRun } = useRequirementContext();
  const { data: run } = useRun(runId);
  const [busy, setBusy] = useState(false);
  const active = run?.run.status === "queued" || run?.run.status === "running";

  async function start() {
    setBusy(true);
    try {
      const created = await startRun([id]);
      followRun(created.id);
      toast.success("Parallax run started");
      await refreshAll();
      router.push(`/requirements/${encodeURIComponent(id)}/simulation?run=${created.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button size="sm" variant="outline" onClick={start} disabled={busy || active}>
      <Play data-icon="inline-start" />
      {active ? "Running…" : busy ? "Starting…" : "Run Parallax"}
    </Button>
  );
}
