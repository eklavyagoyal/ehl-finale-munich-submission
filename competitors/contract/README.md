# Competitor research in the team data contract

Our 5 Series competitor research exported into the **research data contract v1** from branch `feat/research-handoff` (`docs/research-data-contract.md`, `research/schema.json`, `research/prompts/agent-competitors.md`). That branch is **not merged** here. The batches sit at the paths the contract expects, so they land in the right place once both branches meet.

`competitors/findings.jsonl` stays the master. Everything below is generated from it by [`../tools/export_contract.py`](../tools/export_contract.py) and can be regenerated at any time.

## What was exported

| Output | Count | Where |
| --- | ---: | --- |
| Batches (`source.json` + `records.jsonl` + `claims.jsonl` + `notes.md`) | 76 | `research/batches/competitors/luis-20261010-<market>-<source>-<kind>/` |
| Records | 2,290 | 390 web feedback records (one per review/article), 614 feature-availability records, 1,286 NHTSA complaint records |
| Claims | 2,022 | one per feedback statement (`producer.method: llm`, `review_status: pending`) |
| Comparisons | 27 | [`comparisons.json`](comparisons.json): BMW target ↔ competitor, rationale, supporting record IDs |
| Catalog additions | 20 entities, 144 feature keys | [`catalog_additions.json`](catalog_additions.json): to append to `research/catalog/*` |
| Outlook | 21 | [`outlook.json`](outlook.json): announcements 2026–2030, not availability evidence |
| BMW verbatim mentions | 255 | [`bmw_mentions.json`](bmw_mentions.json): labels only, join key `bmw-feedback:G60:<ID>` |
| Exact excerpts | 36 | [`excerpts.json`](excerpts.json) (accepted) and [`excerpt_candidates.json`](excerpt_candidates.json) (all candidates, incl. rejected) |

Validation with the team validator (schema, catalogs, references, quote substrings):

```text
Validated 76 batches, 2290 records, 2022 claims (structure and references only).
```

## Mapping decisions

| Our data | Contract | Note |
| --- | --- | --- |
| Feedback statement (`kind: feedback`) | **record** per review (`review_ref`) + **claim** per statement | Likes → `praise`, Defect → `defect`, Wants → `new_request`, Difficult to Use → `other` |
| Equipment (`kind: equipment`) | `feature_availability` record | standard → `present`, optional → `optional`, not_available → `absent`, unknown → `unknown`; F01–F20 → feature keys such as `dc_fast_charging` |
| BMW baseline equipment | same, subject `bmw:G60` / `bmw:G68` | batches end in `-bmw`; DE option list → channel `bmw_option_list`, market `DE` |
| NHTSA complaints | `feedback` records with NHTSA's verbatim narrative | public domain; VIN-like tokens removed; raw JSON in `data/nhtsa/` (gitignored), SHA-256 in `source.json`. Replaces the agents' paraphrased NHTSA records |
| Competitor set (`kind: competitor`) | `comparisons.json` sidecar | `class_body` and `price_range` stay `null` where no source established them |
| Outlook, BMW mentions | sidecars only | announcements ≠ availability; BMW verbatims belong to the BMW stream |
| Theme, evidence tier, comparison verdict, model year, powertrain, original language, agent | `luis_extensions.json` per batch | keyed by contract `record_id` / `claim_id`; the team tools ignore it |

Batches are split as the contract asks: one per market × source site × kind (owner reviews, forum, survey, press, equipment), plus one NHTSA batch per vehicle.

**Feature keys for claims** are slugs of the BMW VFC level2 topic the research agent assigned as best match (e.g. `touch_screen_operation`), with aliases where a topic names an equipment feature (`Head-Up Display` → `head_up_display`). Claims without a VFC match keep `feature_key: null` and `feature_label: "theme: <id>"`. The feature `area` in the catalog additions is our theme id.

## What is and is not verbatim

- **Web feedback and equipment records:** `text_original` is the agent's English paraphrase (WebFetch returns model-written summaries; original wording was not stored). Each such record says so at the start of `text_original`, and every source manifest repeats it in `sampling.limitations`, with `provenance.verification: unverified`.
- **Claims** quote that paraphrase, so the quote check passes, but the quotes are not source wording. Short "original excerpts" inside feedback records came out of the same summaries.
- **36 equipment records carry an exact excerpt** taken from the raw page text (plain GET or `pdftotext`, whitespace normalised) by [`fetch_excerpts.py`](../tools/fetch_excerpts.py), matched by keyword and reviewed by hand against the record. Candidates were rejected when the excerpt did not establish the stated availability or when PDF column layout garbled the sentence.
- **NHTSA narratives** are verbatim.

## Status and permissions

- `review_status: pending` everywhere (sources and claims).
- `export_permissions.git: true`: stored on branch `luis-competitors` by the collector's decision.
- `export_permissions.external_llm: null`: for the team to decide.
- `sampling.complete: false` for web batches. Blocked and empty sources are listed per agent in `competitors/raw/*.log.md`.

## Rebuild and validate

```bash
.venv/bin/python competitors/tools/export_contract.py
.venv/bin/python competitors/tools/validate_contract.py
```

`validate_contract.py` copies schema, validator and catalogs from `origin/feat/research-handoff` into a temp folder, appends `catalog_additions.json`, and runs the team validator on `research/batches/competitors`. It needs `jsonschema[format]==4.26.0` in the venv. To refresh the exact excerpts: `fetch_excerpts.py`, review `excerpt_candidates.json`, then `fetch_excerpts.py --accept <record_id#n,...>`.
