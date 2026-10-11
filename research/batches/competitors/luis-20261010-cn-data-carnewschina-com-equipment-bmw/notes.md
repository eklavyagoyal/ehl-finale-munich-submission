# luis-20261010-cn-data-carnewschina-com-equipment-bmw

CN · data.carnewschina.com · equipment/specification facts for BMW 5 Series (baseline)

| | |
| --- | --- |
| Channel / dataset | `editorial_review` / `web:data.carnewschina.com:specifications` |
| Records | 14 (feature_availability: 14) |
| Claims | 0 |
| Subjects | `bmw:G68` (14) |
| Collected | 2026-10-10T16:00:00Z by luis (run `luis-competitors-2026-10-10`) |

## Method

Targeted web research by AI agents (Claude Code, run luis-competitors-2026-10-10): WebFetch of pages found via WebSearch or known review/spec URLs; one record per review/article/spec statement.

## Limitations

- text_original holds the collecting agent's English paraphrase, not verbatim source text. The agent read pages through WebFetch, which returns model-written summaries; original wording was not stored (copyright, tool limits).
- Claims quote that paraphrase; any 'Original excerpt' in text_original came out of the same summaries and is not guaranteed verbatim.
- Targeted, non-random selection: pages chosen via web search and known review URLs, capped by a fetch budget.
- collected_at is approximate: the end of the research run (2026-10-10 ~16:00 UTC); per-page fetch times were not recorded.
- markets: the reviewer's country where known, else the site's country domain for EU sources, else the market aggregate (EU/US/CN).
- Some records carry an exact excerpt (see text_original); it was taken from the raw page text by competitors/tools/fetch_excerpts.py and matched by keyword, then reviewed.

## Mapping notes

- Feedback: one record per review/article (`review_ref`), one claim per statement. Claim types: Likes → praise, Defect → defect, Wants → new_request, Difficult to Use → other (original type in `luis_extensions.json`).
- Claim `feature_key` is the slug of the best-matching BMW VFC level2 topic where the agent assigned one, else null; proposed keys are listed in `competitors/contract/catalog_additions.json`.
- Equipment: standard → present, optional → optional, not_available → absent, unknown → unknown.
- Theme, evidence tier, comparison verdict, model year, powertrain, original language: `luis_extensions.json`.
- Status: source and claims `pending`; `export_permissions.external_llm` null (team decision).
