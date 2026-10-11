# Shared research handoff

Read [the data contract](../docs/research-data-contract.md) before exporting data. It defines the counting rules, mappings from the supplied review tables, and LLM workflow.

Each teammate submits one directory per collection batch:

```text
research/batches/<bmw|competitors|social>/<collector>-<date>-<topic>/
  source.json       # origin, sampling, permissions, completeness
  records.jsonl     # one original observation per line
  claims.jsonl      # optional: one extracted feature claim per line
```

Copy a matching directory from `examples/` and replace every fixture ID/value, source location, collector, timestamps, sampling notes, artifact information, and provenance. Set `is_example` to `false`, set the actual `provenance.origin`, and keep source/claim `review_status` as `pending` until reviewed. Set permissions from the actual source authorization; use null when unresolved instead of copying the fixture's true values. Every example is invented, including quotes, numbers, dimensions, and vehicle specifications.

Give each agent its matching prompt:

| Workstream | Prompt | Starting example |
| --- | --- | --- |
| BMW workbook understanding | [agent-bmw.md](prompts/agent-bmw.md) | `examples/bmw-feedback/` and `examples/bmw-study/` |
| Competitor matching and research | [agent-competitors.md](prompts/agent-competitors.md) | `examples/competitor/` |
| Social and app reviews | [agent-social.md](prompts/agent-social.md) | `examples/social/` |

Analyze claims individually. Join `claim.record_id` to `record.record_id`, then `record.source_id` to `source.source_id`. One review can yield many claims and still counts once per feature. Reviewer identities are unnecessary.

Validate from the repository root:

```sh
uv run --with 'jsonschema[format]==4.26.0' python scripts/validate_research.py research/examples
uv run --with 'jsonschema[format]==4.26.0' python scripts/validate_research.py research/batches
uv run --with 'jsonschema[format]==4.26.0' python -m unittest discover -s tests -v
```

The second command becomes usable when the first real batch exists. It fails on missing or empty input rather than reporting a successful empty import. Validation checks structure and references; it does not verify source truth, infer permissions, or approve content for export.

`schema.json` is the contract for sources, records, and claims. `catalog/` holds shared entity IDs and feature vocabulary. `decision-model.json` contains proposed decision criteria. `prompts/synthesize.md` is the initial evidence-analysis prompt. Source originals stay in the existing ignored `data/` directory, and generated analysis stays in the existing ignored `outputs/` directory.

For the first handoff, submit one representative batch plus a short `notes.md` covering scope, counts, limitations, unresolved mappings, any catalog additions, and validation results. Include requests/defects and multiple claims from a review where the source supports them; do not fabricate examples to fill a checklist. Finish the pilot before broad collection. If permission to commit content is unresolved, prepare the export under ignored `outputs/research/submissions/` and report its location; do not publish it as a shared batch yet.

## Build the first context packet

The exporter runs locally and makes no LLM request:

```sh
# Invented fixtures only; useful for checking the integration.
uv run --with 'jsonschema[format]==4.26.0' python scripts/build_research_context.py research/examples --demo

# Real batches after evidence and permissions have been reviewed.
uv run --with 'jsonschema[format]==4.26.0' python scripts/build_research_context.py research/batches
```

Each successful run writes a new `outputs/research/<run-id>/context.json`. Outputs stay out of Git. `--output` can name a new file within `outputs/research/`; existing files are never overwritten. `--max-bytes` optionally rejects an oversized packet without truncating it. Check the selected model's actual token budget separately before using the packet.

Normal exports require accepted, non-example sources with `export_permissions.external_llm = true`. Only accepted claims on retained records are included. Review status and permissions are explicit human decisions; validation does not change them. Demo mode includes only synthetic examples, permits pending fixture status, and marks the packet as a demo. No eligible evidence is an error.

The current target is G60 only. The packet contains validated evidence, latest eligible snapshots per `(dataset_key, dedup_key)`, linked claims, catalogs, synthesis instructions, proposed decision criteria, coverage, exclusions, and exact input hashes. After selecting the latest snapshots, the exporter excludes records assigned only to other BMW vehicle models and their claims, reporting them in `coverage.excluded_records`. Competitor evidence, G60/G68 combined data, brand-wide feedback, and unresolved subjects remain context with their original scope; they do not establish G60 applicability. Existing catalog IDs and stored batches are preserved. `model` stays null until an actual inference run is recorded.

`feature_frequency.by_feature` gives overall collected-review counts; `by_cohort` preserves dataset, channel, subject, market, and sampling selection. Each review counts once per canonical feature. Request counts are separate from defects, praise, and other claim types. Cohort shares use all retained feedback in that cohort as the denominator; incomplete claim review/extraction and unmapped features can leave mentions uncounted. These are collected-review signals, not unique-person counts or customer prevalence. Do not use pooled totals as a model/market priority score.

Availability and study/sales records are included as evidence, but do not contribute customer-review counts. Competitor `comparisons.json` sidecars and narrative `notes.md` are not automatically ingested; review them separately. `comparison_context` remains explicitly pending, so the packet alone cannot establish a matched competitive gap.

Use the [integration checklist](INTEGRATION.md) while the collectors work and when their first batches arrive.
