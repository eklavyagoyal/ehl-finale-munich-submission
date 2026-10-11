"use client";

import type { DepartmentMemo, LlmCall, PersonaResponse, Vote } from "@/lib/api/types";
import { humanize, stanceTone } from "@/lib/format";

export interface Lane {
  id: string;
  group: string;
  region: string;
  name: string;
  vote?: string;
  voteTone?: ReturnType<typeof stanceTone>;
  calls: LlmCall[];
  persona?: PersonaResponse;
  memo?: DepartmentMemo;
  judge?: Vote;
  // From /conversation: who the persona is, and its answer to this requirement.
  detail?: string;
  answer?: string;
  note?: string;
}

// TinyTroupe stores the raw transcript after "[raw]"; the first part is the owner's answer.
export function cleanAnswer(text: string | null | undefined): string {
  return (text ?? "").split("\n[raw] ")[0].trim();
}

export function LaneDetail({ lane }: { lane: Lane }) {
  const tokens = lane.calls.reduce((sum, c) => sum + c.input_tokens + c.output_tokens, 0);
  const models = [...new Set(lane.calls.map((c) => c.model))].join(", ");
  const inputs = [...new Set(lane.calls.flatMap((c) => c.input_record_ids))];
  return (
    <div className="flex flex-col gap-2">
      <p className="font-medium">
        {lane.name}
        {lane.region && <span className="font-normal text-muted-foreground"> · {lane.region}</span>}
      </p>
      {lane.detail && <p className="text-muted-foreground">{lane.detail}</p>}
      {lane.note && <p className="text-muted-foreground">{lane.note}</p>}
      {lane.answer && !lane.persona && <p className="text-foreground/80">“{lane.answer}”</p>}
      {lane.persona && (
        <>
          <p className="text-foreground/80">“{lane.answer || cleanAnswer(lane.persona.response_text)}”</p>
          <p className="text-muted-foreground">
            {[
              lane.persona.importance_0_5 != null && `importance ${lane.persona.importance_0_5.toFixed(1)}/5`,
              lane.persona.market_fit_0_5 != null && `fit ${lane.persona.market_fit_0_5.toFixed(1)}/5`,
              "simulated",
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {lane.persona.concerns?.length ? <p className="text-muted-foreground">Concerns: {lane.persona.concerns.join(", ")}</p> : null}
        </>
      )}
      {lane.memo && (
        <>
          {lane.memo.memo.summary && <p className="text-foreground/80">{lane.memo.memo.summary}</p>}
          <p className="text-muted-foreground">
            {lane.memo.memo.effort_band && `effort ${lane.memo.memo.effort_band} · `}
            {(lane.memo.memo.criterion_ratings ?? [])
              .map((c) => `${humanize(c.criterion)} ${c.low}–${c.high}`)
              .join(" · ")}
            {" · assumed"}
          </p>
        </>
      )}
      {lane.judge && (
        <p className="text-foreground/80">
          {humanize(lane.judge.vote)} · {lane.judge.rationale}
        </p>
      )}
      {inputs.length > 0 && (
        <p className="text-muted-foreground">
          Received: <span className="font-mono">{inputs.slice(0, 4).join(", ")}</span>
          {inputs.length > 4 && ` +${inputs.length - 4}`}
        </p>
      )}
      <p className="flex items-center gap-1.5 text-muted-foreground">
        <span className="size-1.5 rounded-full bg-blue-600" aria-hidden />
        {lane.calls.length} LLM call{lane.calls.length === 1 ? "" : "s"} · {tokens.toLocaleString("en-US")} tokens{models && ` · ${models}`}
      </p>
    </div>
  );
}
