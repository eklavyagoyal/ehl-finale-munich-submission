"use client";

import Link from "next/link";

import type { LlmCall } from "@/lib/api/types";
import { fmtTime, humanize } from "@/lib/format";
import { V } from "@/lib/routes";

// Links a model call's input records: to the evidence row when the record is linked to this
// requirement, otherwise to the records view filtered by id.
export function recordHref(requirementId: string, recordId: string, linked: Set<string>): string {
  return linked.has(recordId)
    ? `${V}/decision/${encodeURIComponent(requirementId)}/evidence#rec-${recordId}`
    : `/sources?tab=records&ids=${encodeURIComponent(recordId)}`;
}

export function allRecordsHref(ids: string[]): string {
  return `/sources?tab=records&ids=${encodeURIComponent(ids.join(","))}`;
}

export function CallDetail({
  call,
  requirementId,
  linked,
  who,
  answer,
}: {
  call: LlmCall;
  requirementId: string;
  linked: Set<string>;
  who?: string;
  answer?: string;
}) {
  const ids = call.input_record_ids;
  return (
    <div className="flex flex-col gap-1.5">
      {who && <p className="font-medium">{who}</p>}
      <p>
        <span className={who ? undefined : "font-medium"}>{humanize(call.purpose)}</span>
        <span className="text-muted-foreground">
          {" "}
          · {call.model} · {call.input_tokens + call.output_tokens} tokens · {call.latency_ms} ms · {fmtTime(call.created_at)}
        </span>
      </p>
      {answer && <p className="line-clamp-4 text-foreground/80">“{answer}”</p>}
      {ids.length === 0 ? (
        <p className="text-muted-foreground">Saw no evidence records.</p>
      ) : (
        <>
          <p className="text-muted-foreground">
            Saw {ids.length} record{ids.length === 1 ? "" : "s"}:
          </p>
          <ul className="flex flex-col gap-0.5 font-mono">
            {ids.slice(0, 6).map((id) => (
              <li key={id}>
                <Link href={recordHref(requirementId, id, linked)} className="hover:underline">
                  {id}
                </Link>
              </li>
            ))}
          </ul>
          {ids.length > 6 && (
            <Link href={allRecordsHref(ids)} className="hover:underline">
              Show all {ids.length}
            </Link>
          )}
        </>
      )}
    </div>
  );
}
