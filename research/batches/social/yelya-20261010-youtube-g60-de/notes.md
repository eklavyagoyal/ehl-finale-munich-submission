# YouTube comments under BMW 5 Series (G60) review videos, DE search market

- **source_id:** `yelya-20261010-youtube-g60-de`
- **dataset_key:** `youtube:comments`
- **channel:** youtube · **collector:** yelya · **collected:** 2026-10-10T16:41:57Z
- **records:** 3464 (one per original review/comment; no claims extracted)
- **content dates:** 2024-01-01 to 2026-10-09
- **review status:** pending · **export permissions:** unresolved (git and external LLM)

## Sampling

YouTube Data API: search.list (relevance, 10 per query, region DE, language de), title filter for the vehicle, then commentThreads newest first, up to 3 pages of 100 threads per video plus the replies the API includes; scrapers/youtube_comments.py

Query: BMW 5er G60 Test | BMW i5 Test | BMW 5er Limousine Fahrbericht

## Limitations

- Market is the search market (region + relevance language), not the commenter's location.
- 26 videos selected by search relevance and a title pattern; not a random sample of owners.
- Up to 3 pages of comment threads per video; replies beyond the 5 the API returns per thread are missing.
- Videos whose language tags all differ from the market language were dropped.
- Reply/thread links, like counts and video titles are kept in the warehouse but have no field in schema v1 source_fields.
- subject_id bmw:G60 also covers Touring (G61), i5 and M5 videos.

## Mapping notes

- `record_id` = `dedup_key` + first 12 hex characters of SHA-256(text): stable on identical reruns.
- Dates keep the source timezone offset; markets are ISO country codes.
- No catalog additions were made by this export.
