"use client";

import { useSearchParams } from "next/navigation";
import { createContext, useContext, useState } from "react";

import { useRequirement } from "@/lib/api/hooks";
import type { RequirementDetail } from "@/lib/api/types";

interface RequirementState {
  id: string;
  detail: RequirementDetail | undefined;
  error: unknown;
  isLoading: boolean;
  // The run the screen follows: one started here, one from ?run=, or the requirement's last run.
  runId: string | null;
  followRun: (runId: string) => void;
}

const RequirementContext = createContext<RequirementState | null>(null);

export function RequirementProvider({ id, children }: { id: string; children: React.ReactNode }) {
  const { data, error, isLoading } = useRequirement(id);
  const fromUrl = useSearchParams().get("run");
  const [started, setStarted] = useState<string | null>(null);
  const runId = started ?? fromUrl ?? data?.requirement.last_run_id ?? data?.latest_run_id ?? null;

  return (
    <RequirementContext.Provider value={{ id, detail: data, error, isLoading, runId, followRun: setStarted }}>
      {children}
    </RequirementContext.Provider>
  );
}

export function useRequirementContext() {
  const value = useContext(RequirementContext);
  if (!value) throw new Error("useRequirementContext needs a RequirementProvider");
  return value;
}
