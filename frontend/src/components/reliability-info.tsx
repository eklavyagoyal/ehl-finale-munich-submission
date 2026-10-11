"use client";

import { Info } from "lucide-react";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";

// The validation results as the backend reports them (backend/API.md), shown instead of hidden.
export function ReliabilityInfo() {
  return (
    <HoverCard openDelay={100} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button type="button" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <Info className="size-3.5" aria-hidden />
          How reliable is this?
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="end" className="w-80 text-xs">
        <p className="mb-2 font-medium">What the validation runs showed</p>
        <ul className="flex flex-col gap-1.5">
          <li>
            <span className="font-medium">Customer council is stable:</span> same verdict 90 % of the time on a repeat run, and it rejects decoys.
          </li>
          <li>
            <span className="font-medium">US owners</span> match the BMW customer study moderately (rho about 0.5–0.6).
          </li>
          <li>
            <span className="font-medium">EU</span> is weak, <span className="font-medium">China</span> cannot be tested.
          </li>
          <li>
            <span className="font-medium">Company council</span> verdicts rarely differ: read its arguments and tensions, not the verdict counts.
          </li>
        </ul>
        <p className="mt-2 text-muted-foreground">Simulated views are hypotheses. Real reviews carry the evidence.</p>
      </HoverCardContent>
    </HoverCard>
  );
}
