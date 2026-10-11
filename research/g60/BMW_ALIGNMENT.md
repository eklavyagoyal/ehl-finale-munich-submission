# BMW challenge alignment and completion checks

Reviewed 2026-10-11 against the original two-page [BMW briefing](../../docs/challenge/sources/BMW_Hackathon_Briefing_Short.pdf), the consolidated [mission and process](../../docs/challenge/brief.md), the original process slide, and the [BMW PM interview notes](../../docs/bmw-pm-interview/bmw-product-manager-groundwork.md). Paths beginning with `../../docs` in this document are resolved from `research/g60/`.

The original briefing was visually checked because its PDF is image-based. The detailed mission is the team's preserved BMW text; interpretations of the process slide and rough interview notes are explicitly distinguished in the source documentation.

**Goal:** a PM can turn diverse evidence into a small set of actionable customer-facing requirements for the G60 successor, understand their priority and uncertainty, change or challenge them, and make a traceable decision. The 3-5 year horizon must shape the proposals rather than merely appear in metadata.

The engineering prototype and automated provisional G60 US slice are complete. It is **not yet a human-reviewed submission**. Passing engineering tests does not establish that the real evidence, resulting requirements or PM experience satisfy BMW's expectations. BMW chooses the final outcome; we can check every stated deliverable and demonstrate it, not guarantee acceptance.

## Product architecture: updated user direction

Parallax is the main product application on `main`; the G60 workbench is a companion research and evaluation layer. This matrix assesses the companion implementation, not the entire deployed application's maturity. Within the companion workspace, our pipeline owns intake, evidence identity, review, grouping, cards, drafts, scores, permissions, budgets, versions and its local audit. Parallax separately owns its application state and PM decision history.

The companion's existing stateless advisory adapter sends frozen, role-permitted views and stores validated hypothetical critiques without changing its local evidence, scores or decisions. The next combined-product seam is an explicit handoff of reviewed evidence cards, provenance and evaluation metadata into Parallax. The shared batch contract is supported today; rich-card synchronization and a unified cross-system audit remain future work.

See [the integration assessment](PARALLAX_INTEGRATION_STATUS.md) for the tested branches and smallest stateless reuse seam.

## BMW deliverable matrix

Status means what exists now, not what is planned. The source references below point to sections of [the consolidated brief](../../docs/challenge/brief.md).

| BMW requirement | Source | Current state | Completion check |
| --- | --- | --- | --- |
| A working AI-powered product-requirements prototype | 6.1 and 6.2.1 | Core workflow implemented; the final 2026-10-11 regression run passed 308 tests with unchanged code hashes. The real provisional slice processed 3,659 records into 5,105 claims, eight drafts, 64 advisory assessments and all five required export types. Structural integrity and the 3,520-event audit pass. No human-reviewed slice or decision exists yet. | Run real G60 US inputs through extraction, cards, requirements, review and a human decision. |
| At least one derivative in one market | 5 | G60 US is the chosen slice and is permitted by the brief. | Demonstrate a real G60 US requirement with correct scope and no cross-market substitution. |
| Heterogeneous BMW data and relevant external evidence | 1, 3.1, 3.2.1 and 7 | Intake and a frozen snapshot exist; the provisional core input covers only the feedback sources, so study, equipment, sales and comparator material stays pending context, now listed by the read-only context inventory. No study join, sales denominator or competitor gap is established. | A PM can inspect the current product baseline, feedback, mapped study, sales exposure and relevant comparison/trend context, including missing or mismatched scope. Each used fact is source-linked. |
| Recurring complaints, unmet needs, advantages and trends linked to sources | 3.2.2 | Atomic claims with extraction annotations (stance, condition) and bounded chunked grouping implemented; the provisional core is extracted with explicit per-record outcomes. Review, adoption and claim-level acceptance remain human work. | Show supporting and contrary evidence, coverage and distinct-review counts; distinguish a complaint, a strength to preserve, a competitive opportunity and a future hypothesis. |
| Clear, actionable, customer-facing successor requirements | 3.1, 3.2.3 and 4 | Draft schema, customer-facing gate and future-assumption fields exist. Typed proposed targets are supported; observed numerical facts retain strict source checks. Real provisional drafting and its bounded validation repair have been exercised. | Customer problem, proposed behavior and a meaningful acceptance/validation criterion are clear; no component specification, regulatory requirement or invented business calculation. |
| Representative sample with all eight required fields | 6.2.2 | The shortlist export carries all eight fields with the current revision, score bounds, unknowns and a full source->record->claim->card->requirement chain. Requirements for the real slice are machine-proposed only; no PM decision exists. | Produce 5-10 real proposed requirements with ID, description, linked findings/sources, priority or score bounds, rationale, evidence level, future assumptions/uncertainties and status. Export the current score/revision consistently. |
| Explainable prioritisation | 3.2.4 and 6.2.2 | Criteria, unknown-preserving bounds, gates and sensitivity implemented. Real inputs and comparative prioritisation not evaluated. | Explain why one item is prioritized, investigated or deferred; show evidence basis, unknowns, conflicting signals and sensitivity. Jury opinion never becomes customer demand. |
| PM approves, rejects, edits or challenges with evidence and rationale | 3.2.5 and 6.1 | Revision-bound actions implemented; the browser form covers problem, response, rationale statements, assumptions, uncertainties, criteria and typed proposed targets with before/after preview, and every content change resets approval and scoring. No PM action has been taken on real data. | PM can revise problem/response, assumptions, uncertainty and targets; a challenge records a question/task and can trigger a frozen follow-up critique. Content changes invalidate approval and scores. |
| Chronological audit of actions, changes and access | 3.2.6 and 6.2.4 | Hash-chained events, requirement/evidence access events (actor, time, reason, frozen refs, content hash) and before/after change detail are implemented; a failed inspection is surfaced in the UI instead of being dropped. | Record actual content/evidence/score/status/priority changes and evidence/requirement access, with actor, time, reason and inspected revision. Display change details and preserve prior versions. |
| Explicit autonomous AI versus mandatory human review | 6.2.3 and 9 | Roles/gates and operator runbook exist; the full workflow needs a visible product explanation. | Demonstrate AI extraction/drafting/critique, and actual human evidence review, target setting, prioritisation review and decisions. No model-produced human approval. |
| Define measurable targets and acceptance criteria | Process slide, 9, specification/quantification | Typed criteria with `proposed_target` and a structured target {metric,value,unit,method,rationale,basis,uncertainty} are implemented and validated; an ungrounded number is repaired into a labelled proposal rather than rejected. Observed numeric facts keep the strict cited-source rule. | A PM can propose a customer target with metric, unit, measurement/test method, rationale, basis and uncertainty, clearly labelled as a proposal rather than an observed fact. |
| Adaptable beyond one model/market | 5 | A validated target configuration (`g60_scope`) exposes supported model/market values, scope hashing and per-record classification, and execution uses the validated G60 US target. The `scope` CLI is a validated preview/classification seam; production execution remains G60 US only, with no cross-market pooling. | Define a validated target configuration and explain extension to another supported slice; retain isolation and explicit unknowns. Implementing all other markets is not required for this demo. |

The brief allows unequal maturity across capabilities. That supports a focused G60 US prototype, but does not make the eight fields, PM control, evidence traceability or demonstrable audit optional.

## Corrections justified by BMW's brief

1. **Separate observed numerical facts from proposed targets.** Keep strict original-source validation for facts. Add a typed proposed-target path that records metric/value/unit, validation method, rationale, basis and uncertainty. A human PM can set a future target not present in old feedback. Such a target is an explicit product decision or hypothesis, never presented as a customer observation. This follows the process slide's AI-plus-human specification stage and the briefing's distinction between evidence and future assumptions.

2. **Use reviewed context during drafting.** The implemented draft payload includes typed, resolvable study, equipment/baseline and comparator handles with provenance. A clearly marked hypothesis-led opportunity can use sourced context while keeping customer-demand evidence low or unknown. Human mapping and context review still determine which facts are usable.

3. **Finish the PM review experience.** Expose the full editable customer-facing content, future assumptions, uncertainty and criteria in the browser. Render priority rationale and score inputs understandably rather than requiring JSON. Preserve the original evidence-only draft and show what a proposed edit would change before saving.

4. **Complete access and change auditing.** Record meaningful requirement/evidence reads in the core log, including actor and frozen references, without putting raw payloads or credentials in audit metadata. Health probes and background status polling should not create misleading evidence-view events. Show before/after content, score and status changes. Ensure access logging does not make a PM's own displayed state immediately stale.

5. **Surface the situation baseline and future horizon.** Show current-equipment scope, relevant BMW portfolio/class context, mapped study findings, competitor comparisons and sales exposure as context. Combined G60/G68 sales remain explicitly combined; Germany-only equipment does not establish a US baseline. Highlight which assumptions concern the successor in 3-5 years and what would confirm or refute them. Unknown baseline information becomes a validation task.

6. **Finish the real prototype evidence.** The prepared pilot and mock demo are engineering preparation. Human labels, a real measured extraction, reviewed cards and actual PM actions are still needed before claiming a representative BMW solution.

These are functional alignment improvements. They do not reopen historical Git/data cleanup, expand to every vehicle/market, require embeddings, or make simulated customers into measured market research.

## Implementation status (present tense)

The engineering work listed here is implemented and covered by the test suite. Where a step depends on
human review or real counted results, that dependency is stated and remains open - the existing
revision, citation, permission and quality gates are unchanged throughout.

1. **Core audit, PM editing and proposed-target gaps - implemented.** Requirement/evidence access events
   (actor, time, reason, frozen refs, content hash), before/after change detail, the full PM form
   (problem, response, rationale, assumptions, uncertainties, criteria, typed `proposed_target`), the
   readable score form with required human basis, and the pre-save preview are all in
   `scripts/g60_store.py`, `scripts/g60_app.py` and `scripts/g60_app.html`. Approval and scoring reset on
   every content change; stale revisions are refused.
2. **Reviewed context handles, baseline/horizon panel and the assumption-led path - implemented.** The
   drafter receives typed, resolvable study/comparator/baseline handles with provenance, the app shows
   the baseline/horizon panel with explicit unknowns, and a labelled hypothesis-led opportunity is
   allowed without a customer complaint (`scripts/g60_workflow.py`).
3. **Stateless Parallax advisory adapter - implemented.** `scripts/g60_parallax.py` runs four company
   roles and four scenario personas through our own model client and audit log, freezes request/revision/
   card hashes, labels results hypothetical and leaves evidence, counts, scores, gates and decision status
   untouched. Persona *grounding* (real attributes with citations) remains human work; the provisional
   personas are scenario assumptions.
4. **Human labels and the real pilot - engineering ready, human work pending.** Pilot selection,
   annotation export/import, bounded extraction with per-record outcomes, exact-input cache/resume and
   evaluation against gold labels all exist and the real frozen G60 US core runs in the machine-attested
   provisional lane. Actual human labels, adjudication, a measured extraction evaluation and the quality
   gate (`extraction.go`) do not exist yet.
5. **Real shortlist and human decision loop - engineering ready, human actions pending.** The shortlist
   export carries the eight fields with the trace chain, score bounds and unknowns; a real shortlist,
   evidence/contrary inspection and any PM approve/reject/defer/challenge/validation-task remain human
   actions on the real data.
6. **Baseline versus human-adopted improvements - export ready, evaluation pending.** The blinded
   baseline-versus-refined A/B packet and its separate key are exported for actual raters; no human
   refinement or rating exists yet, so the packet ships with an honest empty result.

Machine-verified core counts: 3,659 feedback records (3,610 BMW and 49 NHTSA), 5,105 extracted claims,
1,777 retained conditions and 8,697 exact quote spans. Every selected record has a successful structural
outcome: 3,194 with claims and 465 without claims. These checks establish machine integrity, not semantic
extraction quality. The completed slice also has eight code-built cards, eight proposed drafts, 64 hypothetical jury assessments and all required exports; human review remains pending.

## Final demonstration acceptance checklist

- [ ] A real G60 US need is traceable through source -> original review -> atomic claim -> reviewed group -> code-built card -> frozen requirement.
- [ ] More than one relevant input type contributes, with product/study/comparator/sales scope and limitations visible.
- [ ] The sample requirement list has all eight BMW fields and a consistent current revision/score projection.
- [ ] At least one example preserves a customer strength, and one shows contradictory or insufficient evidence.
- [ ] At least one successor-facing assumption and one proposed measurable customer target are labelled and reviewable.
- [ ] The PM can edit, challenge, approve/reject/defer, create a validation task and see exact reasons and changes.
- [ ] A stale decision or tool result cannot affect a newer revision; editing content resets prior approval and scoring.
- [ ] Actual requirement/evidence access and decisions appear in the chronological audit.
- [ ] Calling Parallax leaves original evidence, counts, scores and decision status unchanged; adopted changes originate from a real human action.
- [ ] Extraction quality, failures, unprocessed data and jury limitations are reported honestly.
- [ ] The architecture shows how another model/market would be added without pooling incompatible evidence.

The engineering paths for every check exist and are tested; the boxes stay unchecked because the real
human labels, human review and PM decisions behind them do not exist yet. The provisional machine counts are now verified below. When those are
demonstrated we can claim coverage of the stated BMW deliverables for the chosen prototype slice; BMW's
assessment and real customer/engineering validation remain distinct from that claim.

## Capability status (supervisor update)

The engineering capabilities below exist and are covered by the test suite. The completed real-run
counts are recorded below; human validation remains pending.

- Provisional lane (`scripts/g60_provisional.py`): verified machine integrity, resumable core, bounded
  chunked grouping with per-chunk durable checkpoints and bounded repair, per-card requirements
  checkpoints that retry scoring without re-drafting, advisory jury delivery and registered exports
  (shortlist, subgroup-local rankings, blinded A/B packet, family/stance frequency and the snapshot
  context inventory).
- Grouping: feature families, then bounded model subgroups with content-bound chunk identity; a
  completed chunk is reused only while its recorded memberships remain proposed/active **and** its
  recorded method matches, every chunk outcome is checkpointed immediately (and a corrupt or tampered
  checkpoint is refused rather than trusted), and a rejected chunk is retried once with a fixed
  directive while transport/deadline failures are recorded once. Baseline partitioning is a labelled
  fallback that never runs over partial model state, and a fatal grouping failure stops the lane before
  any card is built. Grouping uses a bounded four-call window and durable validated-partition writes
  before group events, so interrupted commits resume without another model call. Subgroup-local ranks stay local
  and the complete family/stance roll-up is the honest frequency answer.
- Frequency: subgroup-local ranks are labelled as such; complete per-cohort, per-family/stance
  frequency (distinct parents, disjoint accepted/pending, extraction coverage) is exported separately.
- App: PM forms, readable scores, access audit, read-only context/frequency panels resolved from
  registered export events with hash and strict-JSON verification.

Honest provisional limitations (unchanged): no human source acceptance, claim adoption, annotation
labels, target setting, persona grounding, competitor-gap verification, study join, sales denominator
or PM approval exists; all machine output is E0 and unreviewed, and the invented demo is not
research. The completed real provisional slice has 283 grouping chunks, 2,968 proposed groups, 5,051 grouped claims and 54 explicitly unassigned claims. All eight requirements remain E0/proposed; the six priority criteria are unknown, with score bounds 0–100. The 200-record blind annotation packet is prepared; no labels or approvals were fabricated.

## Implementation status update (2026-10-11)

This section records what the engineering work actually changed after the review above. The
deliverable matrix stays the authority: engineering paths now exist, while every human gate is
still pending and no BMW acceptance is claimed.

Implemented and covered by tests:

1. Proposed targets are a first-class typed path: `acceptance_criteria` entries keep
   `{criterion,type,citations}` and gain `type: proposed_target` with
   `target {metric,value,unit,method,rationale,basis,uncertainty}`. A proposal is never presented as
   an observed fact, and basis references are validated.
2. The drafter receives typed, resolvable reviewed-context handles (study/comparator/baseline) with
   exact provenance, so a context-led E0 hypothesis can exist without a customer complaint and
   without inventing claim citations.
3. The PM review experience covers problem, response, rationale, assumptions, uncertainties,
   criteria and targets, with a readable score form, explicit unknowns, before/after preview and a
   revision-bound save that resets approval and scoring.
4. Meaningful requirement/evidence access and every content/score/status change are recorded with
   actor, time, reason and frozen references; health polling logs nothing and a view returns the
   head it just advanced.
5. Baseline/horizon context is surfaced for review: current-equipment scope, mapped study findings,
   competitor context and combined G60/G68 exposure stay explicitly labelled, and Germany-only
   equipment never establishes a US baseline.
6. The stateless advisory adapter exists as a tool over our pipeline (see
   [the tool contract](PARALLAX_INTEGRATION_STATUS.md)); it cannot change evidence, counts, scores,
   gates or decisions.
7. Shortlist, cohort-frequency and blinded A/B exports exist with the eight required fields, the
   current revision/score/status, score bounds and unknowns, and a full
   source -> record -> claim -> card -> requirement chain. Frequency stays "collected feedback
   parents with an extracted mention", never people or prevalence, and cohorts are never pooled.
8. A separate provisional lane can run the real frozen G60 US core before review. It requires a
   machine attestation of the actual user processing instruction (external sharing only), keeps
   explicit revocations, marks every output unreviewed/E0 and never writes a human event.

Still pending (unchanged and not claimed):

- Actual human source reviews, claim adoption, annotation labels, target setting, prioritisation
  review and the PM decision.
- A real measured extraction quality result against human labels, and the blinded A/B evaluation by
  actual raters; the packet ships with no invented ratings.
- BMW's own assessment of the prototype; engineering tests and a synthetic demo are not acceptance.
