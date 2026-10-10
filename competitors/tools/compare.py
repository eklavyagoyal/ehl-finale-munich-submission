"""Per market x theme scorecard: BMW 5 Series vs its competitors.

Inputs: findings.jsonl (merge.py), bmw_g60_theme_profile.csv (bmw_baseline.py), nhtsa_us_theme_profile.csv (nhtsa.py)
Output: scorecard.csv with, per market and theme,
  - owner voice: share of critical statements (Wants + Difficult to Use + Defect) for BMW vs pooled competitors
      BMW baseline = G60 Source A owner reviews (EU/US) or G68 web owner reviews (CN)
  - head-to-head verdicts: explicit comparisons (web records + BMW verbatims naming a rival)
  - NHTSA (US only): share of complaints on the theme, BMW vs competitor median

Usage: .venv/bin/python competitors/tools/compare.py
"""

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRITICAL = {"Wants", "Difficult to Use", "Defect"}  # everything that is not a Like
TYPES = {"Likes", "Wants", "Difficult to Use", "Defect"}


def main() -> None:
    themes = [t["id"] for t in json.loads((ROOT / "themes.json").read_text())["themes"]]
    recs = [json.loads(line) for line in (ROOT / "findings.jsonl").read_text().splitlines() if line.strip()]

    owner = defaultdict(Counter)  # (market, side, theme) -> {neg, total}
    reviews = defaultdict(set)
    verdict = defaultdict(Counter)  # (market, theme) -> comparison counts
    for r in recs:
        if r["kind"] == "feedback":
            is_bmw = r["brand"] == "BMW"
            if r["source_type"] in ("owner_review", "owner_forum") and "nhtsa" not in r["source_name"].lower():
                side = "bmw" if is_bmw else "competitors"
                owner[(r["market"], side, r["theme"])]["total"] += 1
                owner[(r["market"], side, r["theme"])]["neg"] += r["feedback_type"] in CRITICAL
                reviews[(r["market"], side, r["theme"])].add(r["review_ref"])
            if r.get("comparison") and not is_bmw:
                verdict[(r["market"], r["theme"])][r["comparison"]] += 1
        elif r["kind"] == "bmw_mention" and r["relation"] in ("competitor_advantage", "bmw_advantage", "parity"):
            mkt = "US" if r.get("country") == "US" else ("EU" if r.get("country") in {"GB", "SE", "DK", "FI", "NO", "FR", "ES", "LV"} else None)
            if mkt:
                verdict[(mkt, r["theme"])][r["relation"]] += 1

    # BMW G60 Source A owner reviews (EU/US) from the BMW data
    with (ROOT / "bmw_g60_theme_profile.csv").open() as f:
        for row in csv.DictReader(f):
            if row["source"] == "Source A" and row["market"] in ("EU", "US") and row["feedback_type"] in TYPES:
                key = (row["market"], "bmw", row["theme"])
                owner[key]["total"] += int(row["feedbacks"])
                owner[key]["neg"] += int(row["feedbacks"]) if row["feedback_type"] in CRITICAL else 0

    nhtsa = defaultdict(dict)
    path = ROOT / "nhtsa_us_theme_profile.csv"
    if path.exists():
        with path.open() as f:
            for row in csv.DictReader(f):
                nhtsa[row["theme"]][row["vehicle"]] = float(row["share_of_vehicle_complaints"])
    nhtsa_vehicles = {v for d in nhtsa.values() for v in d}

    # Channel bias: BMW Source A and competitor review sites differ in overall negativity. The *_vs_avg columns
    # subtract each side's average critical share in that market, so themes can be compared on relative pain.
    avg = {}
    for (market, side, _), cnt in owner.items():
        a = avg.setdefault((market, side), Counter())
        a["neg"] += cnt["neg"]
        a["total"] += cnt["total"]

    def rel(market: str, side: str, cnt: Counter):
        a = avg.get((market, side))
        if not cnt["total"] or not a or not a["total"]:
            return ""
        return round(cnt["neg"] / cnt["total"] - a["neg"] / a["total"], 2)

    out = []
    for market in ("EU", "US", "CN"):
        for theme in themes:
            b, c = owner[(market, "bmw", theme)], owner[(market, "competitors", theme)]
            v = verdict[(market, theme)]
            row = {
                "market": market, "theme": theme,
                "bmw_owner_statements": b["total"],
                "bmw_owner_share_critical": round(b["neg"] / b["total"], 2) if b["total"] else "",
                "competitor_owner_statements": c["total"],
                "competitor_owner_reviews": len(reviews[(market, "competitors", theme)]),
                "competitor_owner_share_critical": round(c["neg"] / c["total"], 2) if c["total"] else "",
                "bmw_critical_vs_avg": rel(market, "bmw", b),
                "competitor_critical_vs_avg": rel(market, "competitors", c),
                "verdict_competitor_better": v["competitor_advantage"],
                "verdict_bmw_better": v["bmw_advantage"],
                "verdict_parity": v["parity"],
            }
            if market == "US" and nhtsa_vehicles:
                bmw_key = next((k for k in nhtsa_vehicles if k.startswith("BMW")), None)
                rivals = [nhtsa[theme].get(k, 0.0) for k in nhtsa_vehicles if k != bmw_key]
                row["nhtsa_bmw_share"] = nhtsa[theme].get(bmw_key, 0.0) if bmw_key else ""
                row["nhtsa_competitor_median_share"] = round(statistics.median(rivals), 3) if rivals else ""
            out.append(row)

    fields = list(out[0]) + ["nhtsa_bmw_share", "nhtsa_competitor_median_share"]
    fields = list(dict.fromkeys(fields))
    with (ROOT / "scorecard.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {ROOT / 'scorecard.csv'} ({len(out)} rows)")


if __name__ == "__main__":
    main()
