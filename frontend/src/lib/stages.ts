import { Database, Filter, Gavel, MessageSquareText, UsersRound, type LucideIcon } from "lucide-react";

import type { StageKey, StageStatus } from "@/lib/api/types";
import { V } from "@/lib/routes";

// The PM's path, left to right. The sidebar and the start page both follow this order.
export const STAGES: { key: StageKey; title: string; href: string; icon: LucideIcon }[] = [
  { key: "sources", title: "Sources", href: `${V}/sources`, icon: Database },
  { key: "processing", title: "Processing", href: `${V}/processing`, icon: Filter },
  { key: "signals", title: "Signals", href: `${V}/signals`, icon: MessageSquareText },
  { key: "experts", title: "Expert pipeline", href: `${V}/experts`, icon: UsersRound },
  { key: "decision", title: "Decision", href: `${V}/decision`, icon: Gavel },
];

export const STAGE_HREF = Object.fromEntries(STAGES.map((s) => [s.key, s.href])) as Record<StageKey, string>;

export const STATUS_LABEL: Record<StageStatus, string> = { todo: "To do", in_progress: "In progress", done: "Done" };
