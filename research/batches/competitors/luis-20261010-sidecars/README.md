# Competitor batches by luis (2026-10-10): handoff notes

BMW 5 Series (G60; China: G68) competitor research for EU, US and CN, exported into contract v1. The 76 batches `research/batches/competitors/luis-20261010-*` each carry `source.json`, `records.jsonl`, `claims.jsonl`, `notes.md` and `luis_extensions.json`. This folder holds the sidecars, which are not batches.

Master data, the analysis (theme scorecard, NHTSA comparison, findings summary) and the export tools live on branch **`luis-competitors`**: `competitors/` (master `findings.jsonl`, `tools/export_contract.py`) and `docs/competitors/README.md`.

## Counts

| | |
| --- | ---: |
| Batches | 76: 66 web (incl. BMW-baseline equipment batches ending in `-bmw`) and 10 NHTSA (one per vehicle) |
| Records | 2,290: 390 web feedback (one per review/article), 614 feature availability, 1,286 NHTSA complaints |
| Claims | 2,022 (praise 1,137 · other 668 · new_request 127 · defect 90), all `pending`, `producer.method: llm` |
| Comparisons | 27 in `comparisons.json` (target `bmw:G60`; China `bmw:G68`) |
| Catalog additions | 20 competitor entities, 144 feature keys (list: `catalog_additions_applied.json`) |

Validation: `python scripts/validate_research.py research/batches` passes with these batches included: "Validated 105 batches, 38021 records, 2022 claims" (2026-10-10, together with the social batches); the 27 unit tests pass.

## Files here

| File | Content |
| --- | --- |
| `comparisons.json` | Proposed BMW ↔ competitor matches: market, powertrains, rationale, supporting record IDs. `class_body` and `price_range` stay null where no source established them. Needs manual review |
| `outlook.json` | 21 announced/reported/rumoured changes 2026–2030. Not availability evidence, so not exported as records |
| `bmw_mentions.json` | 255 BMW G60 verbatims that name a competitor, as **labels only** (no BMW text). Join key `bmw_dedup_key = bmw-feedback:G60:<ID>` |
| `excerpts.json` | 36 exact excerpts (≤ 15 words) for core equipment features, already embedded in the matching records' `text_original` |
| `catalog_additions_applied.json` | Entity and feature IDs this handoff appended to `research/catalog/` |

## Read before accepting anything

- **Paraphrase, not source text.** For web batches, `text_original` is the research agent's English paraphrase: WebFetch returns model-written summaries, and original wording was not stored. Each record says so, and each manifest repeats it in `sampling.limitations`, with `verification: unverified`. Claims quote the paraphrase, so the quote check passes, but those quotes are **not** source wording.
- **Verbatim parts:** NHTSA narratives (public domain, VIN-like tokens removed, raw JSON with SHA-256 in `artifact`), and the 36 excerpts marked "Exact excerpt".
- **Feature keys:** 124 of the 144 keys are slugs of BMW VFC level2 topics that the agent picked as the best match (`area` = our theme id). Some are generic buckets (e.g. `body_equipment_overall_technology`). Align them with the BMW-workbook mapping before relying on per-feature counts.
- **G68:** China BMW-baseline records use subject `bmw:G68`. Under the G60-only packet rule they are excluded as "other BMW model"; the competitor records stay as context. Decide whether the G68 counts as the 5 Series in China.
- **Permissions:** `git: true` (collector's decision), `external_llm: null` (team decision), `review_status: pending` throughout.
- **Coverage gaps:** EU owner voice is thin (many review sites and forums block automated access). Volvo ES90, Tesla Model S (EU), Audi A6 C9 and the 8th-gen Lexus ES have press records only. Per-source details: `competitors/raw/*.log.md` on `luis-competitors`.
- **Not ingested automatically:** `notes.md` and the sidecars here, as the contract describes.
