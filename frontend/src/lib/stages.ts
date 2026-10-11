import { Filter, Gavel, MessageSquareText, UsersRound, type LucideIcon } from "lucide-react";

import type { StageKey, StageStatus } from "@/lib/api/types";
import { V } from "@/lib/routes";

// The vehicle's pipeline, left to right, as in the sidebar. Sources are not part of it: they live under Data.
export const STAGES: { key: StageKey; title: string; href: string; icon: LucideIcon }[] = [
  { key: "processing", title: "Processing", href: `${V}/processing`, icon: Filter },
  { key: "signals", title: "Signals", href: `${V}/signals`, icon: MessageSquareText },
  { key: "experts", title: "Expert pipeline", href: `${V}/experts`, icon: UsersRound },
  { key: "decision", title: "Decision", href: `${V}/decision`, icon: Gavel },
];

// Sources live once, under Data; the vehicle's Sources card opens them filtered to the vehicle.
export const STAGE_HREF = {
  sources: "/sources?scope=target",
  ...Object.fromEntries(STAGES.map((s) => [s.key, s.href])),
} as Record<StageKey, string>;

export const STATUS_LABEL: Record<StageStatus, string> = { todo: "To do", in_progress: "In progress", done: "Done" };
