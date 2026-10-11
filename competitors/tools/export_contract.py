"""Export our competitor research into the team's research data contract v1.

The contract lives on branch feat/research-handoff (research/schema.json, docs/research-data-contract.md).
Our own format (competitors/findings.jsonl) stays the master. This script writes a contract-shaped copy:

  research/batches/competitors/luis-20261010-<market>-<source>-<kind>/
    source.json, records.jsonl, claims.jsonl   strictly per contract schema
    notes.md                                   scope, counts, limitations
    luis_extensions.json                       everything the contract has no field for (theme, tiers, ...)
  competitors/contract/
    catalog_additions.json   competitor entities + feature keys to append to research/catalog/*
    comparisons.json         BMW target <-> competitor matches with rationale and supporting record IDs
    outlook.json             announcements 2026-2030 (not availability evidence, so not records)
    bmw_mentions.json        BMW G60 verbatims naming a rival (labels only), joinable to BMW feedback records

Mapping:
  feedback statements  -> one record per review (review_ref) + one claim per statement
  equipment            -> feature_availability records
  NHTSA complaints     -> records with the verbatim public-domain narrative (from data/nhtsa/, see nhtsa.py)

Usage: .venv/bin/python competitors/tools/export_contract.py [--only <substring>]
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nhtsa  # noqa: E402  (theme rules and vehicle list)

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
BATCHES = REPO / "research" / "batches" / "competitors"
SIDECARS = ROOT / "contract"
COLLECTOR = "luis"
DATE = "2026-10-10"
COLLECTED_AT = "2026-10-10T16:00:00Z"  # web research ran 14:50-16:00 UTC; records carry no per-page fetch time
RUN_ID = "luis-competitors-2026-10-10"
MODEL = "claude-opus-5-5"
PREFIX = f"{COLLECTOR}-{DATE.replace('-', '')}"  # same style as other collectors: yelya-20261010-...

FEATURES = {
    "F01_display_layout": ("central_display_layout", "Central display(s): size, layout, passenger screen"),
    "F02_hud": ("head_up_display", "Head-up display"),
    "F03_physical_climate_controls": ("physical_climate_controls", "Physical buttons/knobs for climate control"),
    "F04_voice_assistant": ("natural_language_voice_assistant", "Natural-language / LLM voice assistant"),
    "F05_wireless_carplay_aa": ("wireless_smartphone_projection", "Wireless Apple CarPlay / Android Auto (or CN equivalents)"),
    "F06_ota_updates": ("ota_software_updates", "Over-the-air software updates"),
    "F07_digital_key": ("phone_digital_key", "Phone-as-key / digital key"),
    "F08_hands_free_highway": ("hands_free_highway_assist", "Hands-free / navigate-on-autopilot highway assist"),
    "F09_automated_parking": ("automated_remote_parking", "Automated / remote parking"),
    "F10_ventilated_front_seats": ("ventilated_front_seats", "Ventilated front seats"),
    "F11_massage_seats": ("massage_seats", "Massage seats"),
    "F12_rear_comfort": ("rear_seat_comfort_features", "Rear seat comfort (heated/ventilated/recline/rear screens/controls)"),
    "F13_air_suspension": ("air_suspension", "Air suspension"),
    "F14_rear_wheel_steering": ("rear_wheel_steering", "Rear-wheel steering"),
    "F15_bev_range": ("bev_range", "BEV range, best variant"),
    "F16_dc_charging": ("dc_fast_charging", "BEV DC fast charging: peak kW, 10-80 % time, voltage"),
    "F17_rear_space": ("rear_space_wheelbase", "Wheelbase / rear legroom"),
    "F18_trunk_volume": ("trunk_volume", "Trunk volume, frunk"),
    "F19_premium_audio": ("premium_audio_system", "Premium audio system"),
    "F20_panoramic_roof": ("panoramic_glass_roof", "Panoramic / glass roof"),
}
# BMW VFC level2 topics that name the same feature as an equipment key
VFC_ALIASES = {
    "Head-Up Display": "head_up_display", "Panorama glass roof": "panoramic_glass_roof", "Seat massage": "massage_seats",
    "Digital Key": "phone_digital_key", "Remote Software Upgrade/RSU": "ota_software_updates",
    "Electric Range": "bev_range", "Remote controlled parking": "automated_remote_parking",
}
AVAILABILITY = {"standard": "present", "optional": "optional", "not_available": "absent", "unknown": "unknown"}
CLAIM_TYPE = {"Likes": "praise", "Defect": "defect", "Wants": "new_request", "Difficult to Use": "other"}
CHANNEL = {"owner_review": "other", "owner_forum": "forum", "owner_survey": "other", "press_review": "editorial_review"}
KIND_LABEL = {"owner_review": "owner-reviews", "owner_forum": "forum", "owner_survey": "survey", "press_review": "press"}

ENTITY_RULES = [  # (brand regex, model regex, generation regex, entity_id, label)
    (r"^BMW", r"", r"G68", "bmw:G68", None),
    (r"^BMW", r"", r"G60", "bmw:G60", None),
    (r"^Audi", r"^A6L e-tron", r"", "competitor:audi:a6l-e-tron:ppe", "Audi A6L e-tron (PPE, China)"),
    (r"^Audi", r"^A6L", r"C9", "competitor:audi:a6l:c9l", "Audi A6L, new generation (China, 'C9 L')"),
    (r"^Audi", r"^A6L", r"C8", "competitor:audi:a6l:c8l", "Audi A6L (C8 L, China)"),
    (r"^Audi", r"e-tron", r"", "competitor:audi:a6-e-tron:ppe", "Audi A6 e-tron / A6 Sportback e-tron (PPE)"),
    (r"^Audi", r"^A6$", r"C9", "competitor:audi:a6:c9", "Audi A6 (C9)"),
    (r"^Cadillac", r"CT5", r"", "competitor:cadillac:ct5:gen1", "Cadillac CT5 (1st gen, MY2020+)"),
    (r"^Genesis", r"G80", r"", "competitor:genesis:g80:rg3", "Genesis G80 incl. Electrified G80 (RG3)"),
    (r"^Lexus", r"ES", r"8th", "competitor:lexus:es:gen8", "Lexus ES (8th gen, MY2026+)"),
    (r"^Lexus", r"ES", r"XZ10", "competitor:lexus:es:xz10", "Lexus ES (7th gen, XZ10)"),
    (r"^Luxeed", r"S7", r"", "competitor:luxeed:s7:gen1", "Luxeed S7 (HIMA, 1st gen)"),
    (r"^Mercedes", r"^E-Class L", r"", "competitor:mercedes-benz:e-class-l:v214", "Mercedes-Benz E-Class L (V214, China)"),
    (r"^Mercedes", r"^E-Class", r"", "competitor:mercedes-benz:e-class:w214", "Mercedes-Benz E-Class (W214)"),
    (r"^Mercedes", r"^EQE", r"", "competitor:mercedes-benz:eqe-sedan:v295", "Mercedes-Benz EQE sedan (V295)"),
    (r"^NIO", r"ET7", r"", "competitor:nio:et7:gen1", "NIO ET7 (1st gen, 2024 facelift)"),
    (r"^Stelato", r"S9", r"", "competitor:stelato:s9:gen1", "Stelato S9 (HIMA, 1st gen)"),
    (r"^Tesla", r"Model 3", r"", "competitor:tesla:model-3:highland", "Tesla Model 3 (Highland)"),
    (r"^Tesla", r"Model S", r"", "competitor:tesla:model-s:2021-refresh", "Tesla Model S (2021 refresh)"),
    (r"^Volvo", r"ES90", r"", "competitor:volvo:es90:gen1", "Volvo ES90 (1st gen)"),
    (r"^Xiaomi", r"SU7", r"", "competitor:xiaomi:su7:gen1", "Xiaomi SU7 (1st gen)"),
    (r"^Zeekr", r"007", r"", "competitor:zeekr:007:gen1", "Zeekr 007 (1st gen)"),
]
NHTSA_ENTITY = {
    "bmw_5_g60": "bmw:G60", "mb_e_w214": "competitor:mercedes-benz:e-class:w214",
    "mb_eqe_v295": "competitor:mercedes-benz:eqe-sedan:v295", "audi_a6_etron": "competitor:audi:a6-e-tron:ppe",
    "audi_a6_c9": "competitor:audi:a6:c9", "tesla_model_3": "competitor:tesla:model-3:highland",
    "tesla_model_s": "competitor:tesla:model-s:2021-refresh", "genesis_g80": "competitor:genesis:g80:rg3",
    "lexus_es_7": "competitor:lexus:es:xz10", "cadillac_ct5": "competitor:cadillac:ct5:gen1",
}
LOCAL_OPTION_LIST = "docs/datasets/option-lists/G60-5-series.md"

PARAPHRASE_LIMITATIONS = [
    "text_original holds the collecting agent's English paraphrase, not verbatim source text. The agent read pages "
    "through WebFetch, which returns model-written summaries; original wording was not stored (copyright, tool limits).",
    "Claims quote that paraphrase; any 'Original excerpt' in text_original came out of the same summaries and is not "
    "guaranteed verbatim.",
    "Targeted, non-random selection: pages chosen via web search and known review URLs, capped by a fetch budget.",
    "collected_at is approximate: the end of the research run (2026-10-10 ~16:00 UTC); per-page fetch times were not "
    "recorded.",
    "markets: the reviewer's country where known, else the site's country domain for EU sources, else the market "
    "aggregate (EU/US/CN).",
]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def entity_for(rec: dict) -> tuple[str, str | None]:
    for b, m, g, eid, label in ENTITY_RULES:
        if re.search(b, rec["brand"]) and re.search(m, rec["model"]) and re.search(g, rec.get("generation") or ""):
            return eid, label
    raise ValueError(f"no entity for {rec['brand']} {rec['model']} {rec.get('generation')}")


def clean_url(url: str) -> str:
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def domain(url: str) -> str:
    if url == LOCAL_OPTION_LIST:
        return "bmw-option-list"
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


TLD_COUNTRY = {"de": "DE", "uk": "GB", "pl": "PL", "fr": "FR", "se": "SE", "nl": "NL", "it": "IT", "es": "ES",
               "at": "AT", "ch": "CH", "dk": "DK", "no": "NO", "fi": "FI", "be": "BE"}


def markets_for(rec: dict) -> list[str]:
    """Most specific market the record supports: its country, else the site's country TLD (EU only), else the market."""
    country = (rec.get("country") or "").upper()
    if re.fullmatch(r"[A-Z]{2}", country):
        return [country]
    if rec["market"] == "EU" and rec["url"].startswith("http"):
        tld = urllib.parse.urlparse(rec["url"]).netloc.lower().rsplit(".", 1)[-1]
        if tld in TLD_COUNTRY:
            return [TLD_COUNTRY[tld]]
    return [rec["market"]]


def full_date(value) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def rating_fields(rating) -> dict:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*", str(rating or ""))
    if not m:
        return {}
    return {"Rating": float(m.group(1)), "rating_scale": {"min": 0 if float(m.group(2)) == 100 else 1, "max": float(m.group(2))}}


def locator(url: str, native_id=None) -> dict:
    if url == LOCAL_OPTION_LIST:
        return {"kind": "document", "page": None, "section": "G60 equipment & price list (DE, July 2026), extracted to Markdown"}
    return {"kind": "web", "url": clean_url(url), "native_id": native_id, "timestamp_seconds": None}


class Batch:
    def __init__(self, name: str, channel: str, dataset_key: str, title: str, origin: str):
        self.name, self.channel, self.dataset_key, self.title, self.origin = name, channel, dataset_key, title, origin
        self.records, self.claims = [], []
        self.ext_records, self.ext_claims = {}, {}
        self.locators, self.dates, self.subjects = set(), [], Counter()
        self.limitations = list(PARAPHRASE_LIMITATIONS)
        self.method = ("Targeted web research by AI agents (Claude Code, run %s): WebFetch of pages found via WebSearch "
                       "or known review/spec URLs; one record per review/article/spec statement." % RUN_ID)
        self.query = None
        self.verification = "unverified"
        self.provenance_notes = ("Collected by research agents for the BMW 5 Series competitor analysis "
                                 "(competitors/README.md). Agent logs per source: competitors/raw/*.log.md.")
        self.artifact = {"path": None, "sha256": None}
        self.complete = False
        self.retrieved = None
        self.notes = []

    def manifest(self) -> dict:
        dates = sorted(d for d in self.dates if d)
        return {
            "document_type": "source", "schema_version": "1.0",
            "source_id": self.name, "dataset_key": self.dataset_key, "stream": "competitors", "channel": self.channel,
            "title": self.title, "locator": "; ".join(sorted(self.locators))[:2000] or self.dataset_key,
            "collected_at": self.collected_at if hasattr(self, "collected_at") else COLLECTED_AT,
            "collector": f"{COLLECTOR} (Claude Code research agents, run {RUN_ID})",
            "is_example": False, "normalized_record_count": len(self.records),
            "sampling": {
                "method": self.method, "query": self.query,
                "date_start": dates[0] if dates else None, "date_end": dates[-1] if dates else None,
                "retrieved_count": self.retrieved if self.retrieved is not None else len(self.records),
                "complete": self.complete, "limitations": list(dict.fromkeys(self.limitations)),
            },
            "provenance": {"origin": self.origin, "verification": self.verification, "notes": self.provenance_notes},
            "artifact": self.artifact,
            "export_permissions": {
                "git": True, "external_llm": None,
                "notes": "Stored on branch luis-competitors by the collector's decision. External LLM use not decided "
                         "by the team yet.",
            },
            "review_status": "pending",
        }


def build_web_batches(recs: list[dict], excerpts: dict) -> dict[str, Batch]:
    batches: dict[str, Batch] = {}
    reviews = defaultdict(list)

    def batch_for(rec: dict, kind: str, channel: str) -> Batch:
        dom = domain(rec["url"])
        bmw = rec["brand"] == "BMW"
        name = f"{PREFIX}-{rec['market'].lower()}-{slug(dom).replace('_', '-')}-{kind}" + ("-bmw" if bmw else "")
        if name not in batches:
            what = {"equipment": "equipment/specification facts"}.get(kind, f"{kind.replace('-', ' ')} feedback")
            subject = "BMW 5 Series (baseline)" if bmw else "BMW 5 Series competitors"
            origin = "official" if (channel in ("manufacturer_website", "bmw_option_list")) else "third_party"
            kind_key = "specifications" if kind == "equipment" else kind.replace("-", "_")
            b = Batch(name, channel, f"web:{dom}:{kind_key}", f"{rec['market']} · {dom} · {what} for {subject}", origin)
            if dom == "bmw-option-list":
                b.dataset_key = "bmw-option-list:G60:DE-2026-07"
                b.method = "Read from the local Markdown extraction of BMW's G60 DE price list by a research agent."
                b.limitations = ["text_original is the agent's summary of the option-list entry, not the catalog wording."]
            batches[name] = b
        batches[name].locators.add(dom if dom == "bmw-option-list" else f"https://{dom}/")
        return batches[name]

    for rec in recs:
        if rec["kind"] == "feedback":
            if "nhtsa" in (rec.get("source_name") or "").lower():
                continue  # superseded by the verbatim NHTSA batches
            reviews[rec["review_ref"]].append(rec)

    for ref, items in reviews.items():
        first = items[0]
        b = batch_for(first, KIND_LABEL[first["source_type"]], CHANNEL[first["source_type"]])
        eid, _ = entity_for(first)
        statements = [i["statement"].strip() for i in items]
        quotes = [i["quote"] for i in items if i.get("quote")]
        text = "Collector paraphrase (not verbatim source text): " + " ".join(statements)
        if quotes:
            text += " Original excerpt(s), from tool summaries: " + " ".join(f"«{q}»" for q in quotes)
        h = hashlib.sha256("\x1f".join([first["url"], str(first.get("published")), first["model"], *statements]).encode()).hexdigest()
        record_id = f"{COLLECTOR}:{ref}"
        record = {
            "document_type": "record", "schema_version": "1.0", "record_id": record_id, "source_id": b.name,
            "dedup_key": f"{b.dataset_key}:sha256:{h[:20]}", "record_kind": "feedback",
            "locator": locator(first["url"]), "content_date": full_date(first.get("published")), "content_datetime": None,
            "subject_ids": [eid], "markets": markets_for(first), "text_original": text, "language": "en",
            "translation_en": None, "metric": None, "availability": None, "source_fields": rating_fields(first.get("rating")),
        }
        b.records.append(record)
        b.subjects[eid] += 1
        b.dates.append(full_date(first.get("published")))
        b.ext_records[record_id] = {
            "review_ref": ref, "agent": first["agent"], "source_name": first.get("source_name"),
            "source_type": first["source_type"], "source_language": first.get("language"),
            "published": first.get("published"), "model_year": first.get("model_year"),
            "powertrain": first.get("powertrain"), "generation_label": first.get("generation"),
            "market": first["market"], "country": first.get("country"), "evidence_tier": first.get("evidence_tier"),
        }
        for i in items:
            claim_id = f"{COLLECTOR}:{i['record_id']}"
            vfc = i.get("vfc_level2")
            fkey = VFC_ALIASES.get(vfc) or (slug(vfc) if vfc else None)
            claim_quotes = [i["statement"].strip()] + ([i["quote"]] if i.get("quote") and i["quote"] in text else [])
            compared = i.get("compared_to")
            b.claims.append({
                "document_type": "claim", "schema_version": "1.0", "claim_id": claim_id, "record_id": record_id,
                "feature_key": fkey, "feature_label": vfc or f"theme: {i['theme']}",
                "claim_type": CLAIM_TYPE[i["feedback_type"]], "summary": i["statement"].strip(),
                "quotes": list(dict.fromkeys(claim_quotes)),
                "competitors_mentioned": [compared] if (i.get("comparison") and isinstance(compared, str) and compared) else [],
                "producer": {"method": "llm", "name": MODEL, "version": MODEL, "run_id": RUN_ID},
                "review_status": "pending", "source_fields": {},
            })
            b.ext_claims[claim_id] = {k: v for k, v in i.items() if k not in ("agent",)}

    for rec in recs:
        if rec["kind"] != "equipment":
            continue
        channel = ("bmw_option_list" if rec["url"] == LOCAL_OPTION_LIST
                   else "manufacturer_website" if rec.get("source_type") == "manufacturer" else "editorial_review")
        b = batch_for(rec, "equipment", channel)
        eid, _ = entity_for(rec)
        fkey = FEATURES[rec["feature"]][0]
        exc = excerpts.get(rec["record_id"])
        text = (f"Collector summary (not verbatim source text): {FEATURES[rec['feature']][1]} — "
                f"{rec['availability'].replace('_', ' ')}" + (f": {rec['value']}" if rec.get("value") else "") + "."
                + (f" Notes: {rec['notes']}" if rec.get("notes") else ""))
        if exc:
            text += f" Exact excerpt from {exc['url']} (fetched {exc['fetched_at']}, whitespace normalised): «{exc['excerpt']}»"
        record_id = f"{COLLECTOR}:{rec['record_id']}"
        dedup = f"{b.dataset_key}:{eid}:{rec['market']}:{fkey}:{slug(rec.get('trim_scope') or 'all')}"
        n = 2
        while any(r["dedup_key"] == dedup for r in b.records):
            dedup = f"{b.dataset_key}:{eid}:{rec['market']}:{fkey}:{slug(rec.get('trim_scope') or 'all')}:{n}"
            n += 1
        b.records.append({
            "document_type": "record", "schema_version": "1.0", "record_id": record_id, "source_id": b.name,
            "dedup_key": dedup, "record_kind": "feature_availability", "locator": locator(rec["url"]),
            "content_date": None, "content_datetime": None, "subject_ids": [eid],
            "markets": ["DE"] if rec["url"] == LOCAL_OPTION_LIST else markets_for(rec),
            "text_original": text, "language": "en", "translation_en": None, "metric": None,
            "availability": {"feature_key": fkey, "status": AVAILABILITY[rec["availability"]], "model_years": [],
                             "trim": rec.get("trim_scope"), "package": None, "price": None},
            "source_fields": {},
        })
        b.subjects[eid] += 1
        b.ext_records[record_id] = {**{k: v for k, v in rec.items() if k != "agent"}, "agent": rec["agent"],
                                    "exact_excerpt": exc}
    for b in batches.values():
        if any(e.get("exact_excerpt") for e in b.ext_records.values()):
            b.limitations.append("Some records carry an exact excerpt (see text_original); it was taken from the raw "
                                 "page text by competitors/tools/fetch_excerpts.py and matched by keyword, then reviewed.")
    return batches


def strip_vin(text: str) -> str:
    return re.sub(r"\b[A-HJ-NPR-Z0-9]{17}\b", "[VIN removed]", text)


def build_nhtsa_batches() -> dict[str, Batch]:
    batches = {}
    raw_dir = REPO / "data" / "nhtsa"
    for key, (label, make, years, inc, exc) in nhtsa.VEHICLES.items():
        path = raw_dir / f"{key}.json"
        if not path.exists():
            continue
        items = json.loads(path.read_text())
        if not items:
            continue
        name = f"{PREFIX}-us-nhtsa-complaints-{key.replace('_', '-')}"
        b = Batch(name, "other", "nhtsa:complaints", f"US · NHTSA owner complaints · {label}", "official")
        b.collected_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        b.method = ("NHTSA complaints API (complaintsByVehicle) for every NHTSA model name matching the vehicle, "
                    "model years " + f"{min(years)}-{max(years)}" + "; all returned complaints, deduplicated by ODI number. "
                    "Script: competitors/tools/nhtsa.py")
        b.query = f"make={make}; model regex={inc}; exclude={exc}; model years {min(years)}-{max(years)}"
        b.limitations = [
            "Complaints are self-reported and almost all describe defects; volume scales with fleet size and age.",
            "NHTSA model buckets are noisy (e.g. EQE sedan and SUV share buckets; complaints mentioning 'SUV' were dropped).",
            "Narratives are NHTSA's published text (public domain); 17-character VIN-like tokens were replaced.",
            "A complaint filed for several vehicles appears once per vehicle batch (dedup_key = ODI number + vehicle).",
        ]
        b.verification = "provenance_checked"
        b.provenance_notes = "Fetched directly from api.nhtsa.gov by competitors/tools/nhtsa.py; raw JSON kept in data/nhtsa/."
        b.artifact = {"path": f"data/nhtsa/{key}.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        b.complete = True
        eid = NHTSA_ENTITY[key]
        for c in items:
            filed = c.get("dateComplaintFiled")
            iso = datetime.strptime(filed, "%m/%d/%Y").strftime("%Y-%m-%d") if filed else None
            text = strip_vin(c.get("summary") or "").strip() or "(no narrative)"
            labels = [{"name": k, "value": None if c.get(k) is None else str(c.get(k))}
                      for k in ("components", "dateOfIncident", "crash", "fire", "numberOfInjuries", "numberOfDeaths")]
            labels.append({"name": "nhtsa_model", "value": f"{c['query']['model']} MY{c['query']['modelYear']}"})
            record_id = f"{COLLECTOR}:nhtsa:{key}:{c['odiNumber']}"
            b.records.append({
                "document_type": "record", "schema_version": "1.0", "record_id": record_id, "source_id": name,
                "dedup_key": f"nhtsa:complaints:{c['odiNumber']}:{key}", "record_kind": "feedback",
                "locator": {"kind": "web", "url": c["query_url"], "native_id": str(c["odiNumber"]), "timestamp_seconds": None},
                "content_date": iso, "content_datetime": None, "subject_ids": [eid], "markets": ["US"],
                "text_original": text, "language": "en", "translation_en": None, "metric": None, "availability": None,
                "source_fields": {"original_labels": labels},
            })
            b.dates.append(iso)
            b.subjects[eid] += 1
            b.ext_records[record_id] = {
                "vehicle_key": key, "themes": nhtsa.themes_for(c.get("components") or "", c.get("summary") or ""),
                "recall_related": bool(nhtsa.RECALL.search(c.get("summary") or "")),
                "theme_method": "rule-based mapping of NHTSA components + narrative keywords (nhtsa.themes_for)",
            }
        b.locators.add("https://api.nhtsa.gov/complaints/complaintsByVehicle")
        batches[name] = b
    return batches


def write_batch(b: Batch) -> None:
    d = BATCHES / b.name
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.json").write_text(json.dumps(b.manifest(), ensure_ascii=False, indent=2) + "\n")
    (d / "records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in b.records))
    if b.claims:
        (d / "claims.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in b.claims))
    (d / "luis_extensions.json").write_text(json.dumps({
        "description": "Fields from competitors/findings.jsonl that the contract has no place for, keyed by "
                       "contract record_id / claim_id. Not read by the team validator or exporter.",
        "records": b.ext_records, "claims": b.ext_claims,
    }, ensure_ascii=False, indent=1) + "\n")
    kinds = Counter(r["record_kind"] for r in b.records)
    claim_types = Counter(c["claim_type"] for c in b.claims)
    lines = [
        f"# {b.name}", "", b.title, "",
        "| | |", "| --- | --- |",
        f"| Channel / dataset | `{b.channel}` / `{b.dataset_key}` |",
        f"| Records | {len(b.records)} ({', '.join(f'{k}: {n}' for k, n in kinds.items())}) |",
        f"| Claims | {len(b.claims)}" + (f" ({', '.join(f'{k}: {n}' for k, n in claim_types.most_common())})" if b.claims else "") + " |",
        f"| Subjects | {', '.join(f'`{s}` ({n})' for s, n in b.subjects.most_common())} |",
        f"| Collected | {b.manifest()['collected_at']} by {COLLECTOR} (run `{RUN_ID}`) |",
        "", "## Method", "", b.method, "", "## Limitations", "",
    ] + [f"- {x}" for x in dict.fromkeys(b.limitations)] + [
        "", "## Mapping notes", "",
        "- Feedback: one record per review/article (`review_ref`), one claim per statement. Claim types: Likes → praise, "
        "Defect → defect, Wants → new_request, Difficult to Use → other (original type in `luis_extensions.json`).",
        "- Claim `feature_key` is the slug of the best-matching BMW VFC level2 topic where the agent assigned one, else null; "
        "proposed keys are listed in `competitors/contract/catalog_additions.json`.",
        "- Equipment: standard → present, optional → optional, not_available → absent, unknown → unknown.",
        "- Theme, evidence tier, comparison verdict, model year, powertrain, original language: `luis_extensions.json`.",
        "- Status: source and claims `pending`; `export_permissions.external_llm` null (team decision).",
    ]
    (d / "notes.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="write only batches whose name contains this substring (pilot)")
    args = ap.parse_args()

    recs = [json.loads(l) for l in (ROOT / "findings.jsonl").read_text().splitlines() if l.strip()]
    exc_path = SIDECARS / "excerpts.json"
    excerpts = json.loads(exc_path.read_text())["excerpts"] if exc_path.exists() else {}

    batches = {**build_web_batches(recs, excerpts), **build_nhtsa_batches()}
    if args.only:
        batches = {k: v for k, v in batches.items() if args.only in k}
    if BATCHES.exists():
        shutil.rmtree(BATCHES)
    for b in batches.values():
        write_batch(b)

    # Catalog additions: entities used + feature keys used
    entities = {}
    for rule in ENTITY_RULES:
        if rule[3].startswith("competitor:"):
            entities[rule[3]] = {"entity_id": rule[3], "type": "vehicle_model", "label": rule[4], "target": False}
    used_entities = {s for b in batches.values() for r in b.records for s in r["subject_ids"]}
    features = {}
    for fid, (key, label) in FEATURES.items():
        theme = next(t for f, t in [("F01", "hmi_infotainment"), ("F02", "hmi_infotainment"), ("F03", "climate"),
                                    ("F04", "hmi_infotainment"), ("F05", "connectivity_app_digital"),
                                    ("F06", "connectivity_app_digital"), ("F07", "access_locking"),
                                    ("F08", "adas_parking"), ("F09", "adas_parking"), ("F10", "seats_comfort"),
                                    ("F11", "seats_comfort"), ("F12", "seats_comfort"), ("F13", "ride_handling"),
                                    ("F14", "ride_handling"), ("F15", "range_charging_efficiency"),
                                    ("F16", "range_charging_efficiency"), ("F17", "space_practicality"),
                                    ("F18", "space_practicality"), ("F19", "audio_acoustics"),
                                    ("F20", "interior_design_quality")] if fid.startswith(f))
        features[key] = {"feature_key": key, "label": label, "area": theme, "origin": f"equipment benchmark {fid}"}
    themes = json.loads((ROOT / "themes.json").read_text())["vfc_level2_to_theme"]
    for b in batches.values():
        for c in b.claims:
            k = c["feature_key"]
            if k and k not in features:
                features[k] = {"feature_key": k, "label": c["feature_label"], "area": themes.get(c["feature_label"]),
                               "origin": "BMW VFC level2 topic (best match assigned by research agent)"}
    SIDECARS.mkdir(exist_ok=True)
    (SIDECARS / "catalog_additions.json").write_text(json.dumps({
        "description": "Append to research/catalog/entities.json and features.json (feat/research-handoff). "
                       "Status: proposed by collector luis, pending orchestrator review. 'area' = our theme id.",
        "entities": [e for k, e in sorted(entities.items()) if k in used_entities],
        "features": sorted(features.values(), key=lambda f: f["feature_key"]),
    }, ensure_ascii=False, indent=2) + "\n")

    # comparisons.json
    support = defaultdict(list)
    for b in batches.values():
        for r in b.records:
            for s in r["subject_ids"]:
                support[(s, b.name[len(PREFIX) + 1:].split("-")[0])].append(r["record_id"])
    comps = []
    for rec in recs:
        if rec["kind"] != "competitor" or rec["brand"] == "BMW":
            continue
        eid, _ = entity_for(rec)
        target = "bmw:G68" if rec["market"] == "CN" else "bmw:G60"
        comps.append({
            "comparison_id": f"{COLLECTOR}:{rec['record_id']}", "target_bmw_id": target, "competitor_entity_id": eid,
            "market": rec["market"], "model_years": [], "class_body": None,
            "powertrains": rec.get("powertrains"), "price_range": None,
            "launched": rec.get("launched"), "rationale": rec.get("rationale"),
            "next_generation": rec.get("next_generation"), "source_url": rec.get("url"),
            "supporting_record_ids": sorted(support.get((eid, rec["market"].lower()), [])),
            "review_status": "pending",
        })
    (SIDECARS / "comparisons.json").write_text(json.dumps({
        "description": "Proposed BMW 5 Series <-> competitor matches (manual review sidecar per agent-competitors.md). "
                       "class_body and price_range stay null where no source established them.",
        "comparisons": comps}, ensure_ascii=False, indent=2) + "\n")
    (SIDECARS / "outlook.json").write_text(json.dumps({
        "description": "Announced/reported/rumoured changes 2026-2030. Announcements are not availability evidence, "
                       "so they are not exported as records.",
        "outlook": [r for r in recs if r["kind"] == "outlook"]}, ensure_ascii=False, indent=2) + "\n")
    mentions = [{**r, "bmw_dedup_key": f"bmw-feedback:G60:{r['bmw_feedback_id']}"} for r in recs if r["kind"] == "bmw_mention"]
    (SIDECARS / "bmw_mentions.json").write_text(json.dumps({
        "description": "BMW G60 verbatims that name a competitor: labels only, no BMW text. Join to the BMW agent's "
                       "feedback records via bmw_dedup_key (dataset_key 'bmw-feedback:G60' + feedback ID).",
        "mentions": mentions}, ensure_ascii=False, indent=2) + "\n")

    n_rec = sum(len(b.records) for b in batches.values())
    n_cl = sum(len(b.claims) for b in batches.values())
    print(f"{len(batches)} batches, {n_rec} records, {n_cl} claims, {len(comps)} comparisons, "
          f"{len(entities)} entities, {len(features)} feature keys")


if __name__ == "__main__":
    main()
