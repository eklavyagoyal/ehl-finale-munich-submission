"""Aggregate BMW G60 feedback onto the shared theme axis (counts only, no verbatim text).

Writes competitors/bmw_g60_theme_profile.csv with one row per
market x source x engine type x theme x feedback type, counting unique feedback IDs.

Usage: .venv/bin/python competitors/tools/bmw_baseline.py data/G60_feedback_hackathon.xlsx
"""

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
EUROPE = {"GB", "SE", "DK", "FI", "NO", "FR", "ES", "LV", "DE", "IT", "NL", "BE", "AT", "CH", "PL"}


def market(country: str) -> str:
    if country == "US":
        return "US"
    if country in EUROPE:
        return "EU"
    return "other"


def main(feedback_path: str) -> None:
    themes = json.loads((ROOT / "themes.json").read_text())
    l2_map = themes["vfc_level2_to_theme"]
    l3_map = themes["vfc_level3_to_theme"]

    df = pd.read_excel(feedback_path, dtype=str)
    df["Vfc level2 Name"] = df["Vfc level2 Name"].str.replace("\xa0", " ")

    def theme(row) -> str:
        if row["Vfc level3 Name"] in l3_map:
            return l3_map[row["Vfc level3 Name"]]
        return l2_map.get(row["Vfc level2 Name"], "unclassified")

    df["theme"] = df.apply(theme, axis=1)
    df["market"] = df["Country"].map(market)
    df["engine"] = df["Engine Type"].replace({"BEVE": "BEV"})
    df["feedback_type"] = df["Feedback Type"].fillna("none")

    profile = (
        df.drop_duplicates(["ID", "theme", "feedback_type"])
        .groupby(["market", "Source", "engine", "theme", "feedback_type"])["ID"]
        .nunique()
        .rename("feedbacks")
        .reset_index()
        .rename(columns={"Source": "source"})
    )
    out = ROOT / "bmw_g60_theme_profile.csv"
    profile.to_csv(out, index=False)

    pivot = profile.pivot_table(index="theme", columns="market", values="feedbacks", aggfunc="sum", fill_value=0)
    print(pivot.sort_values("US", ascending=False).to_string())
    print(f"wrote {out} ({len(profile)} rows)")


if __name__ == "__main__":
    main(sys.argv[1])
