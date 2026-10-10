# Orchestrator checklist

Keep F70, G60, and G70 in scope. Build one evidence packet with separate model/market views and an explicit unallocated group for combined, brand-wide, and unresolved data. Sparse coverage is a finding to report, not a reason to transfer evidence from another vehicle or market.

## While the collectors work

| Work | Concrete output | Ready when |
| --- | --- | --- |
| Intake | One representative batch per workstream, reviewed before larger collection | IDs, original text/units, scope, sampling and permissions are understood |
| Dimension resolution | Obtain dictionaries and provenance for the anonymous review tables | App, market, OS and version IDs are resolved from documented mappings, or remain explicitly unknown |
| Feature vocabulary | Review additions to `catalog/features.json`; merge true aliases | Claims about one feature share a key; distinct requests, defects and praise retain their types |
| Coverage | Track evidence for each target model and actual market/cohort | Missing strata, combined G60/G68 data and unresolved app applicability are visible |
| LLM evaluation | Prepare a small set of questions with known supporting record IDs and expected limitations | The set checks repeated reviews, contradictory evidence, units, combined models and unresolved scope |
| Decision criteria | Review `decision-model.json` and write evidence-based 0–5 scoring anchors | A PM can explain each score; unsupported effort or fit stays unknown |
| PM workflow | Prepare the requirement view and edit/approve/reject/challenge actions | Each real change records actor, time, changed value and reason |

The validator and offline exporter already provide the first integration path. Model/provider selection and the PM decision/audit interface are still to be implemented. Choose a model only after checking authorized data use, packet size with its tokenizer, output allowance and practical latency/cost. Do not upload content whose external-model permission is unresolved.

## When a pilot batch arrives

1. Put permitted content in its own `research/batches/<stream>/<batch>/` directory. If Git permission is unresolved, keep it under ignored `outputs/research/submissions/` and review it there.
2. Run the validator against the submissions root. Inspect the handoff notes and original locators. Resolve malformed rows, mismatched review joins, dimension dictionaries, duplicated observations, and incorrect units before accepting the source.
3. Review source provenance, sampling, scope and export permissions. Record the review in the source's provenance notes and set `review_status` explicitly. Review claims separately for supporting quotes, feature mapping and request/defect/praise classification; leave unresolved claims pending.
4. Review proposed competitor matches separately against model, year, market, trim and powertrain. Customer competitor mentions and an omitted specification do not prove a gap. The current exporter does not ingest comparison sidecars.
5. Revalidate after changes. Build a new context snapshot and inspect `coverage`, omitted claims, superseded records and per-cohort frequency. Missing accepted claims do not establish no demand.

Run from the repository root:

```sh
uv run --with 'jsonschema[format]==4.26.0' python scripts/validate_research.py research/batches
uv run --with 'jsonschema[format]==4.26.0' python scripts/build_research_context.py research/batches
```

Replace `research/batches` with the local submissions root when needed. Source originals stay unchanged; each output run is new and remains ignored by Git. The exporter never sends data to a model.

## First synthesis and demo

Use the packet's synthesis prompt with the full evidence packet if it fits the selected model's usable budget. Keep all three models available; compare frequency within comparable cohorts. If partitioning becomes necessary, state the partitions and preserve record IDs. Byte size is not a token count.

Before showing a shortlist, check that every cited ID exists, quoted text matches, model/market applicability is supported, and reported counts agree with the code. Run the prepared evidence questions and inspect contrary evidence. Test whether changing evidence order changes the important findings. Record the actual model/version/settings and retain its output with the context run; the offline packet's model field is initially null.

Each requirement needs the brief's eight fields: unique ID, actionable description, linked findings/sources, priority or score, rationale, evidence level, future assumptions/uncertainties, and decision status. Preserve the 3–5 year successor-vehicle horizon. Keep numeric priorities pending until scoring anchors and inputs are reviewed. Frequency can surface demand; severity, applicability, evidence quality and verified competitor differences also inform a decision.

The first demo is ready when the PM can inspect evidence and limitations, change a proposal, approve/reject/challenge it, and see a chronological audit of actual actions. Keep evidence acceptance separate from requirement approval. The brief's minimum is one derivative in one market; our data pipeline retains all three, and any unsupported model/market view must explain its evidence gap.
