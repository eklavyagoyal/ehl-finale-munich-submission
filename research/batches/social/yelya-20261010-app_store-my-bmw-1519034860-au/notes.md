# My BMW (App Store 1519034860) customer reviews, AU storefront

- **source_id:** `yelya-20261010-app_store-my-bmw-1519034860-au`
- **dataset_key:** `app_store:1519034860:AU`
- **channel:** app_store · **collector:** yelya · **collected:** 2026-10-10T15:15:03Z
- **records:** 418 (one per original review/comment; no claims extracted)
- **content dates:** 2021-03-30 to 2026-09-24
- **review status:** pending · **export permissions:** unresolved (git and external LLM)

## Sampling

App Store reviews, newest first, all available up to the scraper limit; scrapers/app_reviews.py

Query: none (store feed)

## Limitations

- Apple's public review feed exposes only the ~500 most recent reviews per storefront; it also skips the occasional empty page, so a few reviews can be missing.
- Market is the storefront country, not the reviewer's residence.
- Reviews concern the companion app, not a specific vehicle model; subject_ids stay empty until the catalog has an app entity.

## Mapping notes

- `record_id` = `dedup_key` + first 12 hex characters of SHA-256(text): stable on identical reruns.
- Dates keep the source timezone offset; markets are ISO country codes.
- No catalog additions were made by this export.
