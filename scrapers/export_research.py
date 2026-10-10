"""Export the scraped warehouse into research-contract batches (docs/research-data-contract.md).

One batch per app storefront (store, app, market) and one per YouTube search market,
each with source.json, records.jsonl and notes.md. Output goes to the git-ignored
outputs/research/submissions/ until the team settles export permissions. Batches with
no usable records are not written; they are listed in the run summary instead.

Usage (from the repo root):
    python -m scrapers.export_research
    python -m scrapers.export_research --channels app_store youtube --markets de
"""

import argparse
import getpass
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from scrapers import warehouse

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "outputs" / "research" / "submissions"
CONFIGS = ROOT / "scrapers" / "configs"
VALIDATOR = ROOT / "scripts" / "validate_research.py"

APP_CHANNELS = {"app_store", "google_play"}
APP_LIMITATIONS = {
    "app_store": "Apple's public review feed exposes only the ~500 most recent reviews per storefront; "
                 "it also skips the occasional empty page, so a few reviews can be missing.",
    "google_play": "Google Play filters reviews mainly by language; the storefront country is a weak market signal.",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_id(dedup_key, text):
    """Stable on identical reruns; a changed text yields a new snapshot (contract §Identity)."""
    return f"{dedup_key}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def table_time(name):
    """Last write of a warehouse table: the closest record of collection time we have."""
    path = warehouse.WAREHOUSE_DIR / f"{name}.parquet"
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_configs():
    """Google Play review languages, app date windows and YouTube settings, keyed for lookup."""
    gp_lang, app_date_from, youtube = {}, {}, None
    for path in sorted(CONFIGS.glob("*.yaml")):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        for entry in config.get("apps", []):
            app_date_from[(entry["store"], str(entry["app_id"]))] = config.get("scrape", {}).get("date_from")
            if entry["store"] == "google_play" and isinstance(entry["markets"], dict):
                for market, lang in entry["markets"].items():
                    gp_lang[(str(entry["app_id"]), market.upper())] = lang
        if "vehicle" in config and "markets" in config:
            youtube = config  # one YouTube config today; extend to a list when there are more
    return gp_lang, app_date_from, youtube


def source_doc(source_id, dataset_key, channel, title, locator, collected_at, collector, records,
               method, query, retrieved, limitations, notes, artifact, date_from=None):
    dates = sorted(r["content_date"] for r in records)
    # The sampling window starts at the configured date_from when there is one.
    date_start = date_from.isoformat() if date_from else dates[0]
    return {
        "document_type": "source", "schema_version": "1.0",
        "source_id": source_id, "dataset_key": dataset_key, "stream": "social", "channel": channel,
        "title": title, "locator": locator, "collected_at": collected_at, "collector": collector,
        "is_example": False, "normalized_record_count": len(records),
        "sampling": {"method": method, "query": query, "date_start": date_start, "date_end": dates[-1],
                     "retrieved_count": retrieved, "complete": False, "limitations": limitations},
        "provenance": {"origin": "third_party", "verification": "provenance_checked", "notes": notes},
        "artifact": {"path": str(artifact.relative_to(ROOT)), "sha256": sha256(artifact)},
        # Unresolved until the team decides; the contract treats null as "not yet allowed".
        "export_permissions": {"git": None, "external_llm": None,
                               "notes": "Unresolved: scraped third-party review text; keep out of Git and external LLMs until decided."},
        "review_status": "pending",
    }


def record_doc(source_id, dedup_key, text, locator, date, datetime_str, subject_ids, market, language, source_fields):
    return {
        "document_type": "record", "schema_version": "1.0",
        "record_id": snapshot_id(dedup_key, text), "source_id": source_id, "dedup_key": dedup_key,
        "record_kind": "feedback", "locator": locator,
        "content_date": date.isoformat(), "content_datetime": datetime_str,
        "subject_ids": subject_ids, "markets": [market], "text_original": text,
        "language": language, "translation_en": None, "metric": None, "availability": None,
        "source_fields": source_fields,
    }


def app_batches(collector, markets, channels, gp_lang, app_date_from):
    facts = warehouse.read_table("fact_review")
    apps = warehouse.read_table("dim_app").set_index("app_id")
    market_codes = warehouse.read_table("dim_market").set_index("market_id")["market_code"]
    facts = facts.assign(market_code=facts["market_id"].map(market_codes))
    collected_at = table_time("fact_review")
    artifact = warehouse.WAREHOUSE_DIR / "fact_review.parquet"

    for (app_id, market), group in facts.groupby(["app_id", "market_code"]):
        app = apps.loc[app_id]
        channel, store_app_id = app["store"], app["store_app_id"]
        if channel not in channels or (markets and market not in markets):
            continue
        dataset_key = f"{channel}:{store_app_id}:{market}"
        # Short app tag: App Store id, or the last part of the Play package (e.g. "row", "na").
        app_tag = slug(store_app_id.split(".")[-1])
        source_id = f"{collector}-{collected_at[:10].replace('-', '')}-{channel}-{slug(app['app_name'])}-{app_tag}-{market.lower()}"
        language = gp_lang.get((store_app_id, market)) if channel == "google_play" else None

        records, skipped = [], 0
        for r in group.sort_values(["content_datetime", "review_id"]).itertuples():
            if not r.content or not r.content.strip():
                skipped += 1  # rating-only review: no evidence text
                continue
            native = r.review_id.split(":", 1)[1]
            records.append(record_doc(
                source_id, f"{dataset_key}:{native}", r.content,
                {"kind": "table", "table": "fact_review", "native_id": native, "row_number": None},
                r.content_date, r.content_datetime, [], market, language,
                {"DimDateID": str(r.date_id), "DimAppID": str(r.app_id), "DimAppVersionID": str(r.app_version_id),
                 "DimOSID": str(r.os_id), "DimMarketID": str(r.market_id), "ReviewID": r.review_id,
                 "ContentDate": r.content_date.isoformat(), "ContentDateTime": r.content_datetime,
                 "Rating": int(r.rating), "Source": r.source, "rating_scale": {"min": 1, "max": 5}},
            ))
        limitations = [
            APP_LIMITATIONS[channel],
            "Market is the storefront country, not the reviewer's residence.",
            "Reviews concern the companion app, not a specific vehicle model; subject_ids stay empty "
            "until the catalog has an app entity.",
        ]
        if skipped:
            limitations.append(f"{skipped} rating-only reviews without text were not exported.")
        if not records:
            yield source_id, None, None, f"no reviews with text ({skipped} rating-only)"
            continue
        store_name = "App Store" if channel == "app_store" else "Google Play"
        locator = (f"https://apps.apple.com/{market.lower()}/app/id{store_app_id}" if channel == "app_store"
                   else f"https://play.google.com/store/apps/details?id={store_app_id}&gl={market}")
        source = source_doc(
            source_id, dataset_key, channel,
            f"{app['app_name']} ({store_name} {store_app_id}) customer reviews, {market} storefront",
            locator, collected_at, collector, records,
            f"{store_name} reviews, newest first, all available up to the scraper limit; scrapers/app_reviews.py",
            None, len(records) + skipped, limitations,
            f"Collected with scrapers/app_reviews.py from the public {store_name} review endpoints. "
            f"DimXxxID values are this warehouse's surrogate keys (see scrapers/warehouse.py), resolved into markets.",
            artifact, app_date_from.get((channel, store_app_id)),
        )
        yield source_id, source, records, None


def youtube_batches(collector, markets, config):
    facts = warehouse.read_table("fact_video_comment")
    if facts.empty:
        return
    videos = warehouse.read_table("dim_video").set_index("video_id")
    market_codes = warehouse.read_table("dim_market").set_index("market_id")["market_code"]
    vehicles = warehouse.read_table("dim_vehicle_model").set_index("vehicle_model_id")
    facts = facts.assign(market_code=facts["market_id"].map(market_codes))
    collected_at = table_time("fact_video_comment")
    artifact = warehouse.WAREHOUSE_DIR / "fact_video_comment.parquet"

    for (vehicle_id, market), group in facts.groupby(["vehicle_model_id", "market_code"]):
        if markets and market not in markets:
            continue
        vehicle = vehicles.loc[vehicle_id]
        subject = f"{vehicle['brand'].lower()}:{vehicle['vehicle_code']}"
        source_id = f"{collector}-{collected_at[:10].replace('-', '')}-youtube-{slug(vehicle['vehicle_code'])}-{market.lower()}"
        market_cfg = (config or {}).get("markets", {}).get(market.lower(), {})
        limits = (config or {}).get("limits", {})

        records = []
        for r in group.sort_values(["content_datetime", "comment_id"]).itertuples():
            if not r.content or not r.content.strip():
                continue
            native = r.comment_id.split(":", 1)[1]
            yt_id = videos.loc[r.video_id, "youtube_video_id"]
            records.append(record_doc(
                source_id, f"youtube:comment:{native}", r.content,
                {"kind": "web", "url": f"https://www.youtube.com/watch?v={yt_id}&lc={native}",
                 "native_id": native, "timestamp_seconds": None},
                r.content_date, r.content_datetime, [subject], market, None,
                {"Source": r.source, "ContentDateTime": r.content_datetime},
            ))
        if not records:
            yield source_id, None, None, "no comments with text"
            continue
        n_videos = group["video_id"].nunique()
        source = source_doc(
            source_id, "youtube:comments", "youtube",
            f"YouTube comments under {vehicle['brand']} {vehicle['series']} ({vehicle['vehicle_code']}) review videos, "
            f"{market} search market",
            "https://www.googleapis.com/youtube/v3/", collected_at, collector, records,
            f"YouTube Data API: search.list (relevance, {limits.get('videos_per_query', '?')} per query, "
            f"region {market}, language {market_cfg.get('language', '?')}), title filter for the vehicle, "
            f"then commentThreads newest first, up to {limits.get('comment_pages_per_video', '?')} pages of 100 "
            f"threads per video plus the replies the API includes; scrapers/youtube_comments.py",
            " | ".join(market_cfg.get("queries", [])) or None, len(records),
            [
                "Market is the search market (region + relevance language), not the commenter's location.",
                f"{n_videos} videos selected by search relevance and a title pattern; not a random sample of owners.",
                "Up to 3 pages of comment threads per video; replies beyond the 5 the API returns per thread are missing.",
                "Videos whose language tags all differ from the market language were dropped.",
                "Reply/thread links, like counts and video titles are kept in the warehouse but have no field "
                "in schema v1 source_fields.",
                f"subject_id {subject} also covers Touring (G61), i5 and M5 videos.",
            ],
            "Collected with scrapers/youtube_comments.py (spec docs/specs/youtube-scraper.md). "
            "Commenter names and channel ids are not stored.",
            artifact, limits.get("date_from"),
        )
        yield source_id, source, records, None


def notes_md(source, records):
    s = source["sampling"]
    limitations = "\n".join(f"- {item}" for item in s["limitations"])
    return f"""# {source['title']}

- **source_id:** `{source['source_id']}`
- **dataset_key:** `{source['dataset_key']}`
- **channel:** {source['channel']} · **collector:** {source['collector']} · **collected:** {source['collected_at']}
- **records:** {len(records)} (one per original review/comment; no claims extracted)
- **content dates:** {s['date_start']} to {s['date_end']}
- **review status:** pending · **export permissions:** unresolved (git and external LLM)

## Sampling

{s['method']}

Query: {s['query'] or 'none (store feed)'}

## Limitations

{limitations}

## Mapping notes

- `record_id` = `dedup_key` + first 12 hex characters of SHA-256(text): stable on identical reruns.
- Dates keep the source timezone offset; markets are ISO country codes.
- No catalog additions were made by this export.
"""


def write_batch(out_dir, source, records):
    stream_dir = out_dir / source["stream"] / source["source_id"]
    if stream_dir.exists():
        shutil.rmtree(stream_dir)  # rewrite the batch so no stale records survive
    stream_dir.mkdir(parents=True)
    (stream_dir / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (stream_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    (stream_dir / "notes.md").write_text(notes_md(source, records), encoding="utf-8")


def export(out_dir=DEFAULT_OUT, collector=None, channels=None, markets=None):
    collector = slug(collector or getpass.getuser())
    channels = set(channels or (APP_CHANNELS | {"youtube"}))
    markets = {m.upper() for m in markets} if markets else None
    gp_lang, app_date_from, youtube_config = load_configs()

    batches = []
    if channels & APP_CHANNELS:
        batches += app_batches(collector, markets, channels, gp_lang, app_date_from)
    if "youtube" in channels:
        batches += youtube_batches(collector, markets, youtube_config)

    written, total = 0, 0
    for source_id, source, records, skip_reason in batches:
        if source is None:
            print(f"skipped {source_id}: {skip_reason}")
            continue
        write_batch(out_dir, source, records)
        written += 1
        total += len(records)
        print(f"{source_id}: {len(records)} records")
    print(f"wrote {written} batches, {total} records to {out_dir}")
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--collector", help="name in batch ids (default: your user name)")
    parser.add_argument("--channels", nargs="+", choices=sorted(APP_CHANNELS | {"youtube"}))
    parser.add_argument("--markets", nargs="+", help="country codes, e.g. de gb")
    args = parser.parse_args()
    if not export(args.out, args.collector, args.channels, args.markets):
        sys.exit("nothing exported")
    if VALIDATOR.exists():  # present once the research-handoff branch is merged
        sys.exit(subprocess.call([sys.executable, str(VALIDATOR), str(args.out)]))
    print(f"validator not found ({VALIDATOR.relative_to(ROOT)}); validate after merging the research-handoff branch")


if __name__ == "__main__":
    main()
