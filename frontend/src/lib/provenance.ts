import {
  ClipboardList,
  FileText,
  Globe,
  type LucideIcon,
  MessageSquareText,
  MessagesSquare,
  Newspaper,
  PlayCircle,
  Smartphone,
} from "lucide-react";

import type { ClaimSummary, Source, SourceSummary } from "@/lib/api/types";
import { humanize, type Tone } from "@/lib/format";

// Where a number or quote comes from. Labels only; every value is shown as the backend sends it.

export const STREAM_ORDER = ["bmw", "social", "competitors"];

export function streamLabel(stream: string | null | undefined): string {
  if (stream === "bmw") return "BMW";
  if (stream === "social") return "Social";
  if (stream === "competitors") return "Competitor";
  return stream ? humanize(stream) : "Unknown source";
}

const CHANNEL_ICON: Record<string, LucideIcon> = {
  bmw_feedback: MessageSquareText,
  bmw_customer_study: ClipboardList,
  youtube: PlayCircle,
  app_store: Smartphone,
  google_play: Smartphone,
  editorial_review: Newspaper,
  press: Newspaper,
  forum: MessagesSquare,
  manufacturer_website: Globe,
};

const CHANNEL_LABEL: Record<string, string> = {
  bmw_feedback: "BMW feedback",
  bmw_customer_study: "BMW customer study",
  youtube: "YouTube",
  app_store: "App Store",
  google_play: "Google Play",
};

export function channelIcon(channel: string | null | undefined): LucideIcon {
  return (channel && CHANNEL_ICON[channel]) || FileText;
}

export function channelLabel(channel: string | null | undefined): string {
  if (!channel) return "Unknown channel";
  return CHANNEL_LABEL[channel] ?? humanize(channel);
}

export function isSynthetic(source: { is_example?: boolean | null; origin?: string | null } | null | undefined): boolean {
  return !!source && (source.is_example === true || source.origin === "synthetic");
}

// The backend sends a source to an external model only when it is accepted AND external_llm is true.
export function llmPermission(value: boolean | null | undefined, reviewStatus?: string | null): string {
  if (value === false) return "no";
  if (value !== true) return "unknown";
  if (reviewStatus === "accepted") return "yes";
  if (reviewStatus === "rejected") return "no, rejected";
  return "once accepted";
}

export interface Interpretation {
  label: string;
  tone: Tone;
  review: string | null;
}

// Strict mapping: BMW's own labels, a model, a person, or provided without a known method.
export function interpretation(claims: ClaimSummary[]): Interpretation {
  if (claims.length === 0) return { label: "Not interpreted", tone: "muted", review: null };
  let label = "Provided, method unknown";
  let tone: Tone = "neutral";
  if (claims.some((c) => c.derived_from_bmw_labels)) {
    label = "BMW label";
  } else if (claims.some((c) => c.producer_method === "llm")) {
    const c = claims.find((x) => x.producer_method === "llm")!;
    const run = c.producer_run_id ? `, run ${c.producer_run_id.slice(0, 8)}` : "";
    label = `AI-extracted (${c.producer_name ?? "model"}${run})`;
    tone = "blue";
  } else if (claims.some((c) => c.producer_method === "human")) {
    label = "Human";
  }
  const states = new Set(claims.map((c) => c.review_status));
  const review = states.has("rejected") ? "rejected" : states.has("pending") ? "pending" : states.has("accepted") ? "accepted" : null;
  return { label, tone, review };
}

export function producerText(c: ClaimSummary): string {
  if (c.derived_from_bmw_labels) return `BMW label · ${c.producer_name ?? "BMW classification"}`;
  const method = c.producer_method === "llm" ? "AI" : c.producer_method === "human" ? "Human" : "Provided, method unknown";
  return [method, c.producer_name, c.producer_version && `v${c.producer_version}`, c.producer_run_id && `run ${c.producer_run_id.slice(0, 8)}`]
    .filter(Boolean)
    .join(" · ");
}

export type RaterKind = "code" | "persona" | "department" | "research" | "pm";

export const RATER_KINDS: { kind: RaterKind; label: string; meaning: string }[] = [
  { kind: "code", label: "Code", meaning: "real data" },
  { kind: "persona", label: "Persona", meaning: "simulation" },
  { kind: "department", label: "Department", meaning: "assumption" },
  { kind: "research", label: "Research", meaning: "verified web source" },
  { kind: "pm", label: "PM", meaning: "human" },
];

export function raterKind(raterType: string): RaterKind {
  if (raterType === "code" || raterType === "persona" || raterType === "department" || raterType === "research" || raterType === "pm") {
    return raterType;
  }
  return raterType.startsWith("market") ? "persona" : raterType.startsWith("dept") ? "department" : "code";
}

// Finds the quote inside the full text, ignoring case and runs of whitespace, and returns the
// original character range, or null when the quote does not occur.
export function locateQuote(text: string, quote: string): [number, number] | null {
  const norm: string[] = [];
  const map: number[] = [];
  let lastSpace = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (/\s/.test(ch)) {
      if (lastSpace) continue;
      norm.push(" ");
      lastSpace = true;
    } else {
      norm.push(ch.toLowerCase());
      lastSpace = false;
    }
    map.push(i);
  }
  const needle = quote.trim().replace(/\s+/g, " ").toLowerCase();
  if (!needle) return null;
  const at = norm.join("").indexOf(needle);
  if (at < 0) return null;
  return [map[at], map[at + needle.length - 1] + 1];
}

// The source list returns full rows; the hover card wants the evidence-style summary.
export function toSummary(source: Source): SourceSummary {
  return {
    source_id: source.source_id,
    stream: source.stream,
    channel: source.channel,
    title: source.title,
    collector: source.collector ?? "",
    collected_at: source.collected_at,
    dataset_key: source.dataset_key,
    origin: source.provenance?.origin ?? null,
    verification: source.provenance?.verification ?? null,
    review_status: source.review_status,
    external_llm: source.external_llm,
    is_example: source.is_example,
    sampling_method: source.sampling?.method ?? null,
    sampling_complete: (source.sampling as { complete?: boolean } | null)?.complete ?? null,
    limitations: source.sampling?.limitations ?? [],
  };
}
