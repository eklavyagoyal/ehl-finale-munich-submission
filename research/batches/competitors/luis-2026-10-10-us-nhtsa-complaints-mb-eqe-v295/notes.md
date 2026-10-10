# luis-2026-10-10-us-nhtsa-complaints-mb-eqe-v295

US · NHTSA owner complaints · Mercedes-Benz EQE sedan (V295)

| | |
| --- | --- |
| Channel / dataset | `other` / `nhtsa:complaints` |
| Records | 60 (feedback: 60) |
| Claims | 0 |
| Subjects | `competitor:mercedes-benz:eqe-sedan:v295` (60) |
| Collected | 2026-10-10T16:15:05Z by luis (run `luis-competitors-2026-10-10`) |

## Method

NHTSA complaints API (complaintsByVehicle) for every NHTSA model name matching the vehicle, model years 2023-2027; all returned complaints, deduplicated by ODI number. Script: competitors/tools/nhtsa.py

## Limitations

- Complaints are self-reported and almost all describe defects; volume scales with fleet size and age.
- NHTSA model buckets are noisy (e.g. EQE sedan and SUV share buckets; complaints mentioning 'SUV' were dropped).
- Narratives are NHTSA's published text (public domain); 17-character VIN-like tokens were replaced.
- A complaint filed for several vehicles appears once per vehicle batch (dedup_key = ODI number + vehicle).

## Mapping notes

- Feedback: one record per review/article (`review_ref`), one claim per statement. Claim types: Likes → praise, Defect → defect, Wants → new_request, Difficult to Use → other (original type in `luis_extensions.json`).
- Claim `feature_key` is the slug of the best-matching BMW VFC level2 topic where the agent assigned one, else null; proposed keys are listed in `competitors/contract/catalog_additions.json`.
- Equipment: standard → present, optional → optional, not_available → absent, unknown → unknown.
- Theme, evidence tier, comparison verdict, model year, powertrain, original language: `luis_extensions.json`.
- Status: source and claims `pending`; `export_permissions.external_llm` null (team decision).
