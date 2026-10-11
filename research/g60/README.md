# G60 US pipeline

This runbook documents the companion implementation in the `feat/g60-pipeline` working checkout. Its `scripts/g60_*.py` files are not included in this documentation-only update to `main`; the main application is Parallax.

This is a working local implementation of the first pipeline slice: frozen intake → pilot and human labels → atomic claim extraction → reviewed needs → code-built evidence cards → proposed requirements → scoring and jury critiques → PM decisions. Generated data and the audit log stay under ignored `outputs/research/`. The original intake is never edited.

The orchestration workers used **gpt-6.1-sol**. The pipeline's runtime model is separately configurable; the default live runtime in this implementation is DeepSeek V4.1 Flash through the supplied loopback gateway, restricted to the allowlisted model IDs. The gateway pins the allowlist and a price ceiling and disables fallbacks, but it routes by price and preserves no upstream provider identifier, so reported provider metadata is descriptive rather than a pin. No hosted calls are needed for the invented demo.

Parallax is the main product cockpit on `main`. This G60 implementation is the companion evidence-preparation and evaluation workbench. Within its own workspace, the G60 pipeline owns evidence, requirements, scoring, local review decisions and audit; those artifacts are not automatically synchronized with Parallax's product state. The stateless advisory adapter is implemented (`scripts/g60_parallax.py`) and runs through our own model client and audit log. See [the assessed integration status](PARALLAX_INTEGRATION_STATUS.md) and [the BMW deliverable alignment checklist](BMW_ALIGNMENT.md) for verified capabilities and remaining work.

## Run the invented demo

From this checkout, define a shell shortcut:

```sh
alias g60="uv run --with 'jsonschema[format]==4.26.0' python scripts/g60_pipeline.py"
g60 --workspace outputs/research/g60-demo demo
uv run --with 'jsonschema[format]==4.26.0' python scripts/g60_app.py \
  --workspace outputs/research/g60-demo --actor 'Your own name' --port 8765
```

Open `http://127.0.0.1:8765`. Use a **new** demo workspace for each demo run; published artifacts are never overwritten. All fixture content is invented, all claims remain pending, evidence grades remain E0, and approvals remain absent. The demo copies fixtures into its ignored workspace and previews mock extraction without inventing a human adoption event. It exercises cards, drafts, both juries, score bounds, and audit replay.

## Run the real pilot

The current local intake is `outputs/research/intake/8eca8cdf69fb4351ae4d36a6b7fbfacb`. It holds the frozen input used by this implementation. Keep subsequent collection versions in separate intake directories.

The local workspace has already been initialized, and its 200-record pilot and three annotation CSVs are indexed by `outputs/research/g60/pilot-preparation.json`. Use that index to start reviewing and labelling; omit `init` for this existing workspace. No human review or external-model call was recorded during preparation.

```sh
g60 init outputs/research/intake/8eca8cdf69fb4351ae4d36a6b7fbfacb
g60 --actor 'Your own name' permission --allow \
  --destination external_model_api --reason 'Actual basis for the sharing decision'
g60 --actor 'Your own name' source-review SOURCE_ID accept \
  --reason 'Actual review of scope, provenance and sampling'
g60 snapshot
g60 pilot --size 200 --seed 42
g60 annotation-export PATH_TO_PILOT_JSON
```

Review each relevant source individually. A sharing event does not accept a source. Pilot selection reports realized source quotas, edge coverage, splits and shortfalls. The three exported CSVs separate dev, blind evaluation gold, and assisted review. Complete the labels yourself; empty annotation cells are not zero-claim labels. The [annotation rubric](annotation-rubric.md) describes the format.

Copy `.env.example` to the ignored `.env`, set the key, choose a model/provider, and deliberately set `G60_MODEL_CALLS=on`. The default $5 limit is a conservative reservation budget **per invocation**, including ambiguous timeouts; it can stop the pilot early. Configure a budget and reservation rates appropriate to your chosen provider before running. Read actual usage in the run manifest. Endpoint/provider changes need matching destination authorization.

```sh
g60 extract --pilot PATH_TO_PILOT_JSON
g60 --actor 'Annotator own name' --role annotator annotation-import COMPLETED_CSV \
  --reason 'Actual blind labels and rubric version'
g60 evaluate GOLD_JSON RUN_MANIFEST_JSON
g60 --actor 'Reviewer own name' adopt RUN_ID --reason 'Actual extraction review'
g60 snapshot
```

Real extraction requires an explicit pilot or a JSON array supplied with `--record-ids`. The exact pilot bytes must match its audit event. Every record gets an outcome: claims, zero supported claims, or a visible failure. The current implementation uses one record per request with bounded concurrency, at most three network attempts per record including repair, and a stage deadline. Completed artifacts contain hashes, actual model metadata, coverage and failed IDs. There is no silent input truncation.

Selections over 200 records additionally require a human `extraction.go` event bound to a stored, audited, non-synthetic `eval_gold` report. It checks the proposed precision/recall, failure, unsupported-claim, applicability and BMW-baseline thresholds; unmatched model claims require actual human adjudication. Smaller repeated selections do not establish quality or permission to scale. Use `event` to record the human decision:

```json
{
  "action": "extraction.go",
  "target": {"kind": "extraction", "id": "g60-us"},
  "payload": {
    "decision": "go",
    "evaluation_path": "evaluations/ACTUAL_REPORT.json",
    "evaluation_sha256": "ACTUAL_SHA256",
    "adjudicated_unsupported_count": 0
  }
}
```

The count above is a format example. Supply the **actual** adjudicated count and exact report hash. `g60 --actor 'Your own name' event FILE.json --reason 'Actual review'` records the decision; it never invents an approval.

## Review claims and needs

Use `event` for individual claim/record reviews; then rebuild the snapshot. For example:

```json
{
  "action": "claim.reviewed",
  "target": {"kind": "claim", "id": "ACTUAL_CLAIM_ID"},
  "payload": {"decision": "accept", "stance": "wants_changed", "applicability": "g60_direct"}
}
```

Use `record.reviewed` with `payload: {"complete": true}` only after reviewing all claims and omissions for that parent. A claim review alone never establishes complete extraction. Social vehicle tags alone cannot establish direct G60 applicability; that requires a human claim applicability decision. BMW core feedback and G60 NHTSA rows retain their explicitly scoped parent metadata.

```sh
g60 groups --method baseline
g60 groups --method llm
g60 --actor 'Reviewer own name' group-review GROUP_ID \
  --description 'Reviewed customer need with its conditions' --reason 'Actual membership review'
g60 cards
g60 draft CARD_ID
g60 score REQUIREMENT_ID
g60 juries REQUIREMENT_ID
```

Group proposals remain unreviewed. The baseline partitions by catalog family and stance. The model proposes subgroups in bounded windows of **25 claims per call** (validated default
`GROUP_CHUNK_SIZE=25`, configurable range 5-50 via `G60_GROUP_CHUNK_SIZE`), with singletons and
unassigned claims preserved; each chunk's outcome is checkpointed immediately and a rejected chunk
is repaired at most once by default (up to two validation repairs with `G60_GROUP_CHUNK_ATTEMPTS=3`),
while transport/deadline failures are recorded once after the client's bounded retries. Merge related
proposals across windows through reviewed membership edits. `--members` accepts an explicit JSON array. A claim belongs to at most one active reviewed group. Existing catalog keys are preserved; the tracked seed family file starts with one family per key, and alias merges need review.

Cards are built by code from the reviewed description. They retain exact source→record→claim links, supporting and contrary indexes, per-cohort counts and coverage, reviewed metric joins, comparator context, and sampling limits. Accepted and pending counts never mean unique people. Multiple claims from one parent count once per need. Pending claims do not increase verified demand, and duplicate candidates are not silently collapsed.

Human metric maps use `metric_map.reviewed`, an attribute, `record_ids`, a `family_id` or `need_group_id`, and `relation: direct|related`. Supply `ordered_record_ids` only for an explicitly reviewed seven-level ordering; code derives bottom-three/top-two from those actual rows. No automatic mapping, invented sample base, cross-market pooling, or customer-level reconstruction occurs.

Human `comparison.reviewed` events preserve accepted/partial status, US scope, reviewed dimensions and usable feature keys. Verified gaps require a current US match, recent manufacturer availability explicitly checked in `verbatim_record_ids`, and a G60 US baseline explicitly absent with a human `record.reviewed` payload `availability_verified: true`. Reported paraphrases stay unverified and receive no competitive-gap score. Germany-only options do not establish US availability.

## PM review and decisions

The app binds to loopback only. Its server-configured, self-asserted human actor is used for every mutation. A session token, exact Origin/Host checks, bounded JSON bodies, revision checks and a locked hash chain protect local actions. A save confirms only after the audit append is flushed. Conflicts require reloading.

The screen shows the requirement's eight fields, evidence, coverage, score bounds, gates, assumptions, internal critiques, hypothetical personas, tasks, suggestions and audit timeline. PM edits create a new revision and reset approval and scores. Citations and numeric assertions are revalidated. Previous revisions stay in the audit history.

Only a human PM can approve, challenge, investigate, reject, defer or reopen. Approval requires customer-facing scope, direct applicability and traceability gates to pass for the current revision. Juries cannot approve or supply effort/cost estimates. Suggestions become tasks or are applied through a reviewed edit; they never overwrite the baseline automatically.

Four provisional persona scenarios are generated by code with all attributes labelled `scenario_assumption`. Replace or import them through `persona.created` events before a grounded run, with per-attribute citations and provenance. Observed joint traits must co-occur in the same parent; weights and population shares are rejected. `run_juries(..., persona_ids=[...])` accepts the team's four validated personas. Personas see only the description and customer problem; design/engineering roles have separate views, and scores are hidden from the market/design roles. Jury assertions are typed as hypotheses or cited observations; flagged numeric or market assertions are hidden pending review.

## Deliberate first-implementation limits

- Demand stays unknown below 100 fully reviewed G60 US parents and adequate extraction coverage. Its automatic anchors are deliberately conservative (1–2); higher frequency ranks need a reviewed cohort comparison. Unknown criteria retain their original weights when computing bounds. Delivery/reuse stay null without a human basis.
- Weight perturbations and channel-removal bounds are implemented. Top-k robustness remains unknown until a fully comparable ranked shortlist exists.
- Cross-source duplicate disposition events are stored; automatic card-level duplicate collapse is deferred. Counts disclose this. There is no embedding-based clustering or vector database.
- Group/card/requirement versions and all decisions are reproducible through stored artifacts and the event log. Both juries, resumable exact-cache extraction and the blinded baseline-versus-refined A/B export are implemented; optional debate rounds and large-context comparison remain follow-up work.
- Human annotation imports support one labelled artifact at a time. Double-labelling agreement and adjudication remain a human-reviewed evaluation step.
- Source C/D template/severity regexes belong in ignored `config/templates.json`. Missing configuration is visible in extraction flags.
- NHTSA counts are reported complaints, not verified incident rates. Combined G60/G68 sales remain exposure context and never feed G60-only demand.

These limits prevent the first demo from implying evidence or measurements that have not been reviewed. The core flow works now; quality gates control the real rollout.

## Verification

```sh
g60 verify
uv run --with 'jsonschema[format]==4.26.0' python -m unittest discover -s tests -t . -v
```

Tests cover the original contract/exporter, event corruption/concurrency/revisions, source revocation, adopted output integrity, human annotations, model failures/spend limits, counts, citation validation, blinded views, hypothetical personas, PM actions, HTTP boundaries, and the complete invented demo. No test calls a hosted model.

## PM app response projection

The local PM app answers `/api/state` with a read-only projection instead of the whole folded state, so a
large run stays fast: every requirement, its referenced evidence-card snapshots (current and historical
references), scores, jury assessments, suggestions, tasks, personas, access list, changes, audit, score
policy and the read-only documents are kept; groups and unreferenced cards are dropped. Measured on the
real v3 workspace: 3.12 MB -> **0.32 MB** (309 cards -> 1 referenced card, 309 groups dropped). Mutation
and access handlers still load the authoritative full state, and the HTTP handler owns the `read_only`
flag, so freshness and authorization are unchanged.

## Provisional real-data lane (unreviewed, machine-attested)

The ordinary workflow keeps every human gate. The provisional lane is a separate,
clearly-labelled product path for running the real frozen core before anyone has
reviewed it. It never fabricates source acceptance, adoption, quality approval or a
PM decision.

```sh
alias g60="uv run --with 'jsonschema[format]==4.26.0' python scripts/g60_pipeline.py"
g60 --workspace outputs/research/g60-us-full init outputs/research/intake/INTake_HASH
g60 --workspace outputs/research/g60-us-full snapshot
# Machine attestation of the actual user instruction: external sharing authorisation only.
g60 --workspace outputs/research/g60-us-full attest \
  --instruction-reference 'user-instruction://...' --instruction-excerpt 'the actual instruction text' \
  --models deepseek/deepseek-v4.1-flash --destination external_model_api --reason 'why sharing is authorised'
# verify -> pilot -> core -> grouping -> requirements -> juries -> exports (resumable, one stage set at a time)
g60 --workspace outputs/research/g60-us-full provisional \
  --selection outputs/research/implementation-20261011/real-core-selection.json --stages verify pilot
g60 --workspace outputs/research/g60-us-full provisional \
  --selection outputs/research/implementation-20261011/real-core-selection.json --stages core
g60 --workspace outputs/research/g60-us-full provisional \
  --selection outputs/research/implementation-20261011/real-core-selection.json \
  --stages grouping requirements juries exports
# Read-only exports (each is hash-named, immutable and recorded as an export.created event)
g60 --workspace outputs/research/g60-us-full shortlist
g60 --workspace outputs/research/g60-us-full rankings
g60 --workspace outputs/research/g60-us-full jury-ab-export
```

A bounded preflight can exercise the real downstream path in its own workspace before the core
finishes; it validates the canonical pilot's hashes and passed machine verdict, adopts its pending
claims read-only and never writes a human event:

```sh
env G60_MODEL_CALLS=on G60_MODEL=deepseek/deepseek-v4.1-flash G60_MAX_CONCURRENCY=4 \
    G60_MAX_ATTEMPTS=2 G60_TIMEOUT_S=30 G60_ATTEMPT_DEADLINE_S=90 G60_MAX_TOKENS=4096 \
    G60_REASONING_EFFORT=none G60_MAX_COST_USD=5 \
    uv run --with 'jsonschema[format]==4.26.0' \
    python outputs/research/implementation-20261011/g60_preflight.py \
    --workspace outputs/research/g60-preflight \
    --pilot-manifest outputs/research/g60-us-full/runs/RUN_ID/run_manifest.json \
    --instruction-reference 'user-instruction://...' --instruction-excerpt '<the exact instruction text>' \
    --drafts 2
```

Grouping recovery semantics (bounded, tested, frozen for the current run):

- Chunk repair is bounded (default 2 attempts) and applies only to our own validation rejections
  (schema, exact-partition, stance). Transport and deadline failures are recorded once, after the
  client's own bounded retries, and are never repaired again.
- Every chunk outcome is checkpointed immediately as
  `runs/group-chunk-<chunk_key[:12]>-<digest(record)[:8]>.json`. Loading rejects corrupt, malformed or
  tampered records (a valid JSON file whose name no longer binds its own digest) instead of trusting
  them, and the legacy whole-run `groups-*.json` manifest remains a compatible fallback.
- Reuse requires the recorded method to match and every recorded membership to remain
  `proposed`/`active`; identical partitions are recorded as skipped memberships so the partition proof
  covers every group, and a deterministic baseline chunk is never reused as model grouping.
- A fatal grouping failure (corrupt checkpoint, revoked permission, unreadable artifact) records the
  stage as failed with a fixed safe error class and stops the lane before any card is built.
- `G60_GROUP_CONCURRENCY=4` enables a bounded four-call window. A validated partition is written
  before its first group event; a restart completes an interrupted commit without re-calling the
  model. Permissions are checked before each call and repair and before committing results.
- `--card-limit 8` selects a balanced shortlist before card persistence. It keeps all groups and
  claims for frequency analysis, excludes rejected/merged/superseded groups, and reuses selected
  cards only while their membership, cadence and review identity remain unchanged.
- `G60_JURY_CONCURRENCY=4` streams valid perspectives into durable artifacts. A partial jury resumes
  the same request and frozen personas, calls only missing roles, preserves successful assessments
  and old manifests, and permits one precise, value-free schema repair per role. Every critique is
  hypothetical; it cannot change evidence, scores or decisions.
- Inspect the returned stage status and `provisional/lane-state.json`, not just the CLI exit code.
  An incomplete grouping, draft or jury stage stays retryable and stops later stages. An export
  failure is explicitly returned as failed. Published artifacts are immutable.

Lane behaviour worth knowing:

- Live calls route only through the loopback budget gateway (`gateway.json`); permitted models are
  `deepseek/deepseek-v4.1-flash` and `xiaomi/mimo-v2.6-pro`. Reasoning effort `none` keeps the
  extraction latency bounded; MiMo failed JSON/schema validation in the real benchmark and is not
  used for extraction.
- Provider wording: the gateway enforces the allowlist, disables fallbacks and caps the price, then
  routes by price. It keeps no upstream provider identifier, so `provider`/`provider_routing` in
  metadata describe the request, not a guaranteed upstream provider.
- An attempt is bounded by a wall-clock deadline that aborts the socket, because the gateway
  forwards upstream keep-alives and a socket timeout alone never fires.
- Extraction keeps one immutable cache entry per exact validated input; failures are never cached
  and are retried on the next run. The worker window rolls, so one slow record cannot idle the pool,
  and a breaker stops scheduling on repeated transport or protocol failures. Records the breaker or
  deadline never scheduled stay visible as `failed_not_processed`/`failed_upstream_unhealthy`.
- Verified counts describe collected feedback parents with an extracted mention, never people or
  market prevalence. Accepted-evidence counts stay at zero in this lane and evidence level stays E0.
