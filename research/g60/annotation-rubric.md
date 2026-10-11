# Human annotation rubric (g60-annotation-1)

Use the blind exported CSV before viewing model output. Enter your own name when importing; no system or model can supply a human label. The original text, record ID, rubric version and split must stay unchanged. Duplicate a record row to label multiple atomic claims. To label no supported claim, write `none` in claim_type and leave all claim fields blank. Do not leave undecided records blank and import them.

A claim describes one specific feature or customer experience. Split distinct needs. Generic praise or complaint has no supported claim. Copy an exact quote from the customer's answer, preserving the original language and characters. Survey question wording is not customer evidence. Translation is interpretation and must not replace the original quote.

Choose a known feature key where clearly supported, otherwise leave it blank. Enter the reviewed family ID if available. Give a short neutral need label. Preserve stated conditions and negation. An existing function that fails or is hard to use is `defect` with `complains`; a wish for a new function is `new_request` with `wants`. “Do not remove” has stance `wants_kept`; “I do not need” has `does_not_want`. Permitted claim types and stances are documented in the extraction prompt.

Applicability requires evidence in the text or established context. The G60 collection label alone does not establish a respondent's car. Touring, M5 and X models are `other_bmw_model`; general My BMW app experiences are `brand_or_app_wide`; unknown context is `unresolved`.

Keep development (`dev`) labels separate from held-out `eval_gold`. The `eval_assisted` sheet is for later assisted review, and its blind export supplies no model labels. Do not tune prompts using held-out labels. Double-label at least 25 records with a second independent annotator. Match claims by record, reviewed family, type bucket and overlapping exact quote span. Report matched-claim F1 and type/stance agreement; resolve disagreements by a third annotator or a documented discussion. Import each annotator separately. A single annotator artifact is not an adjudicated gold set.

Unmatched model claims must be adjudicated as supported claims missed by gold or unsupported; a mismatch alone cannot establish hallucination. Report raw counts by cohort. This purposive pilot does not support population prevalence or confidence intervals.
