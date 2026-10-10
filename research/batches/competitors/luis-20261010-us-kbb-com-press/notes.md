# luis-20261010-us-kbb-com-press

US · kbb.com · press feedback for BMW 5 Series competitors

| | |
| --- | --- |
| Channel / dataset | `editorial_review` / `web:kbb.com:press` |
| Records | 8 (feedback: 8) |
| Claims | 81 (praise: 53, other: 24, new_request: 3, defect: 1) |
| Subjects | `competitor:mercedes-benz:e-class:w214` (1), `competitor:mercedes-benz:eqe-sedan:v295` (1), `competitor:genesis:g80:rg3` (1), `competitor:lexus:es:xz10` (1), `competitor:lexus:es:gen8` (1), `competitor:tesla:model-s:2021-refresh` (1), `competitor:audi:a6-e-tron:ppe` (1), `competitor:audi:a6:c9` (1) |
| Collected | 2026-10-10T16:00:00Z by luis (run `luis-competitors-2026-10-10`) |

## Method

Targeted web research by AI agents (Claude Code, run luis-competitors-2026-10-10): WebFetch of pages found via WebSearch or known review/spec URLs; one record per review/article/spec statement.

## Limitations

- text_original holds the collecting agent's English paraphrase, not verbatim source text. The agent read pages through WebFetch, which returns model-written summaries; original wording was not stored (copyright, tool limits).
- Claims quote that paraphrase; any 'Original excerpt' in text_original came out of the same summaries and is not guaranteed verbatim.
- Targeted, non-random selection: pages chosen via web search and known review URLs, capped by a fetch budget.
- collected_at is approximate: the end of the research run (2026-10-10 ~16:00 UTC); per-page fetch times were not recorded.
- markets: the reviewer's country where known, else the site's country domain for EU sources, else the market aggregate (EU/US/CN).

## Mapping notes

- Feedback: one record per review/article (`review_ref`), one claim per statement. Claim types: Likes → praise, Defect → defect, Wants → new_request, Difficult to Use → other (original type in `luis_extensions.json`).
- Claim `feature_key` is the slug of the best-matching BMW VFC level2 topic where the agent assigned one, else null; proposed keys are listed in `competitors/contract/catalog_additions.json`.
- Equipment: standard → present, optional → optional, not_available → absent, unknown → unknown.
- Theme, evidence tier, comparison verdict, model year, powertrain, original language: `luis_extensions.json`.
- Status: source and claims `pending`; `export_permissions.external_llm` null (team decision).
