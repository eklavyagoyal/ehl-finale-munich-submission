"""Pull NHTSA owner complaints for the BMW 5 Series (G60) and its US competitors, map them to themes.

NHTSA complaints are the one customer channel measured the same way for every vehicle in the US,
so they give a like-for-like comparison of *what goes wrong* (almost all are defects).

Writes:
  nhtsa_us_complaints.csv      one row per complaint x theme (no complaint text, ODI number for lookup)
  nhtsa_us_theme_profile.csv   complaints per vehicle x theme, with share of the vehicle's complaints

Usage: .venv/bin/python competitors/tools/nhtsa.py
"""

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.nhtsa.gov"

# vehicle key -> (label, make, model years, include regex on NHTSA model name, exclude regex)
VEHICLES = {
    "bmw_5_g60": ("BMW 5 Series (G60)", "BMW", range(2024, 2028), r"^(5\d0I|I5|5 SERIES)", r"GRAN TURISMO|^M5"),
    "mb_e_w214": ("Mercedes-Benz E-Class (W214)", "MERCEDES-BENZ", range(2024, 2028), r"^E[- ]?(CLASS|\d{3})", r"COUPE|CABRIOLET"),
    "mb_eqe_v295": ("Mercedes-Benz EQE sedan (V295)", "MERCEDES-BENZ", range(2023, 2028), r"^EQE", r"SUV"),
    "audi_a6_etron": ("Audi A6 e-tron (PPE)", "AUDI", range(2025, 2028), r"^(A6|S6).*E-TRON", r"$^"),
    "audi_a6_c9": ("Audi A6 (C9)", "AUDI", range(2026, 2028), r"^(A6|S6)\b", r"E-TRON|ALLROAD|AVANT|RS"),
    "tesla_model_3": ("Tesla Model 3 (Highland)", "TESLA", range(2024, 2028), r"^MODEL 3", r"$^"),
    "tesla_model_s": ("Tesla Model S (2021 refresh)", "TESLA", range(2021, 2028), r"^MODEL S", r"$^"),
    "genesis_g80": ("Genesis G80 (RG3)", "GENESIS", range(2021, 2028), r"G80", r"$^"),
    "lexus_es_7": ("Lexus ES (XZ10)", "LEXUS", range(2019, 2026), r"^ES", r"$^"),
    "cadillac_ct5": ("Cadillac CT5", "CADILLAC", range(2020, 2028), r"^CT5", r"$^"),
}

COMPONENT_THEME = [
    ("AIR BAG", "safety"), ("SEAT BELT", "safety"), ("CHILD SEAT", "safety"), ("SEATS", "seats_comfort"),
    ("STEERING", "ride_handling"), ("SERVICE BRAKES", "ride_handling"), ("PARKING BRAKE", "ride_handling"),
    ("SUSPENSION", "ride_handling"), ("TIRES", "ride_handling"), ("WHEELS", "ride_handling"),
    ("ELECTRONIC STABILITY", "ride_handling"), ("TRACTION CONTROL", "ride_handling"),
    ("ENGINE", "powertrain_performance"), ("POWER TRAIN", "powertrain_performance"),
    ("FUEL/PROPULSION", "powertrain_performance"), ("HYBRID PROPULSION", "powertrain_performance"),
    ("FORWARD COLLISION", "adas_parking"), ("LANE DEPARTURE", "adas_parking"), ("BACK OVER", "adas_parking"),
    ("VISIBILITY", "lighting_visibility"), ("EXTERIOR LIGHTING", "lighting_visibility"),
    ("LATCHES/LOCKS", "access_locking"), ("STRUCTURE", "overall_quality_ownership"),
    ("EQUIPMENT", "overall_quality_ownership"),
]
# For ELECTRICAL SYSTEM / UNKNOWN OR OTHER / VEHICLE SPEED CONTROL the text decides (first match wins).
TEXT_THEME = [
    ("range_charging_efficiency", r"charg|high[- ]voltage|\bhv\b|traction battery|battery pack|range"),
    ("adas_parking", r"cruise|lane|collision|emergency brak|phantom|automatic brak|parking assist|park assist|camera|radar|sensor"),
    ("hmi_infotainment", r"screen|display|infotainment|idrive|mbux|touch ?screen|monitor|instrument cluster|navigation|head[- ]up"),
    ("connectivity_app_digital", r"carplay|android auto|bluetooth|\bapp\b|software update|over the air|\bota\b|wi-?fi|phone"),
    ("access_locking", r"door|lock|key|trunk|liftgate|tailgate|handle"),
    ("climate", r"a/c|air condition|heater|hvac|climate|defrost"),
    ("powertrain_performance", r"los[st]e? (of )?(motive )?power|power loss|shut (off|down)|accelerat|propulsion|transmission|stall|shift"),
    ("interior_design_quality", r"sunroof|panoram|glass roof|moonroof"),
    ("overall_quality_ownership", r"12 ?v|12-volt|battery|electrical"),
]
RECALL = re.compile(r"campaign number|\brecall", re.I)
TEXT_DECIDED = ("ELECTRICAL SYSTEM", "UNKNOWN OR OTHER", "VEHICLE SPEED CONTROL")


def get(path: str, **params) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # NHTSA returns 400 for unknown model/year combinations
            if attempt == 2:
                print(f"  ! {url}: {e}")
                return {"results": []}
            time.sleep(1.5)
    return {"results": []}


def themes_for(components: str, summary: str) -> list[str]:
    text = summary.lower()
    out = []
    for comp in [c.strip() for c in components.split(",") if c.strip()]:
        if comp.startswith(TEXT_DECIDED):
            theme = next((t for t, rx in TEXT_THEME if re.search(rx, text)), "overall_quality_ownership")
        else:
            theme = next((t for key, t in COMPONENT_THEME if comp.startswith(key)), "overall_quality_ownership")
        if theme not in out:
            out.append(theme)
    return out or ["unclassified"]


def main() -> None:
    model_cache = {}
    rows = []
    for key, (label, make, years, inc, exc) in VEHICLES.items():
        seen = set()
        for year in years:
            if (make, year) not in model_cache:
                res = get("/products/vehicle/models", modelYear=year, make=make, issueType="c")["results"]
                model_cache[(make, year)] = sorted({r["model"] for r in res})
            models = [m for m in model_cache[(make, year)] if re.search(inc, m) and not re.search(exc, m)]
            for model in models:
                for c in get("/complaints/complaintsByVehicle", make=make, model=model, modelYear=year)["results"]:
                    odi = c["odiNumber"]
                    if odi in seen:
                        continue
                    summary = c.get("summary") or ""
                    if key == "mb_eqe_v295" and re.search(r"\bsuv\b", summary.lower()):
                        continue  # NHTSA mixes EQE sedan and EQE SUV in some buckets
                    seen.add(odi)
                    for theme in themes_for(c.get("components") or "", summary):
                        rows.append({
                            "vehicle_key": key, "vehicle": label, "make": make, "nhtsa_model": model, "model_year": year,
                            "odi_number": odi, "date_filed": c.get("dateComplaintFiled"), "components": c.get("components"),
                            "theme": theme, "recall_related": bool(RECALL.search(summary)),
                            "crash": c.get("crash"), "fire": c.get("fire"), "injuries": c.get("numberOfInjuries"),
                        })
                time.sleep(0.2)
            print(f"{label} MY{year}: models {models}")
        print(f"  -> {len(seen)} complaints")

    with (ROOT / "nhtsa_us_complaints.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    complaints = defaultdict(set)
    recall = defaultdict(set)
    per_theme = defaultdict(Counter)
    for r in rows:
        complaints[r["vehicle"]].add(r["odi_number"])
        per_theme[r["vehicle"]][r["theme"]] += 1
        if r["recall_related"]:
            recall[r["vehicle"]].add(r["odi_number"])
    with (ROOT / "nhtsa_us_theme_profile.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vehicle", "complaints_total", "recall_related_total", "theme", "complaints",
                    "share_of_vehicle_complaints"])
        for veh, counter in per_theme.items():
            total = len(complaints[veh])
            for theme, n in counter.most_common():
                w.writerow([veh, total, len(recall[veh]), theme, n, round(n / total, 3)])
    print({v: (len(s), len(recall[v])) for v, s in complaints.items()})


if __name__ == "__main__":
    main()
