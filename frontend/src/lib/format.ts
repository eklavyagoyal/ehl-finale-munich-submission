// Display helpers shared by all screens. Enum values come from /api/meta; this file only turns
// machine values into readable labels and picks a tone.

export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export type Tone = "neutral" | "amber" | "green" | "red" | "blue" | "muted";

const STATUS_TONE: Record<string, Tone> = {
  draft: "muted",
  proposed: "neutral",
  in_review: "amber",
  investigate: "amber",
  approved: "green",
  rejected: "red",
  challenged: "blue",
  deferred: "muted",
};

export function statusTone(status: string | null | undefined): Tone {
  return (status && STATUS_TONE[status]) || "neutral";
}

const STANCE_TONE: Record<string, Tone> = {
  positive: "green",
  support: "green",
  approve: "green",
  negative: "red",
  oppose: "red",
  reject: "red",
  neutral: "muted",
  mixed: "muted",
  investigate: "amber",
  defer: "muted",
};

export function stanceTone(stance: string | null | undefined): Tone {
  return (stance && STANCE_TONE[stance]) || "muted";
}

export function gateTone(value: string | null | undefined): Tone {
  return value === "pass" ? "green" : value === "fail" ? "red" : "amber";
}

// Observed and estimated numbers are evidence; simulated and assumed ones are hypotheses.
export function isHypothesis(status: string | null | undefined): boolean {
  if (!status) return true;
  return status.split("+").some((part) => part === "simulated" || part === "assumed" || part === "unknown");
}

export function fmtScore(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? "–" : value.toFixed(digits);
}

export function fmtRange(low: number | null | undefined, high: number | null | undefined, digits = 0): string {
  if (low === null || low === undefined || high === null || high === undefined) return "–";
  const a = low.toFixed(digits);
  const b = high.toFixed(digits);
  return a === b ? a : `${a}–${b}`;
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  return `${date.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} · ${fmtTime(iso)}`;
}

const REGION = /^(us|eu|cn)-/;

// persona:us-bev-early-adopter -> { group: "US", name: "Bev early adopter" }
export function agentLabel(agentId: string): { group: string; name: string } {
  const [kind, rest = ""] = agentId.split(":");
  if (kind === "persona") {
    const region = rest.match(REGION)?.[1];
    return { group: region ? region.toUpperCase() : "", name: humanize(rest.replace(REGION, "")) };
  }
  if (kind === "dept") {
    const parts = rest.split("-");
    const region = ["us", "eu", "cn"].includes(parts[parts.length - 1]) ? parts.pop()!.toUpperCase() : "";
    return { group: region, name: humanize(parts.join(" ")) };
  }
  if (kind === "judge") return { group: "", name: `Judge ${rest}` };
  if (kind === "agent") return { group: "", name: humanize(rest) };
  if (kind === "pm") return { group: "PM", name: humanize(rest) };
  return { group: "", name: humanize(rest || kind) };
}

export function actorLabel(actorId: string): string {
  const { group, name } = agentLabel(actorId);
  return group ? `${name} · ${group}` : name;
}

export const STAGES = ["market_and_company_twin", "research", "scoring", "synthesis_and_vote"] as const;

export const STAGE_LABEL: Record<string, string> = {
  market_and_company_twin: "Market and company twin",
  research: "Research",
  scoring: "Scoring",
  synthesis_and_vote: "Synthesis and vote",
  done: "Done",
};
