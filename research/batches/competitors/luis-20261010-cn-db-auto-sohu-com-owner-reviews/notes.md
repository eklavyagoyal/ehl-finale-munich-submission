# luis-20261010-cn-db-auto-sohu-com-owner-reviews

CN · db.auto.sohu.com · owner reviews feedback for BMW 5 Series competitors

| | |
| --- | --- |
| Channel / dataset | `other` / `web:db.auto.sohu.com:owner_reviews` |
| Records | 160 (feedback: 160) |
| Claims | 604 (praise: 328, other: 194, new_request: 49, defect: 33) |
| Subjects | `competitor:mercedes-benz:e-class-l:v214` (31), `competitor:audi:a6l:c8l` (28), `competitor:xiaomi:su7:gen1` (20), `competitor:nio:et7:gen1` (20), `competitor:zeekr:007:gen1` (20), `competitor:luxeed:s7:gen1` (20), `competitor:stelato:s9:gen1` (20), `competitor:audi:a6l:c9l` (1) |
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
