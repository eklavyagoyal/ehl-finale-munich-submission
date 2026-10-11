"""Validate and merge the research agents' raw/*.jsonl files.

Writes:
  findings.jsonl          all valid records (plus `agent`)
  validation.md           rejected records and warnings
  theme_comparison.csv    feedback mix per market x vehicle x theme, BMW G60 baseline included
  equipment_matrix.csv    feature x vehicle per market

Usage: .venv/bin/python competitors/tools/merge.py
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = json.loads((ROOT / "themes.json").read_text())
THEME_IDS = {t["id"] for t in THEMES["themes"]}
VFC_L2 = set(THEMES["vfc_level2_to_theme"])
FEEDBACK_TYPES = set(THEMES["feedback_types"])
COMPARISON = set(THEMES["comparison_values"])
MARKETS = {"EU", "US", "CN"}
FEATURES = {
    "F01_display_layout", "F02_hud", "F03_physical_climate_controls", "F04_voice_assistant",
    "F05_wireless_carplay_aa", "F06_ota_updates", "F07_digital_key", "F08_hands_free_highway",
    "F09_automated_parking", "F10_ventilated_front_seats", "F11_massage_seats", "F12_rear_comfort",
    "F13_air_suspension", "F14_rear_wheel_steering", "F15_bev_range", "F16_dc_charging",
    "F17_rear_space", "F18_trunk_volume", "F19_premium_audio", "F20_panoramic_roof",
}
RELATIONS = {"competitor_advantage", "bmw_advantage", "parity", "previous_car", "cross_shopped", "mention_only"}
LOCAL_SOURCES = {"docs/datasets/option-lists/G60-5-series.md"}


def check(rec: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one record."""
    err, warn = [], []
    kind = rec.get("kind")

    def need(*fields):
        for f in fields:
            if rec.get(f) in (None, ""):
                err.append(f"missing {f}")

    def url_ok():
        url = rec.get("url") or ""
        if not (url.startswith("http") or url in LOCAL_SOURCES):
            err.append(f"bad url {url!r}")

    if kind == "feedback":
        need("record_id", "review_ref", "market", "brand", "model", "generation", "source_type", "url",
             "feedback_type", "theme", "statement", "evidence_tier")
        url_ok()
        if rec.get("market") not in MARKETS:
            err.append(f"market {rec.get('market')!r}")
        if rec.get("feedback_type") not in FEEDBACK_TYPES:
            err.append(f"feedback_type {rec.get('feedback_type')!r}")
        if rec.get("theme") not in THEME_IDS:
            err.append(f"theme {rec.get('theme')!r}")
        if rec.get("comparison") not in COMPARISON | {None}:
            err.append(f"comparison {rec.get('comparison')!r}")
        if rec.get("vfc_level2") not in VFC_L2 | {None}:
            warn.append(f"unknown vfc_level2 {rec.get('vfc_level2')!r} (dropped)")
            rec["vfc_level2"] = None
        if rec.get("evidence_tier") not in {"A", "B"}:
            err.append(f"evidence_tier {rec.get('evidence_tier')!r}")
        quote = rec.get("quote") or ""
        if len(quote.split()) >= 15 or len(quote) > 60:
            warn.append("quote too long (dropped)")
            rec["quote"] = None
    elif kind == "equipment":
        need("record_id", "market", "brand", "model", "feature", "availability", "url")
        url_ok()
        if rec.get("feature") not in FEATURES:
            err.append(f"feature {rec.get('feature')!r}")
        if rec.get("availability") not in {"standard", "optional", "not_available", "unknown"}:
            err.append(f"availability {rec.get('availability')!r}")
        if rec.get("market") not in MARKETS:
            err.append(f"market {rec.get('market')!r}")
    elif kind == "competitor":
        need("record_id", "market", "brand", "model", "rationale")
    elif kind == "outlook":
        need("record_id", "brand", "model", "announcement", "url", "confidence")
        url_ok()
        if rec.get("confidence") not in {"announced", "reported", "rumoured"}:
            err.append(f"confidence {rec.get('confidence')!r}")
    elif kind == "bmw_mention":
        need("record_id", "bmw_feedback_id", "competitor_brand", "relation", "theme")
        if rec.get("relation") not in RELATIONS:
            err.append(f"relation {rec.get('relation')!r}")
        if rec.get("theme") not in THEME_IDS:
            err.append(f"theme {rec.get('theme')!r}")
    else:
        err.append(f"unknown kind {kind!r}")
    return err, warn


def channel(rec: dict) -> str:
    """Comparable customer channel: owner reviews/forums, complaint databases, surveys, press."""
    if rec["source_type"] == "press_review":
        return "press"
    if "nhtsa" in (rec.get("source_name") or "").lower():
        return "complaints"
    if rec["source_type"] == "owner_survey":
        return "survey"
    return "owner"


def vehicle(rec: dict) -> str:
    gen = rec.get("generation") or ""
    return f"{rec['brand']} {rec['model']}" + (f" ({gen})" if gen else "")


def bmw_rows() -> list[dict]:
    """BMW G60 baseline from bmw_g60_theme_profile.csv: all sources, and Source A only."""
    path = ROOT / "bmw_g60_theme_profile.csv"
    if not path.exists():
        return []
    agg = defaultdict(Counter)
    with path.open() as f:
        for r in csv.DictReader(f):
            if r["market"] not in MARKETS or r["feedback_type"] not in FEEDBACK_TYPES:
                continue
            n = int(r["feedbacks"])
            agg[(r["market"], "bmw_all_sources", r["theme"])][r["feedback_type"]] += n
            if r["source"] == "Source A":
                agg[(r["market"], "owner", r["theme"])][r["feedback_type"]] += n
    return [
        {"market": m, "vehicle": "BMW 5 Series (G60)", "channel": ch, "theme": t, "basis": "BMW feedback IDs",
         "n_reviews": "", "counts": c}
        for (m, ch, t), c in agg.items()
    ]


def main() -> None:
    valid, rejected, warnings = [], [], []
    seen = set()
    for path in sorted((ROOT / "raw").glob("*.jsonl")):
        agent = path.stem
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                rejected.append((agent, i, f"invalid JSON: {e}"))
                continue
            err, warn = check(rec)
            rid = rec.get("record_id")
            if rid in seen:
                err.append(f"duplicate record_id {rid}")
            seen.add(rid)
            warnings += [(agent, i, w) for w in warn]
            if err:
                rejected.append((agent, i, "; ".join(err)))
                continue
            rec["agent"] = agent
            valid.append(rec)

    with (ROOT / "findings.jsonl").open("w") as f:
        for rec in valid:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Feedback mix per market x vehicle x theme
    groups = defaultdict(lambda: {"counts": Counter(), "reviews": set(), "tiers": Counter()})
    for rec in valid:
        if rec["kind"] != "feedback":
            continue
        g = groups[(rec["market"], vehicle(rec), channel(rec), rec["theme"])]
        g["counts"][rec["feedback_type"]] += 1
        g["reviews"].add(rec["review_ref"])
        g["tiers"][rec["evidence_tier"]] += 1
    rows = [
        {"market": m, "vehicle": v, "channel": ch, "theme": t, "basis": "web records",
         "n_reviews": len(g["reviews"]), "counts": g["counts"]}
        for (m, v, ch, t), g in groups.items()
    ] + bmw_rows()
    types = ["Likes", "Wants", "Difficult to Use", "Defect"]
    with (ROOT / "theme_comparison.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["market", "channel", "theme", "vehicle", "basis", "n_reviews", "n_statements"]
                   + [f"share_{t.lower().replace(' ', '_')}" for t in types] + ["share_negative"])
        for r in sorted(rows, key=lambda r: (r["market"], r["channel"], r["theme"], r["vehicle"])):
            n = sum(r["counts"][t] for t in types)
            if not n:
                continue
            shares = [round(r["counts"][t] / n, 2) for t in types]
            neg = round((r["counts"]["Difficult to Use"] + r["counts"]["Defect"]) / n, 2)
            w.writerow([r["market"], r["channel"], r["theme"], r["vehicle"], r["basis"], r["n_reviews"], n]
                       + shares + [neg])

    # Equipment matrix
    eq = defaultdict(dict)
    for rec in valid:
        if rec["kind"] == "equipment":
            cell = rec["availability"] + (f": {rec['value']}" if rec.get("value") else "")
            key = (rec["market"], rec["feature"])
            veh = vehicle(rec)
            eq[key][veh] = (eq[key][veh] + " | " + cell) if veh in eq[key] else cell
    vehicles = sorted({v for cells in eq.values() for v in cells})
    with (ROOT / "equipment_matrix.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["market", "feature"] + vehicles)
        for (m, feat) in sorted(eq):
            w.writerow([m, feat] + [eq[(m, feat)].get(v, "") for v in vehicles])

    # Report
    kinds = Counter((r["agent"], r["kind"]) for r in valid)
    lines = ["# Validation report", "", f"Valid records: {len(valid)} · rejected: {len(rejected)} · warnings: {len(warnings)}", "",
             "| agent | kind | records |", "| --- | --- | ---: |"]
    lines += [f"| {a} | {k} | {n} |" for (a, k), n in sorted(kinds.items())]
    if rejected:
        lines += ["", "## Rejected", ""] + [f"- `{a}` line {i}: {e}" for a, i, e in rejected]
    if warnings:
        lines += ["", "## Warnings", ""] + [f"- `{a}` line {i}: {w}" for a, i, w in warnings]
    (ROOT / "validation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:4 + len(kinds) + 2]))


if __name__ == "__main__":
    main()
