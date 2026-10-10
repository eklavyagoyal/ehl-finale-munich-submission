"""Scrape app reviews from the Apple App Store and Google Play into the review warehouse.

Product-, market- and region-agnostic: everything specific lives in a YAML config
(see scrapers/configs/my_bmw.yaml). Reruns are incremental: paging stops once a
page holds only reviews that are already stored. Reviewer names are never stored.

Usage (from the repo root):
    python -m scrapers.app_reviews discover "My BMW" --countries de us cn
    python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml
    python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml --stores app_store --full
"""

import argparse
import json
import random
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import yaml
from google_play_scraper import Sort, app as gp_app, reviews as gp_reviews, search as gp_search

from scrapers import warehouse

APPLE_PAGE_SIZE = 50
APPLE_MAX_PAGES = 10  # hard limit of Apple's public review feed
GOOGLE_PAGE_SIZE = 200
# Apple serves an empty review feed to browser-like user agents.
USER_AGENT = "app-review-scraper/1.0 (product research)"

# Concurrent requests per store, to stay polite and avoid throttling.
APPLE_SLOTS = threading.BoundedSemaphore(3)
GOOGLE_SLOTS = threading.BoundedSemaphore(4)


def http_json(url, attempts=4):
    """GET a JSON document, retrying transient failures with exponential backoff."""
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt + random.random())


# --- Apple App Store --------------------------------------------------------

def apple_app_info(app_id, country):
    results = http_json(f"https://itunes.apple.com/lookup?id={app_id}&country={country}")["results"]
    r = results[0] if results else {}
    return {"store": "app_store", "store_app_id": str(app_id), "app_name": r.get("trackName"),
            "bundle_id": r.get("bundleId"), "developer": r.get("sellerName")}


def apple_page(app_id, market, page, attempts=5):
    """One feed page. The feed intermittently returns an empty page mid-way, so retry."""
    url = (f"https://itunes.apple.com/{market}/rss/customerreviews/"
           f"page={page}/id={app_id}/sortby=mostrecent/json")
    for attempt in range(attempts):
        with APPLE_SLOTS:
            entries = http_json(url)["feed"].get("entry", [])
        if isinstance(entries, dict):  # a single entry comes back as an object
            entries = [entries]
        page_reviews = [e for e in entries if "im:rating" in e]
        if page_reviews:
            return page_reviews
        time.sleep(2 ** attempt)
    return []


def apple_reviews(app_id, market, limit, known_ids, date_from=None):
    out, empty_pages = [], 0
    for page in range(1, APPLE_MAX_PAGES + 1):
        page_reviews = apple_page(app_id, market, page)
        if not page_reviews:
            empty_pages += 1
            if empty_pages == 2 or page == 1:  # two empty pages in a row: end of the feed
                break
            continue
        empty_pages = 0
        new, too_old = 0, False
        for e in page_reviews:
            when = datetime.fromisoformat(e["updated"]["label"])
            if date_from and when.date() < date_from:
                too_old = True
                continue
            review_id = f"app_store:{e['id']['label']}"
            new += review_id not in known_ids
            out.append({
                "store": "app_store", "store_app_id": str(app_id), "market": market,
                "review_id": review_id,
                "datetime": when,
                "content": f"{e['title']['label']}. {e['content']['label']}".strip(),
                "rating": int(e["im:rating"]["label"]),
                "app_version": e.get("im:version", {}).get("label") or None,
            })
        # Newest first: an all-known page means we're caught up; an old review means we're past date_from.
        if new == 0 or too_old or len(out) >= limit:
            break
        time.sleep(0.5)
    return out[:limit]


# --- Google Play ------------------------------------------------------------

def google_app_info(package, country, lang):
    a = gp_app(package, lang=lang, country=country)
    return {"store": "google_play", "store_app_id": package, "app_name": a.get("title"),
            "bundle_id": package, "developer": a.get("developer")}


def google_reviews(package, market, lang, limit, known_ids, date_from=None):
    out, token = [], None
    while len(out) < limit:
        with GOOGLE_SLOTS:
            batch, token = gp_reviews(package, lang=lang, country=market, sort=Sort.NEWEST,
                                      count=min(GOOGLE_PAGE_SIZE, limit - len(out)),
                                      continuation_token=token)
        new, too_old = 0, False
        for r in batch:
            when = r["at"].replace(tzinfo=timezone.utc)
            if date_from and when.date() < date_from:
                too_old = True
                continue
            review_id = f"google_play:{r['reviewId']}"
            new += review_id not in known_ids
            out.append({
                "store": "google_play", "store_app_id": package, "market": market,
                "review_id": review_id,
                "datetime": when,
                "content": (r["content"] or "").strip(),
                "rating": r["score"],
                "app_version": r.get("appVersion") or r.get("reviewCreatedVersion"),
            })
        if not batch or token is None or new == 0 or too_old:
            break
        time.sleep(0.5)
    return out[:limit]


# --- Commands ---------------------------------------------------------------

def jobs_from_config(config, stores, markets_filter):
    """Expand the config into one (store, app_id, market, lang) job per country store."""
    for entry in config["apps"]:
        if stores and entry["store"] not in stores:
            continue
        markets = entry["markets"]
        if isinstance(markets, list):
            markets = {m: None for m in markets}
        for market, lang in markets.items():
            if markets_filter and market.lower() not in markets_filter:
                continue
            yield entry["store"], str(entry["app_id"]), market.lower(), lang


def scrape(config_path, stores=None, markets=None, full=False, workers=8):
    config = yaml.safe_load(open(config_path, encoding="utf-8"))
    limit = config.get("scrape", {}).get("max_reviews_per_market", 2000)
    date_from = config.get("scrape", {}).get("date_from")  # YAML parses it as a date; None = no limit
    known_ids = set() if full else set(warehouse.read_table("fact_review")["review_id"])
    jobs = list(jobs_from_config(config, stores, {m.lower() for m in markets or []}))

    def run(job):
        store, app_id, market, lang = job
        if store == "app_store":
            return apple_app_info(app_id, market), apple_reviews(app_id, market, limit, known_ids, date_from)
        return (google_app_info(app_id, market, lang),
                google_reviews(app_id, market, lang, limit, known_ids, date_from))

    apps, reviews = {}, {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run, job): job for job in jobs}
        for future in as_completed(futures):
            store, app_id, market, _ = futures[future]
            try:
                info, got = future.result()
            except Exception as e:  # one failing store/market should not stop the run
                print(f"{store}/{app_id}/{market}: failed ({e})")
                continue
            if info["app_name"]:
                apps[(store, app_id)] = info
            fresh = [r for r in got if r["review_id"] not in reviews and r["review_id"] not in known_ids]
            reviews.update((r["review_id"], r) for r in got)
            print(f"{store}/{app_id}/{market}: {len(got)} fetched, {len(fresh)} new")

    tables = warehouse.build_tables(list(reviews.values()), list(apps.values()))
    for name, rows in tables.items():
        total = warehouse.upsert(name, rows)
        print(f"{name}: {total} rows")

    if date_from:  # keep stored reviews of this config's apps inside the configured window
        app_ids = {warehouse.surrogate_key(e["store"], str(e["app_id"])) for e in config["apps"]}
        removed = warehouse.delete_where("fact_review", lambda t: t["app_id"].isin(app_ids)
                                         & (pd.to_datetime(t["content_date"]).dt.date < date_from))
        if removed:
            print(f"fact_review: removed {removed} stored reviews older than {date_from}")


def discover(term, countries, lang):
    """Print candidate app ids per country, to fill in a new config."""
    for country in countries:
        print(f"== {country}")
        q = urllib.parse.quote(term)
        for r in http_json(f"https://itunes.apple.com/search?term={q}&entity=software"
                           f"&country={country}&limit=5")["results"]:
            print(f"  app_store    {r['trackId']:<12} {r['trackName']}  ({r['sellerName']})")
        for r in gp_search(term, lang=lang, country=country, n_hits=5):
            print(f"  google_play  {r['appId']:<40} {r['title']}  ({r.get('developer')})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scrape", help="scrape the apps and markets in a config file")
    p.add_argument("config")
    p.add_argument("--stores", nargs="+", choices=["app_store", "google_play"])
    p.add_argument("--markets", nargs="+", help="only these country codes, e.g. de us")
    p.add_argument("--full", action="store_true", help="ignore stored reviews and page to the limit")
    p.add_argument("--workers", type=int, default=8)

    p = sub.add_parser("discover", help="look up app ids for a search term")
    p.add_argument("term")
    p.add_argument("--countries", nargs="+", default=["us"])
    p.add_argument("--lang", default="en")

    args = parser.parse_args()
    if args.command == "scrape":
        scrape(args.config, args.stores, args.markets, args.full, args.workers)
    else:
        discover(args.term, args.countries, args.lang)


if __name__ == "__main__":
    main()
