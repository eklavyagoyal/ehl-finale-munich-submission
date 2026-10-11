# Does a new data source make the signals better?

Fixed on 2026-10-11, **before** any new data was collected. These are the only numbers that go on the slide,
whatever they show. If the new source makes no difference, the slide says so.

## Setup

1. Decide on the triage filter, then rebuild the signals once. That snapshot is the **baseline**
   (`GET /api/signals/snapshots`); its id goes into this file.
2. Keep everything else fixed: labeler prompt `labeler-v2-fewshot`, triage prompt `triage-v2`, policy version,
   catalog.
3. Add only the new source: scraper → research export → `push-research` → labeling and triage of the new records
   only → rebuild. That snapshot is **after**.

## Three metrics (per market US / EU, pooled for reference)

| # | Metric | How | Better means |
| --- | --- | --- | --- |
| 1 | **Agreement with BMW** (main number) | Spearman rank correlation between a source's feature ranking (share of its reviews mentioning the feature) and the ranking from BMW-labelled owner feedback, over features with at least 10 reviews on both sides. Computed for the new source alone, and for all online data before vs after. | The new source ranks problems like BMW's own owners do, and adding it does not pull the online ranking away from BMW's. |
| 2 | **Coverage** | Signals with at least 30 reviews (`frequent_min_reviews`) per market; signals backed by at least two channels. `GET /api/signals/compare` → `summary.before/after`. | More frequent signals, especially in EU and CN, and more signals confirmed by two channels. |
| 3 | **Stability** | Overlap of the top 10 signals before vs after (`summary.top_unchanged`, `entered_top`, `left_top`). | The core stays (high overlap). What enters the top is explained by the new source's reviews, not by noise. |

Metric 1 needs counts per source, which the themes do not store. It is computed from claims per stream when
the experiment runs (endpoint to be added together with the first new source), using the same counting rule as
the themes (one review counts once per feature).

## Not claimed

- Customer prevalence: these are collected reviews, not a sample of owners.
- Owner share: triage finds an owner only where the author says so (about 8 % of G60 online reviews).
