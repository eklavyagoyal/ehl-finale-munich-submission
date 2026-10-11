"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { createContext, useContext, useState } from "react";

import { ErrorState, LoadingRows } from "@/components/states";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ApiError } from "@/lib/api/client";
import { useLlmCallDetail } from "@/lib/api/hooks";
import type { LlmCallDetail } from "@/lib/api/types";
import { fmtCount, fmtDuration, humanize } from "@/lib/format";
import { cn } from "cn";

// Any call dot (lanes or flow) can open its call here; one side panel for the whole app.
const OpenCall = createContext<(callId: number) => void>(() => {});

export function useOpenCall() {
  return useContext(OpenCall);
}

export function CallPanelProvider({ children }: { children: React.ReactNode }) {
  const [callId, setCallId] = useState<number | null>(null);
  return (
    <OpenCall.Provider value={setCallId}>
      {children}
      <Sheet open={callId != null} onOpenChange={(open) => !open && setCallId(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          {callId != null && <CallBody callId={callId} />}
        </SheetContent>
      </Sheet>
    </OpenCall.Provider>
  );
}

function CallBody({ callId }: { callId: number }) {
  const { data, error, isLoading } = useLlmCallDetail(callId);
  if (error instanceof ApiError && error.status === 404) {
    return (
      <SheetHeader>
        <SheetTitle>Call {callId}</SheetTitle>
        <SheetDescription>This call was not found.</SheetDescription>
      </SheetHeader>
    );
  }
  if (error) return <div className="p-4"><ErrorState error={error} /></div>;
  if (isLoading || !data) return <div className="p-4"><LoadingRows /></div>;
  return <CallDetailView call={data} />;
}

// Visible: who, what for and one line. Prompt, answer and sources open on click.
function CallDetailView({ call }: { call: LlmCallDetail }) {
  const sources = call.citations.length + call.input_record_ids.length;
  return (
    <div className="flex flex-col gap-5 px-4 pb-6">
      <SheetHeader className="px-0">
        <SheetTitle>
          {call.agent_name} <span className="font-normal text-muted-foreground">· {humanize(call.purpose)}</span>
        </SheetTitle>
        <SheetDescription>{call.summary ?? call.note ?? "No summary for this call."}</SheetDescription>
      </SheetHeader>

      <p className="text-xs text-muted-foreground tabular-nums">
        {call.model} · {fmtCount(call.input_tokens)} in · {fmtCount(call.output_tokens)} out · {fmtDuration(call.latency_ms / 1000)}
        {call.status !== "ok" && <span className="text-red-600"> · {call.status}</span>}
      </p>
      {call.error && <p className="text-xs text-red-700 dark:text-red-300">{call.error}</p>}

      <Fold title="Prompt">
        {call.prompt.system && <Mono label="System" text={call.prompt.system} />}
        {call.prompt.user && <Mono label="User" text={call.prompt.user} />}
        {!call.prompt.system && !call.prompt.user && <p className="text-xs text-muted-foreground">No prompt stored.</p>}
      </Fold>

      <Fold title="Answer">
        {call.note && call.response == null ? <p className="text-xs text-muted-foreground">{call.note}</p> : <Answer value={call.response} />}
      </Fold>

      <Fold title={`Sources${sources ? ` · ${sources}` : ""}`}>
        {sources === 0 && <p className="text-xs text-muted-foreground">This call saw no records and cited no web sources.</p>}
        {call.citations.map((c) => (
          <a key={c.url} href={c.url} target="_blank" rel="noreferrer noopener" className="block truncate text-[13px] hover:underline">
            {c.title || c.url}
          </a>
        ))}
        {call.input_record_ids.length > 0 && (
          <div className="flex flex-col gap-0.5">
            {call.input_record_ids.slice(0, 20).map((id) => (
              <Link key={id} href={`/sources?tab=records&ids=${encodeURIComponent(id)}`} className="truncate font-mono text-xs text-muted-foreground hover:underline">
                {id}
              </Link>
            ))}
            {call.input_record_ids.length > 20 && (
              <Link href={`/sources?tab=records&ids=${encodeURIComponent(call.input_record_ids.join(","))}`} className="text-xs hover:underline">
                All {call.input_record_ids.length} records
              </Link>
            )}
          </div>
        )}
      </Fold>
    </div>
  );
}

function Fold({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="border-t pt-3">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-center gap-1.5 text-[13px] font-medium">
        <ChevronDown className={cn("size-3.5 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
        {title}
      </button>
      {open && <div className="mt-2 flex flex-col gap-3">{children}</div>}
    </section>
  );
}

function Mono({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs text-muted-foreground">{label}</p>
      <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{text}</pre>
    </div>
  );
}

// A structured answer as readable key/value rows (nested values as JSON); persona text as text.
function Answer({ value }: { value: unknown }) {
  if (value == null) return <p className="text-xs text-muted-foreground">No answer stored.</p>;
  if (typeof value === "string") return <p className="text-[13px] whitespace-pre-wrap">{value}</p>;
  if (typeof value !== "object" || Array.isArray(value)) {
    return <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 font-mono text-[11px]">{JSON.stringify(value, null, 2)}</pre>;
  }
  return (
    <dl className="grid grid-cols-[140px_minmax(0,1fr)] gap-x-3 gap-y-2 text-[13px]">
      {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted-foreground">{humanize(k)}</dt>
          <dd className="min-w-0">
            {typeof v === "string" || typeof v === "number" || typeof v === "boolean" ? (
              String(v)
            ) : Array.isArray(v) && v.every((x) => typeof x === "string") ? (
              <ul className="list-disc pl-4">
                {(v as string[]).map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            ) : (
              <pre className="max-h-48 overflow-auto rounded-md bg-muted p-2 font-mono text-[11px]">{JSON.stringify(v, null, 2)}</pre>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
