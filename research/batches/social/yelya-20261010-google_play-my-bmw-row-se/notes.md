# My BMW (Google Play de.bmw.connected.mobile20.row) customer reviews, SE storefront

- **source_id:** `yelya-20261010-google_play-my-bmw-row-se`
- **dataset_key:** `google_play:de.bmw.connected.mobile20.row:SE`
- **channel:** google_play · **collector:** yelya · **collected:** 2026-10-10T15:15:03Z
- **records:** 299 (one per original review/comment; no claims extracted)
- **content dates:** 2020-12-09 to 2026-09-25
- **review status:** pending · **export permissions:** unresolved (git and external LLM)

## Sampling

Google Play reviews, newest first, all available up to the scraper limit; scrapers/app_reviews.py

Query: none (store feed)

## Limitations

- Google Play filters reviews mainly by language; the storefront country is a weak market signal.
- Market is the storefront country, not the reviewer's residence.
- Reviews concern the companion app, not a specific vehicle model; subject_ids stay empty until the catalog has an app entity.

## Mapping notes

- `record_id` = `dedup_key` + first 12 hex characters of SHA-256(text): stable on identical reruns.
- Dates keep the source timezone offset; markets are ISO country codes.
- No catalog additions were made by this export.
