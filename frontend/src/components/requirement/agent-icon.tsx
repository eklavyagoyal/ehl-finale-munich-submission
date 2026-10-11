"use client";

import {
  BadgeCheck,
  Banknote,
  Bot,
  Building2,
  Calculator,
  Filter,
  GitMerge,
  type LucideIcon,
  PenLine,
  PenTool,
  Scale,
  Search,
  ShieldCheck,
  Swords,
  Target,
  TrendingUp,
  User,
  UserCheck,
  Users,
  Wrench,
} from "lucide-react";
import { createElement } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "cn";

const DEPT_ICON: Record<string, LucideIcon> = {
  design: PenTool,
  engineering: Wrench,
  sales: TrendingUp,
  finance: Banknote,
  quality: BadgeCheck,
  "product-management": Target,
};

const AGENT_ICON: Record<string, LucideIcon> = {
  "agent:research": Search,
  "agent:verifier": ShieldCheck,
  "agent:synthesizer": GitMerge,
  "agent:challenger": Swords,
  "agent:drafter": PenLine,
  "agent:condenser": Filter,
};

// One icon per agent id; the same faces appear in the decision path and the flow view.
export function agentIcon(agentId: string, kind?: string): LucideIcon {
  const [prefix, rest = ""] = agentId.split(":");
  if (AGENT_ICON[agentId]) return AGENT_ICON[agentId];
  if (prefix === "persona" || kind === "persona") return User;
  if (agentId === "tinytroupe") return Users;
  if (prefix === "dept" || kind === "department") return DEPT_ICON[rest.replace(/-(us|eu|cn)$/, "")] ?? Building2;
  if (prefix === "judge" || kind === "judge") return Scale;
  if (prefix === "code" || kind === "code") return Calculator;
  if (prefix === "pm" || kind === "human") return UserCheck;
  return Bot;
}

export function AgentAvatar({ id, name, kind, className }: { id: string; name: string; kind?: string; className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "flex size-6 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground",
            kind === "human" && "border-foreground bg-foreground text-background",
            className,
          )}
        >
          {createElement(agentIcon(id, kind), { className: "size-3", strokeWidth: 1.5, "aria-hidden": true })}
        </span>
      </TooltipTrigger>
      <TooltipContent>{name}</TooltipContent>
    </Tooltip>
  );
}

// At most five faces, the rest as "+n", so a council of 12 owners stays one glance.
export function AgentStack({ agents, max = 5 }: { agents: { id: string; name: string; kind?: string }[]; max?: number }) {
  const shown = agents.slice(0, max);
  return (
    <span className="flex items-center -space-x-1.5">
      {shown.map((a) => (
        <AgentAvatar key={a.id} id={a.id} name={a.name} kind={a.kind} className="ring-2 ring-background" />
      ))}
      {agents.length > max && <span className="pl-2.5 text-[11px] text-muted-foreground tabular-nums">+{agents.length - max}</span>}
    </span>
  );
}
