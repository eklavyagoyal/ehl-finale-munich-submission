# Parallax API: frontend contract

Base URL: `http://127.0.0.1:8000` for real data, or `http://127.0.0.1:8001` for the synthetic demo database (`backend/scripts/demo_db.sh serve`). The full machine-readable spec is [`openapi.json`](openapi.json), and the interactive docs are at `/api/docs` while the server runs.

**Identity.** Send `X-Actor: pm:<name>` on every request. The backend audits every request, including reads.

**Auth (deployed).** On nexus every `/api` call needs `Authorization: Bearer <token>`; only `/api/health` is open. The frontend app gets `PARALLAX_API_URL` and `PARALLAX_API_TOKEN` injected by nexus and should call the API server-side (route handler / proxy), never expose the token to the browser. Locally no token is needed.

**Human-only actions.** Decisions, edits, gate overrides, evidence review, manual ratings and spec changes need a `pm:` actor. Any other actor gets 403.

**Types.** Responses of the main endpoints are typed in the OpenAPI spec (`RequirementOut`, `RequirementDetailOut`, `TaskOut`, `RunDetailOut`, `LLMCallOut`, `AuditPageOut`, ...), so `openapi-typescript` generates them.

**IDs.**
- Requirements: `REQ-G60-0001`.
- Agents: `persona:us-bev-early-adopter`, `dept:engineering`, `judge:1`, `agent:synthesizer`.
- Runs: UUIDs.

## Typical PM flow

| Step | Call |
| --- | --- |
| 0. Sidebar "My tasks" | `GET /api/tasks`: `decide` / `simulate` items carry `requirement_id`, `score`, `score_low`, `score_high`; `running` items carry `run_id`, `requirement_ids`, `stage`; `review_evidence` carries `count` |
| 1. See what evidence exists | `GET /api/coverage` |
| 2. Accept evidence (separate from approving requirements) | `POST /api/sources/{id}/review` or `POST /api/sources/review-bulk` |
| 3. Build signals | `POST /api/themes/build`, then `GET /api/themes?market=US` |
| 4. Let the AI draft requirements | `POST /api/requirements/draft {"market": "US", "limit": 5}` |
| 5. Requirement list | `GET /api/requirements?sort=priority` |
| 6. Run Parallax on up to 20 cases (5 in parallel) | `POST /api/simulations {"requirement_ids": [...], "challenge": null}` |
| 7. Follow progress (poll every 1–2 s) | `GET /api/simulations/{run_id}` |
| 8. Detail view | `GET /api/requirements/{id}` |
| 9. Decide | `POST /api/requirements/{id}/decision {"action": "approve", "rationale": "..."}` |
| 10. History | `GET /api/requirements/{id}/versions`, `GET /api/requirements/{id}/audit`, `GET /api/audit` |

## Shapes the UI needs most

### `GET /api/requirements` returns a list of requirement objects

The list covers all 8 brief fields:

| Brief field | Backend field(s) |
| --- | --- |
| Unique identifier | `id` |
| Clear, actionable description | `title`, `description`, `customer_problem`, `acceptance_criteria[]` |
| Linked findings and sources | in the detail view: `evidence[]` |
| Priority or score | `priority_rank`, `score` (midpoint of `score_low`..`score_high`, 0–100) |
| Prioritization rationale | `prioritization_rationale` |
| Evidence level | `evidence_level`: `strong` / `moderate` / `weak` / `simulated_only` / `none`, plus `evidence_level_explanation` |
| Future-facing assumptions and uncertainties | `assumptions[]`, `uncertainties[]` |
| Current decision status | `status`: `draft` / `proposed` / `in_review` / `approved` / `rejected` / `challenged` / `deferred` |

Extra fields:
- Structuring: `kano_class` (`must_be` / `performance` / `attractive` / `indifferent` / `reverse` / `unclear`), `kano_rationale`, `benchmark_target`. These are AI proposals; the PM edits them via PATCH.
- `gates`: `{gate: "pass" | "fail" | "unknown"}`.
- `ai_recommendation`: `approve` / `reject` / `investigate` / `defer` / null.
- Also `market`, `feature_key`, `version`, `last_run_id`.

### `GET /api/requirements/{id}`

```jsonc
{
  "requirement": { /* as in the list */ },
  "gates": { "evidence_traceability": {"value": "pass", "owner": "system:gates", "reason": "...", "at": "..."} },
  "scores": {
    "criteria": {
      "demand": {"score": 3.0, "low": 3.0, "high": 3.0, "status": "observed", "raters": ["code:theme-counts"], "weight": 0.25},
      "vehicle_market_fit": {"score": null, "low": 2.4, "high": 3.6, "status": "simulated+assumed", "raters": ["market_twin:US", "dept:sales"]}
    },
    "score_low": 43.5, "score_high": 58.3, "score_midpoint": 50.9, "unknown_criteria": [], "uncertain_criteria": ["vehicle_market_fit"]
  },
  "ratings": [ /* every individual rating with rater + rationale */ ],
  "evidence": [ {"record_id": "...", "relation": "supporting|contradicting|context", "quote": "...", "quote_verified": true,
                 "record": {"text": "...", "markets": ["US"], "source_id": "...", "locator": {}}} ],
  "synthesis": { "content": { "headline": "...", "market_views": [], "internal_view": "...", "research_view": "...",
                              "conflicts": [], "evidence_vs_simulation": "...", "suggested_requirement_edit": null,
                              "clinic_questions": ["..."] } },
  "recommendation": { "recommendation": "investigate", "tally": {"counts": {"approve": 2, "reject": 1}, "gate_cap": "..."}, "minority_report": [],
                      "challenge": {"counter_position": "...", "strongest_arguments": [], "overlooked_segments": [],
                                    "evidence_that_would_change_the_call": [], "risk_if_outcome_is_wrong": "medium"} },
  "votes": [ {"agent_id": "judge:1", "model": "...", "vote": "approve", "rationale": "..."} ],
  "persona_responses": [ {"agent_id": "persona:us-bev-early-adopter", "stance": "positive", "importance_0_5": 3.4,
                          "ssr_distribution": [0.1, 0.2, 0.3, 0.25, 0.15], "response_text": "...", "concerns": []} ],
  "department_memos": [ {"agent_id": "dept:engineering", "stance": "neutral", "memo": {"summary": "...", "effort_band": "medium", "criterion_ratings": []}} ],
  "research": [ {"question": "...", "requested_by": "dept:sales", "verdict": "verified", "findings": [], "sources": [], "verification": {}} ],
  "decisions": [ {"action": "approve", "rationale": "...", "actor_id": "pm:lisa", "ai_recommendation": "approve", "agreed_with_ai": true} ]
}
```

**Labeling rule for the UI.** Rating `status` tells you where a number comes from:
- `observed`: computed from real reviews.
- `estimated`: verified research.
- `simulated`: market twin.
- `assumed`: departments.

Show `simulated` and `assumed` values as ranges and visibly as hypotheses. `score` is a midpoint of bounds, so show `score_low`..`score_high` next to it.

### `POST /api/requirements/{id}/decision`

Body: `{"action": "approve" | "reject" | "challenge" | "defer", "rationale": "required", "challenge_question": "optional"}`.

Responses:
- **409** when approving while any gate other than `pm_review` is not `pass` (`fail` or `unknown`). Fix the requirement, add evidence, or `POST /api/requirements/{id}/gates/{gate}` with a rationale. PM overrides stick.
- **200** returns `{decision, requirement, followup_run_id}`.
- `challenge` starts a follow-up run automatically. Poll it like any other run.

### Other PM actions

| Action | Call and body |
| --- | --- |
| Edit content | `PATCH /api/requirements/{id}` with `{"changes": {"title": "...", "acceptance_criteria": [...]}, "rationale": "..."}`. Creates a new version. |
| Link evidence | `POST /api/requirements/{id}/evidence` with `{"record_id", "relation", "quote"?, "rationale"}` |
| Add a reviewed criterion rating | `POST /api/requirements/{id}/ratings` with `{"criterion", "score"` or `"low"/"high", "status", "rationale"}` |
| Override a gate | `POST /api/requirements/{id}/gates/{gate}` with `{"value", "rationale"}` |
| Create manually | `POST /api/requirements` with `{"title", "description", "market"?, "feature_key"?, ...}` |

### Runs

| Call | Returns |
| --- | --- |
| `GET /api/simulations/{id}` | `{run: {status: queued\|running\|completed\|partial\|failed, progress: {stage, completed_stages[], errors[]}, llm_calls, input_tokens, output_tokens}, steps: [...]}` |
| `GET /api/simulations/{id}/results` | All outputs grouped by requirement |
| `GET /api/simulations/{id}/llm-calls?requirement_id=&agent_id=` | Every model call: model, prompt version, input record IDs, tokens, timestamps. For the blue dots on the simulation lanes; `agent_id` is the lane. Add `include_payloads=true` to get the full prompts. |

Run stages, in order:
1. `market_and_company_twin`
2. `research`
3. `scoring`
4. `synthesis_and_vote`

### Agents

| Call | Purpose |
| --- | --- |
| `GET /api/agents?kind=market_persona` | Personas; also `department`, `judge` |
| `GET /api/agents/{id}` | Spec and versions |
| `GET /api/agents/{id}/grounding` | Which real reviews the persona sees |
| `PUT /api/agents/{id}` with `{"spec": {...}, "rationale": "..."}` | Edit a persona or department. Creates a new version and resets persona validation. |
| `POST /api/agents/validate` | Persona validation, run in the background |

### Governance

| Call | Purpose |
| --- | --- |
| `GET /api/meta` | Configuration, counts and enum values for dropdowns |
| `GET /api/policy` / `PUT /api/policy` | Decision model (weights, anchors). Each change is versioned. |
| `GET /api/audit?requirement_id=&actor_id=&category=change\|decision\|ai\|evidence\|system\|access` | Filtered audit trail (sidebar "Activity"; requirement tab "Timeline" together with `/versions`) |
| `GET /api/learning/agreement` | Per agent: share of decisions where it agreed with the PM |
| `GET /api/learning/decisions`, `GET /api/learning/lessons` | Decision history (sidebar "History") and lessons |

## Flow endpoints (start page, signals, councils, decision path)

| Call | Use in the UI |
| --- | --- |
| `GET /api/vehicles` | Landing page: vehicles with `status` (`active` / `data_available` / `not_imported`), record counts, plus "Across vehicles" |
| `GET /api/pipeline` | Start page: five stages (sources → processing → signals → experts → decision) with `question`, `status`, `counts`, `next_action` |
| `GET /api/signals?market=US\|EU\|CN&kind=pain\|request\|strength\|mixed\|all` | Signals page: per signal counts, `sample_quotes`, `has_requirement`, `condensed` and `findings[]` (title, description, kind, reviews, share, quotes) |
| `POST /api/signals/condense {markets, kinds, limit}` | Condense top signals into findings (background run; poll `/api/simulations/{run_id}`) |
| `GET /api/requirements/{id}/trace` | **Decision path**: ordered steps `evidence → customers → company → research → scores → synthesis → challenger → judge → decision`; each step has `agents`, `inputs`, `output`, `why`, `basis` (evidence / simulation / assumption / mixed / human), `effect` (supports / against / neutral), optional `caveat`, `tensions`, `drill_down` |
| `GET /api/requirements/{id}/council` | Customer council by market (personas with verdict, budget points, quote) vs. company council (department verdict, main argument, cost view) and `tensions` |
| `GET /api/simulations/{run_id}/conversation` | Who was asked what (`question_to_owners`) and every answer, grouped by market; departments; research; challenger; judge |
| `GET /api/simulations/{run_id}/llm-calls` | Persona calls now carry `agent_id = persona:<id>` (one lane per persona) |

Validation results to show honestly: the customer council is reliable (same verdict 90 % on a repeat run) and rejects decoys, US personas match the BMW study moderately (rho ~0.5-0.6), EU is weak, China untestable. Company council verdicts rarely differ: show its arguments and tensions, not the verdict counts.
