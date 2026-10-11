"use client";

import Link from "next/link";

import { useTasks } from "@/lib/api/hooks";
import { V } from "@/lib/routes";

// "My tasks" as a counter in the top-right corner of every page.
export function TasksCounter() {
  const { data } = useTasks();
  const count = data?.length;
  return (
    <Link
      href={`${V}/tasks`}
      className="flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs text-muted-foreground hover:text-foreground"
    >
      My tasks
      <span className={count ? "font-medium text-foreground tabular-nums" : "tabular-nums"}>{count ?? "–"}</span>
    </Link>
  );
}
