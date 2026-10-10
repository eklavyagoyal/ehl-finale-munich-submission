# Spec: YouTube comment scraper (BMW 5 Series)

| | |
| --- | --- |
| Status | Implemented; first live run on 2026-10-10: 113 videos, 16,462 comments |
| Branch | `feat/scraper-my-bmw` |
| Code | `scrapers/youtube_comments.py`, config `scrapers/configs/bmw_5_series_youtube.yaml` |
| Related | [App review scraper](../../scrapers/README.md) · [Dataset gaps](../datasets/README.md) |

## 1. Why

The BMW feedback files have **no German and almost no European customer voice for the 5 Series** (G60: 3,610 of 4,000 feedbacks are US). Europe is still the largest 5 Series market (115k units in 2025). The My BMW app reviews we already scrape rarely name a car model.

YouTube comments under 5 Series review videos fill this gap:

- **About one specific car:** every comment sits under a video about the G60 / i5.
- **Per market:** searching in German, French or Italian finds videos for those markets.
- **Official API:** the YouTube Data API v3 is stable and needs only a free key.

## 2. Scope

**In scope**

- Top-level comments, plus the replies the API returns with them, under 5 Series (G60, including i5 and M5) review videos.
- Markets DE, GB, US, FR, IT (configurable).
- Same storage pattern as the app review scraper: Parquet tables in `outputs/warehouse/`, deterministic BIGINT keys, incremental reruns.

**Out of scope (for now)**

- China. YouTube is blocked there; China gets its own source later (Bilibili or collected by hand).
- Competitor videos (another team member owns competitor data).
- Classifying comments into topics or sentiment (analysis step, not scraping).
- Video transcripts.

## 3. Data source: YouTube Data API v3

| Call | Used for | Quota cost |
| --- | --- | ---: |
| `search.list` (`type=video`, `q`, `relevanceLanguage`, `regionCode`, `publishedAfter`) | Find review videos per market and query | 100 units per call |
| `videos.list` (`part=snippet,statistics`) | Title, channel, publish date, views, comment count | 1 unit per 50 videos |
| `commentThreads.list` (`part=snippet,replies`, `order=time`) | Comments, newest first, 100 per page | 1 unit per page |

The default quota is **10,000 units per day**. The default config uses 5 markets × 3 queries = 15 searches (1,500 units), plus up to 150 videos × 3 pages of comments (at most 450 units, usually far less). That's at most **~1,950 units per full run** (`--dry-run` prints the estimate), so several runs a day fit.

Comments have **no author location or language field**. A comment's market is the market whose search found the video (see §6).

## 4. Configuration

One YAML file per vehicle and source. Nothing BMW- or model-specific lives in code.

```yaml
name: bmw_5_series_youtube
vehicle:
  brand: BMW
  code: G60                      # e-code, as in the BMW datasets
  series: 5 Series
  # A video is kept only if its title matches; filters out other models and the old G30.
  title_pattern: '\b(5er|5[ -]?series|s[ée]rie 5|i5|m5|g60|5[2-5]0[ide])\b'
  # Earlier generations reviewed after the G60 premiere (e.g. "540i (G30) review").
  exclude_title_pattern: '\b(g30|g31|f10|f11|e60|e61|e39)\b'
  published_after: 2023-05-01    # G60 world premiere
markets:
  de: {language: de, queries: ["BMW 5er G60 Test", "BMW i5 Test", "BMW 5er Fahrbericht"]}
  gb: {language: en, queries: ["BMW 5 Series G60 review", "BMW i5 review UK"]}
  ...
limits:
  videos_per_query: 10
  comment_pages_per_video: 3     # 100 comments per page
  date_from: 2024-01-01          # drop older comments; stored older rows are removed on the next run
```

The API key comes from the environment variable `YOUTUBE_API_KEY` (or `.env`), never from the config.

## 5. Data model

The same conventions as the app tables: lowercase column names, BIGINT surrogate keys hashed from the natural key, `-1` for unknown, existing dimensions reused where they fit.

### `fact_video_comment`

| Column | Type | Notes |
| --- | --- | --- |
| `date_id` | BIGINT | → `dim_date` (shared) |
| `video_id` | BIGINT | → `dim_video` |
| `market_id` | BIGINT | → `dim_market` (shared) |
| `vehicle_model_id` | BIGINT | → `dim_vehicle_model` |
| `comment_id` | STRING | `youtube:<comment id>` |
| `parent_comment_id` | STRING | null for top-level comments |
| `content_date` | DATE | |
| `content_datetime` | STRING | ISO 8601 |
| `content` | STRING | plain text, HTML stripped |
| `like_count` | BIGINT | useful as an "agreement" weight |
| `reply_count` | BIGINT | 0 for replies |
| `source` | STRING | always `youtube` |

### `dim_video`

`video_id` (BIGINT), `youtube_video_id`, `title`, `channel_title`, `published_date`, `view_count`, `comment_count`, `search_query`, `search_language`, `video_language` (uploader's language tags, comma-separated)

### `dim_vehicle_model`

`vehicle_model_id` (BIGINT), `brand`, `vehicle_code` (`G60`), `series` (`5 Series`)

Author names and channel ids of commenters are **not stored**.

## 6. Known limits and assumptions

1. **The market is approximate.** It comes from the search language and region, not from the commenter. English markets (GB, US) overlap most. Statements per market should show comment counts and this caveat.
2. **If two markets find the same video**, the first market processed keeps it. The video's comments are stored once.
6. **Foreign-language videos:** search returns some videos in other languages (in the first run: Polish, Croatian, Arabic, and English videos in the Italian results). A video is dropped when it has language tags (`defaultAudioLanguage`, `defaultLanguage`) and none matches the market's language. Untagged videos are kept.
3. **Search results depend on relevance ranking** and change over time, so reruns can add new videos.
4. **Disabled comments:** `commentThreads.list` returns 403 `commentsDisabled`; the video is skipped.
5. **Replies:** only the up to 5 replies that `commentThreads.list` includes are stored. Getting all replies would need `comments.list` per thread (more quota, little extra value).

## 7. Implementation plan, step by step

| # | Step | Done when | Status |
| --- | --- | --- | --- |
| 1 | **API key setup:** create a key in Google Cloud Console (APIs & Services → enable "YouTube Data API v3" → Credentials → API key); put `YOUTUBE_API_KEY=...` in `.env` | `curl "https://www.googleapis.com/youtube/v3/search?part=id&q=bmw&key=$YOUTUBE_API_KEY"` returns JSON | ✅ |
| 2 | **Config:** `scrapers/configs/bmw_5_series_youtube.yaml` with vehicle, markets, queries, limits | File loads; queries reviewed by a German speaker | ✅ |
| 3 | **Schemas:** add `fact_video_comment`, `dim_video`, `dim_vehicle_model` to `scrapers/warehouse.py` | Tables write and re-read with the types in §5 | ✅ |
| 4 | **API client:** small `youtube_get()` with key from env, retries with backoff on 5xx/network errors, clear error on quota exceeded (403 `quotaExceeded`) | Unit test with mocked responses | ✅ |
| 5 | **Video discovery:** `search.list` per market and query → filter by `title_pattern` → `videos.list` for details | Run prints kept vs dropped videos per query | ✅ |
| 6 | **Comment collection:** `commentThreads.list` newest first, pages until the limit or until a page holds only known comments (incremental) | Second run fetches one page per video and adds 0 rows | ✅ |
| 7 | **Build rows and upsert:** facts + dims via `warehouse.upsert` | Row counts printed; keys stable across runs | ✅ |
| 8 | **CLI:** `python -m scrapers.youtube_comments scrape <config> [--markets de gb] [--dry-run]`; `--dry-run` prints planned calls and the quota estimate | `--dry-run` works without a key | ✅ |
| 9 | **Tests:** offline test with fake API responses covering pagination, title filter, disabled comments, dedupe | Passes in CI-less local run | ✅ 3 tests |
| 10 | **Live run and check:** run for all markets; read 20 random comments per market | Comments are about the G60 and in the expected language | ✅ see §9 |
| 11 | **Docs:** update `scrapers/README.md` (run command, tables, limits) | Teammate can run it from the README alone | ✅ |

## 8. Open questions

- Should the analysis step read app reviews and video comments as one combined table? If so, we add a view that unions both into the shared signal format (`source, vehicle, region, text, date, url`).
- Do we want transcripts of professional review videos (presenters' opinions, often comparing with E-Class / A6)? That overlaps with competitor work, so decide with the competitor owner.
- Which languages does the team read well enough to check samples in step 10?

## 9. First live run (2026-10-10)

| Market | Videos | Comments | Share in market language* |
| --- | ---: | ---: | ---: |
| DE | 23 | 4,528 | 81 % German |
| GB | 27 | 4,218 | 72 % English |
| FR | 22 | 2,494 | 78 % French |
| IT | 17 | 2,738 | 65 % Italian |
| US | 23 | 2,484 | 74 % English |
| **Total** | **113** | **16,462** | |

\* Rough stop-word check; the rest is mostly too short or emoji-only to classify. Comments date from 2023-05 to 2026-10.

Sample reading: comments are on topic (design, interior quality, rear space, range, diesel vs. EV, price) and include direct competitor comparisons (E-Class, Tesla, Polestar, Lucid). Expect noise as well: off-topic politics and jokes about the presenter. The analysis step needs to filter those.

The first run surfaced two problems, both fixed before the final run: two videos about the previous G30 (→ `exclude_title_pattern`) and foreign-language videos (→ language-tag filter, §6.6). Quota used for both runs together: about 4,000 of 10,000 units.
