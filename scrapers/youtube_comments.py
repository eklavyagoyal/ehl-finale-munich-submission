"""Scrape YouTube comments under vehicle review videos into the warehouse.

Vehicle-, market- and language-agnostic: everything specific lives in a YAML config
(see scrapers/configs/bmw_5_series_youtube.yaml). Reruns are incremental: comment
paging stops once a page holds only comments that are already stored. Commenter
names and channel ids are never stored. Spec: docs/specs/youtube-scraper.md

Needs YOUTUBE_API_KEY in the environment or in .env.

Usage (from the repo root):
    python -m scrapers.youtube_comments scrape scrapers/configs/bmw_5_series_youtube.yaml --dry-run
    python -m scrapers.youtube_comments scrape scrapers/configs/bmw_5_series_youtube.yaml
    python -m scrapers.youtube_comments scrape scrapers/configs/bmw_5_series_youtube.yaml --markets de
"""

import argparse
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import yaml

from scrapers import warehouse

API_URL = "https://www.googleapis.com/youtube/v3/"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
SEARCH_COST, LIST_COST = 100, 1  # quota units per call


class QuotaExceeded(Exception):
    pass


class CommentsUnavailable(Exception):
    """Comments are disabled, or the video is private or gone."""


def api_key():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key and ENV_FILE.exists():  # read only this one variable from .env
        for line in ENV_FILE.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "YOUTUBE_API_KEY":
                key = value.strip().strip("'\"")
    if not key:
        raise SystemExit("YOUTUBE_API_KEY is not set (environment or .env). See docs/specs/youtube-scraper.md step 1.")
    return key


def youtube_get(endpoint, params, attempts=4):
    """GET one API resource; retries network errors and 5xx with backoff."""
    query = urllib.parse.urlencode({**params, "key": api_key()})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(f"{API_URL}{endpoint}?{query}", timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            reasons = set()
            try:
                reasons = {err.get("reason") for err in json.load(e).get("error", {}).get("errors", [])}
            except Exception:
                pass
            if reasons & {"quotaExceeded", "dailyLimitExceeded"}:
                raise QuotaExceeded("YouTube API daily quota exceeded; rerun tomorrow") from e
            if reasons & {"commentsDisabled", "videoNotFound", "forbidden"} or e.code == 404:
                raise CommentsUnavailable(", ".join(sorted(r for r in reasons if r)) or str(e.code)) from e
            if e.code < 500 or attempt == attempts - 1:
                raise
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** attempt + random.random())


# --- Video discovery --------------------------------------------------------

def search_videos(query, market, language, published_after, max_results):
    data = youtube_get("search", {
        "part": "snippet", "type": "video", "q": query, "maxResults": max_results,
        "regionCode": market.upper(), "relevanceLanguage": language,
        "publishedAfter": f"{published_after}T00:00:00Z", "order": "relevance",
    })
    return [{"youtube_video_id": item["id"]["videoId"], "title": item["snippet"]["title"]}
            for item in data.get("items", [])]


def video_details(youtube_video_ids):
    details = {}
    for i in range(0, len(youtube_video_ids), 50):
        data = youtube_get("videos", {"part": "snippet,statistics", "id": ",".join(youtube_video_ids[i:i + 50])})
        for item in data.get("items", []):
            snippet, stats = item["snippet"], item.get("statistics", {})
            details[item["id"]] = {
                "title": snippet["title"],
                "channel_title": snippet.get("channelTitle"),
                "published_date": datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")).date(),
                "view_count": int(stats.get("viewCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                # Language tags set by the uploader; "zxx" means no spoken language.
                "languages": {lang for lang in (snippet.get("defaultAudioLanguage"),
                                                snippet.get("defaultLanguage")) if lang and lang != "zxx"},
            }
    return details


def discover_videos(config, markets):
    """Search each market's queries; keep videos whose title matches the vehicle.

    Returns {youtube_video_id: video dict}; the first market whose search finds a
    video owns it (spec §6). Videos whose language tags all differ from the market's
    language are dropped; untagged videos are kept.
    """
    vehicle, limits = config["vehicle"], config["limits"]
    pattern = re.compile(vehicle["title_pattern"], re.IGNORECASE)
    exclude = re.compile(vehicle["exclude_title_pattern"], re.IGNORECASE) if vehicle.get("exclude_title_pattern") else None
    videos = {}
    for market in markets:
        m = config["markets"][market]
        for query in m["queries"]:
            found = search_videos(query, market, m["language"], vehicle["published_after"],
                                  limits["videos_per_query"])
            kept = [v for v in found if pattern.search(v["title"])
                    and not (exclude and exclude.search(v["title"]))]
            new = 0
            for v in kept:
                if v["youtube_video_id"] not in videos:
                    videos[v["youtube_video_id"]] = {**v, "market": market, "search_query": query,
                                                     "search_language": m["language"]}
                    new += 1
            print(f"{market} | {query!r}: {len(found)} found, {len(kept)} match the vehicle, {new} new")
    for vid, d in video_details(list(videos)).items():
        videos[vid].update(d)
    kept = {}
    for vid, v in videos.items():
        if "published_date" not in v:  # deleted or private
            continue
        bases = {lang.split("-")[0].lower() for lang in v["languages"]}
        if bases and v["search_language"] not in bases:
            print(f"  dropped {vid} {v['title'][:60]!r}: language {sorted(v['languages'])}, market wants {v['search_language']}")
            continue
        kept[vid] = v
    return kept


# --- Comments ---------------------------------------------------------------

def comment_row(c, comment_id, parent_comment_id, reply_count):
    s = c["snippet"]
    when = datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
    return {"comment_id": comment_id, "parent_comment_id": parent_comment_id, "datetime": when,
            "content": (s.get("textDisplay") or "").strip(), "like_count": int(s.get("likeCount", 0)),
            "reply_count": reply_count}


def fetch_comments(youtube_video_id, max_pages, known_ids):
    """Comment threads newest first, plus the replies the API includes with them."""
    rows, token = [], None
    for _ in range(max_pages):
        params = {"part": "snippet,replies", "videoId": youtube_video_id, "maxResults": 100,
                  "order": "time", "textFormat": "plainText"}
        if token:
            params["pageToken"] = token
        data = youtube_get("commentThreads", params)
        new = 0
        for thread in data.get("items", []):
            top = thread["snippet"]["topLevelComment"]
            top_id = f"youtube:{top['id']}"
            new += top_id not in known_ids
            rows.append(comment_row(top, top_id, None, int(thread["snippet"].get("totalReplyCount", 0))))
            for reply in thread.get("replies", {}).get("comments", []):
                rows.append(comment_row(reply, f"youtube:{reply['id']}", top_id, 0))
        token = data.get("nextPageToken")
        if not token or new == 0:  # newest first: an all-known page means we're caught up
            break
    return rows


# --- Rows -------------------------------------------------------------------

def build_tables(config, videos, comments_by_video):
    v = config["vehicle"]
    vehicle_model_id = warehouse.surrogate_key(v["brand"], v["code"])
    tables = {
        "dim_vehicle_model": [{"vehicle_model_id": vehicle_model_id, "brand": v["brand"],
                               "vehicle_code": v["code"], "series": v["series"]}],
        "dim_video": [], "dim_market": {}, "dim_date": {}, "fact_video_comment": [],
    }
    for yt_id, video in videos.items():
        video_id = warehouse.surrogate_key("youtube", yt_id)
        tables["dim_video"].append({
            "video_id": video_id, "youtube_video_id": yt_id, "title": video["title"],
            "channel_title": video["channel_title"], "published_date": video["published_date"],
            "view_count": video["view_count"], "comment_count": video["comment_count"],
            "search_query": video["search_query"], "search_language": video["search_language"],
            "video_language": ",".join(sorted(video["languages"])) or None,
        })
        market = warehouse.dim_market_row(video["market"])
        tables["dim_market"][market["market_id"]] = market
        for c in comments_by_video.get(yt_id, []):
            d = c["datetime"].date()
            tables["dim_date"][warehouse.date_id(d)] = warehouse.dim_date_row(d)
            tables["fact_video_comment"].append({
                "date_id": warehouse.date_id(d), "video_id": video_id, "market_id": market["market_id"],
                "vehicle_model_id": vehicle_model_id, "comment_id": c["comment_id"],
                "parent_comment_id": c["parent_comment_id"], "content_date": d,
                "content_datetime": c["datetime"].isoformat(), "content": c["content"],
                "like_count": c["like_count"], "reply_count": c["reply_count"], "source": "youtube",
            })
    tables["dim_market"] = list(tables["dim_market"].values())
    tables["dim_date"] = list(tables["dim_date"].values())
    return tables


# --- Command ----------------------------------------------------------------

def scrape(config_path, markets=None, dry_run=False, workers=4):
    config = yaml.safe_load(open(config_path, encoding="utf-8"))
    markets = [m.lower() for m in (markets or config["markets"])]
    unknown = set(markets) - set(config["markets"])
    if unknown:
        raise SystemExit(f"markets not in config: {', '.join(sorted(unknown))}")

    limits = config["limits"]
    searches = sum(len(config["markets"][m]["queries"]) for m in markets)
    max_videos = searches * limits["videos_per_query"]
    print(f"plan: {searches} searches, up to {max_videos} videos x {limits['comment_pages_per_video']} comment pages")
    print(f"quota: ~{searches * SEARCH_COST + max_videos * limits['comment_pages_per_video'] * LIST_COST:,} "
          f"units at most (daily default 10,000)")
    if dry_run:
        for m in markets:
            for q in config["markets"][m]["queries"]:
                print(f"  search {m} [{config['markets'][m]['language']}]: {q}")
        return

    known_ids = set(warehouse.read_table("fact_video_comment")["comment_id"])
    videos, comments = {}, {}
    try:
        videos = discover_videos(config, markets)
        print(f"{len(videos)} videos kept")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch_comments, vid, limits["comment_pages_per_video"], known_ids): vid
                       for vid in videos}
            for future in as_completed(futures):
                vid = futures[future]
                try:
                    comments[vid] = future.result()
                except CommentsUnavailable as e:
                    print(f"  {vid}: skipped ({e})")
                    continue
                new = sum(c["comment_id"] not in known_ids for c in comments[vid])
                print(f"  {vid} [{videos[vid]['market']}] {videos[vid]['title'][:60]!r}: "
                      f"{len(comments[vid])} comments, {new} new")
    except QuotaExceeded as e:
        print(f"stopped: {e}. Saving what was collected.")

    # Store only videos whose comments were read (skips disabled comments, quota stops).
    videos = {vid: v for vid, v in videos.items() if vid in comments}
    for name, rows in build_tables(config, videos, comments).items():
        print(f"{name}: {warehouse.upsert(name, rows)} rows")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("scrape", help="search videos and collect their comments")
    p.add_argument("config")
    p.add_argument("--markets", nargs="+", help="only these markets from the config, e.g. de gb")
    p.add_argument("--dry-run", action="store_true", help="print the plan and quota estimate, call nothing")
    p.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    scrape(args.config, args.markets, args.dry_run, args.workers)


if __name__ == "__main__":
    main()
