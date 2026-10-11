"use client";

import { Layers } from "lucide-react";
import Link from "next/link";

import { ErrorState, LoadingRows } from "@/components/states";
import { useVehicles } from "@/lib/api/hooks";
import type { Vehicle } from "@/lib/api/types";
import { fmtCount } from "@/lib/format";
import { cn } from "cn";

// Side views as hairlines: a sedan, the long-wheelbase sedan, the larger 7 Series and the 1 Series hatch.
const SILHOUETTE: Record<string, string> = {
  G60: "M8 44 L14 34 Q40 30 58 22 Q74 14 100 14 Q122 14 140 26 L172 30 Q184 32 186 40 L186 44",
  G68: "M4 44 L10 34 Q36 30 54 22 Q72 14 104 14 Q130 14 148 26 L180 30 Q192 32 194 40 L194 44",
  G70: "M6 44 L10 32 Q36 28 56 20 Q74 12 104 12 Q130 12 150 24 L182 28 Q194 30 196 40 L196 44",
  F70: "M22 44 L26 34 Q44 30 60 22 Q74 14 98 14 Q122 14 134 22 Q146 30 158 32 Q170 34 172 44",
};
const WHEELS: Record<string, number[]> = { G60: [46, 150], G68: [44, 160], G70: [46, 160], F70: [52, 140] };

function Silhouette({ code, muted }: { code: string; muted: boolean }) {
  const body = SILHOUETTE[code];
  if (!body) return <Layers className="size-10 text-muted-foreground/60" strokeWidth={1} aria-hidden />;
  return (
    <svg viewBox="0 0 200 56" className={cn("h-12 w-full", muted ? "text-muted-foreground/40" : "text-foreground/70")} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round">
        <path d={body} />
        <line x1={4} y1={44} x2={196} y2={44} strokeOpacity={0.3} />
        {(WHEELS[code] ?? []).map((x) => (
          <circle key={x} cx={x} cy={44} r={8} fill="var(--background)" />
        ))}
      </g>
    </svg>
  );
}

export default function LandingPage() {
  const { data, error, isLoading } = useVehicles();

  return (
    <main className="mx-auto flex min-h-svh max-w-5xl flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <span className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">P</span>
          <span className="font-semibold">Parallax</span>
        </span>
        <p className="max-w-2xl text-[17px] leading-relaxed text-foreground/80">
          Parallax turns what owners really say into requirements for the next BMW, lets simulated owners and departments argue about them,
          and shows you why every agent decided what it did, so you can decide with confidence.
        </p>
      </header>

      {error && <ErrorState error={error} />}
      {isLoading && <LoadingRows />}
      {data && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((v) => (
            <VehicleCard key={v.entity_id} vehicle={v} />
          ))}
        </section>
      )}
    </main>
  );
}

function VehicleCard({ vehicle: v }: { vehicle: Vehicle }) {
  const active = v.status === "active";
  const inner = (
    <>
      <Silhouette code={v.code} muted={!active} />
      <span className="flex flex-col gap-0.5">
        <span className="flex items-baseline gap-2">
          <span className={cn("font-medium", !active && "text-muted-foreground")}>{v.name}</span>
          {!active && <span className="ml-auto text-xs text-muted-foreground">coming</span>}
        </span>
        <span className="text-xs text-muted-foreground">{v.detail}</span>
      </span>
      <span className="text-xs text-muted-foreground tabular-nums">
        {v.records ? `${fmtCount(v.records)} records` : "no data imported"}
        {v.status === "data_available" && " · not analysed yet"}
      </span>
    </>
  );
  const box = "flex flex-col gap-4 rounded-xl border p-5";
  if (!active) return <div className={cn(box, "border-dashed opacity-80")}>{inner}</div>;
  return (
    <Link href="/pipeline" className={cn(box, "transition-colors hover:border-foreground/30")}>
      {inner}
    </Link>
  );
}
