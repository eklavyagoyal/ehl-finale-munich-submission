"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";

import { TasksCounter } from "@/components/tasks-counter";
import { useVehicles } from "@/lib/api/hooks";
import { cn } from "cn";
import { V } from "@/lib/routes";

export interface Crumb {
  label: string;
  href?: string;
}

export interface MarketFilter {
  value: string | null;
  // Without onChange the chip only shows the market (e.g. a requirement's market).
  onChange?: (market: string | null) => void;
  options?: (string | null)[];
}

// The only header: "Overview › G60 › <Stage> › <Item>" at the top edge, then the market chip, page actions
// and the tasks counter on the right. Every crumb except the last is a link. The market is a filter, not a crumb.
export function PageHeader({ crumbs, market, children }: { crumbs: Crumb[]; market?: MarketFilter; children?: React.ReactNode }) {
  const { data: vehicles } = useVehicles();
  const code = (vehicles?.active ?? "bmw:G60").split(":").pop() ?? "G60";
  const trail: Crumb[] = [{ label: "Overview", href: "/" }, { label: code, href: V }, ...crumbs];

  return (
    <div className="flex min-h-12 flex-wrap items-center gap-3 py-2">
      <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-[13px] text-muted-foreground">
        {trail.map((crumb, index) => {
          const last = index === trail.length - 1;
          return (
            <Fragment key={`${crumb.label}-${index}`}>
              {index > 0 && <ChevronRight className="size-3.5 text-muted-foreground/60" aria-hidden />}
              {crumb.href && !last ? (
                <Link href={crumb.href} className="hover:text-foreground">
                  {crumb.label}
                </Link>
              ) : (
                <span className={last ? "font-medium text-foreground" : undefined}>{crumb.label}</span>
              )}
            </Fragment>
          );
        })}
      </nav>
      {market && <MarketChips {...market} />}
      <div className="ml-auto flex items-center gap-2">
        {children}
        <TasksCounter />
      </div>
    </div>
  );
}

function MarketChips({ value, onChange, options = ["US", "EU", "CN", null] }: MarketFilter) {
  if (!onChange) {
    return <span className="rounded-full border px-2 py-0.5 font-mono text-[11px] text-muted-foreground">{value ?? "All markets"}</span>;
  }
  return (
    <div role="radiogroup" aria-label="Market" className="flex items-center rounded-full border p-0.5">
      {options.map((m) => (
        <button
          key={m ?? "all"}
          type="button"
          role="radio"
          aria-checked={value === m}
          onClick={() => onChange(m)}
          className={cn(
            "h-6 rounded-full px-2.5 text-[11px]",
            value === m ? "bg-foreground font-medium text-background" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {m ?? "All"}
        </button>
      ))}
    </div>
  );
}
