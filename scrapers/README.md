# App review scrapers

Collects app reviews from the Apple App Store and Google Play into a small star schema: one review fact table and five dimensions.

Each target is a YAML file in [`configs/`](configs/). [`configs/my_bmw.yaml`](configs/my_bmw.yaml) covers the My BMW app in 15 markets.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Incremental: reruns only fetch new reviews; ~70 s for a full My BMW run
.venv/bin/python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml
.venv/bin/python -m scrapers.app_reviews scrape scrapers/configs/my_bmw.yaml --stores app_store --markets cn
```

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

- Surrogate keys are deterministic 63-bit hashes of the natural key, so reruns produce the same ids. `app_version_id` is `-1` when the store gives no version.
- `review_id` is prefixed with the store (`app_store:…`, `google_play:…`).

## Known limits

- **App Store:** the public feed gives at most ~500 recent reviews per country, so rerun regularly to build history. It occasionally returns an empty page mid-way; the scraper retries and skips single gaps, so some markets end at 450.
- **Google Play** filters reviews mainly by language. A market's language setting decides which reviews you get.
- Apple returns an empty feed to browser-like user agents, so the scraper sends its own.
