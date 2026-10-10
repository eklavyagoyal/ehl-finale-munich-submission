# Scrapers

Collect customer voice into a small star schema of Parquet tables:

- **App reviews** from the Apple App Store and Google Play (`app_reviews.py`)
- **YouTube comments** under vehicle review videos (`youtube_comments.py`, [spec](../docs/specs/youtube-scraper.md))

Each target is a YAML file in [`configs/`](configs/). [`configs/my_bmw.yaml`](configs/my_bmw.yaml) covers the My BMW app in 15 markets; [`configs/bmw_5_series_youtube.yaml`](configs/bmw_5_series_youtube.yaml) covers 5 Series (G60) review videos in DE, GB, US, FR and IT.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# App reviews. Incremental: reruns only fetch new reviews; ~70 s for a full My BMW run
.venv/bin/python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml
.venv/bin/python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml --stores app_store --markets cn

# YouTube comments. Needs YOUTUBE_API_KEY in the environment or .env (spec, step 1)
.venv/bin/python -m scrapers.youtube_comments scrape scrapers/configs/bmw_5_series_youtube.yaml --dry-run
.venv/bin/python -m scrapers.youtube_comments scrape scrapers/configs/bmw_5_series_youtube.yaml --markets de

# Export to the shared research format (docs/research-data-contract.md on the research-handoff branch)
.venv/bin/python -m scrapers.export_research --collector <your-name>
.venv/bin/python -m scrapers.export_research --collector <your-name> --channels app_store youtube --markets de

# Offline tests
.venv/bin/python -m unittest discover tests
```

The export writes one batch per app storefront and one per YouTube search market (`source.json`, `records.jsonl`, `notes.md`) to the git-ignored `outputs/research/submissions/social/`. Export permissions are left unresolved (`null`), so batches stay out of Git until the team decides. Once `scripts/validate_research.py` is merged, the export runs it automatically.

New target: find its app ids with `python -m scrapers.app_reviews discover "<app name>" --countries de us cn`, copy `my_bmw.yaml`, and edit the app ids and markets.

## Output: `outputs/warehouse/*.parquet` (git-ignored)

| Table | Key | Columns |
| --- | --- | --- |
| `fact_review` | `review_id` | `date_id`, `app_id`, `app_version_id`, `os_id`, `market_id`, `review_id`, `content_date`, `content_datetime`, `content`, `rating`, `source` |
| `dim_date` | `date_id` (yyyymmdd) | `date`, `year`, `quarter`, `month`, `day`, `iso_week`, `day_of_week` |
| `dim_app` | `app_id` | `store`, `store_app_id`, `app_name`, `bundle_id`, `developer` |
| `dim_app_version` | `app_version_id` | `app_id`, `app_version` |
| `dim_os` | `os_id` | `os_name` (ios / android) |
| `dim_market` | `market_id` | `market_code`, `region` (EU / CN / US / RoW, as in BMW's sales data) |
| `fact_video_comment` | `comment_id` | `date_id`, `video_id`, `market_id`, `vehicle_model_id`, `comment_id`, `parent_comment_id`, `content_date`, `content_datetime`, `content`, `like_count`, `reply_count`, `source` |
| `dim_video` | `video_id` | `youtube_video_id`, `title`, `channel_title`, `published_date`, `view_count`, `comment_count`, `search_query`, `search_language` |
| `dim_vehicle_model` | `vehicle_model_id` | `brand`, `vehicle_code` (e.g. G60), `series` |

`dim_date` and `dim_market` are shared by both fact tables.

- **Date window:** `date_from` in each config (`scrape.date_from` for apps, `limits.date_from` for YouTube; both 2024-01-01 today) stops collection at that date, and each run removes stored rows of that config that are older. The export uses it as `sampling.date_start`.
- Surrogate keys are deterministic 63-bit hashes of the natural key, so reruns produce the same ids. `app_version_id` is `-1` when the store gives no version.
- `review_id` is prefixed with the store (`app_store:…`, `google_play:…`).

## Known limits

- **App Store:** the public feed gives at most ~500 recent reviews per country, so rerun regularly to build history. It occasionally returns an empty page mid-way; the scraper retries and skips single gaps, so some markets end at 450.
- **Google Play** filters reviews mainly by language. A market's language setting decides which reviews you get.
- Apple returns an empty feed to browser-like user agents, so the scraper sends its own.
- **YouTube:** a comment's market is the market whose search found the video, not the commenter's location. English markets (GB, US) overlap. A full 5 Series run uses at most ~2,000 of the 10,000 daily quota units. More in the [spec](../docs/specs/youtube-scraper.md#6-known-limits-and-assumptions).
