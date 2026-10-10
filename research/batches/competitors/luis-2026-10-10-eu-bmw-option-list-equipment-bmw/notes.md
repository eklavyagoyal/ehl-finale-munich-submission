# luis-2026-10-10-eu-bmw-option-list-equipment-bmw

EU · bmw-option-list · equipment/specification facts for BMW 5 Series (baseline)

| | |
| --- | --- |
| Channel / dataset | `bmw_option_list` / `bmw-option-list:G60:DE-2026-07` |
| Records | 21 (feature_availability: 21) |
| Claims | 0 |
| Subjects | `bmw:G60` (21) |
| Collected | 2026-10-10T16:00:00Z by luis (run `luis-competitors-2026-10-10`) |

## Method

Read from the local Markdown extraction of BMW's G60 DE price list by a research agent.

## Limitations

- text_original is the agent's summary of the option-list entry, not the catalog wording.

## Mapping notes

- Feedback: one record per review/article (`review_ref`), one claim per statement. Claim types: Likes → praise, Defect → defect, Wants → new_request, Difficult to Use → other (original type in `luis_extensions.json`).
- Claim `feature_key` is the slug of the best-matching BMW VFC level2 topic where the agent assigned one, else null; proposed keys are listed in `competitors/contract/catalog_additions.json`.
- Equipment: standard → present, optional → optional, not_available → absent, unknown → unknown.
- Theme, evidence tier, comparison verdict, model year, powertrain, original language: `luis_extensions.json`.
- Status: source and claims `pending`; `export_permissions.external_llm` null (team decision).
