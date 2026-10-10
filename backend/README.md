# Parallax backend

The backend for **Parallax**, a multi-agent decision workflow for the BMW challenge. It reads the evidence from the research contract (`feat/research-handoff`), counts it deterministically, and lets two simulations review each candidate requirement in parallel:

- a **market twin**: BMW owners in EU, US and China, simulated with TinyTroupe;
- a **company twin**: the Design, Engineering, Sales and Finance departments.

A research agent fills open questions, and a stronger model verifies its findings. A synthesizer combines everything, and a judge panel recommends an outcome. **The PM decides.** Every step is stored in Postgres and recorded in an append-only audit trail.

The frontend contract for the parallel UI agent is in [API.md](API.md), and the OpenAPI spec is in [openapi.json](openapi.json).

## Quick start

```bash
cd backend
/opt/homebrew/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
scripts/db.sh init                     # project-local Postgres on localhost:5433, no system service
cp .env.example .env                   # add OPENAI_API_KEY, set PARALLAX_LLM_MODE=openai
.venv/bin/python -m parallax.cli db-init
.venv/bin/python -m parallax.cli seed
.venv/bin/python -m parallax.cli ingest ../research/batches     # research branch checkout
.venv/bin/python -m parallax.cli themes
.venv/bin/python -m parallax.cli serve --reload                 # http://127.0.0.1:8000/api/docs
```

**Mock mode.** `PARALLAX_LLM_MODE=mock` is the default. It runs the whole pipeline offline with deterministic fake outputs, for UI work and tests.

**Demo database for the frontend.** `scripts/demo_db.sh` builds `parallax_demo`: synthetic fixtures (texts start with `SYNTHETIC`), drafted requirements and one finished mock run. `scripts/demo_db.sh serve` serves it on port 8001. The main database `parallax` holds only the real research batches.

**Tests.** `.venv/bin/python -m pytest` runs against the `parallax_test` database using synthetic fixtures.

## Flow

```text
research contract batches ──► ingest (validated, idempotent) ──► evidence tables
                                                     │
                                                     ▼
                     themes: distinct reviews per feature × market × cohort (code, not LLM)
                                                     │
                                                     ▼
                     drafter ──► requirements (8 brief fields, cited quotes verified)
                                                     │
                    ┌────────────────────────────────┴──────────────────────────────┐
                    ▼                                                               ▼
     market twin (TinyTroupe TinyWorld)                          company twin (4 departments)
     12 owner personas, grounded on real reviews                 design / engineering / sales / finance
     free text ──► SSR ──► importance + class fit                ranges only, status "assumed"
                    └──────────────── info requests ───────────────────────────────┘
                                                     ▼
                     research agent (web search) ──► verifier (strong model)
                                                     ▼
                     MCDA scoring (decision-model.json): bounds, sensitivity, gates
                                                     ▼
                     synthesizer ──► judge panel (heterogeneous models, majority)
                                                     ▼
                     PM: approve / reject / edit / challenge (challenge = follow-up run)
                                                     ▼
                     audit trail + decision snapshot + lessons (learning history)
```

A run handles up to 20 requirement cases at once, five in parallel (`PARALLAX_MAX_PARALLEL_CASES`). LangGraph is not used. The PM decision is an asynchronous API action rather than a graph interrupt, so a plain threaded pipeline with every step persisted in Postgres is simpler and fully traceable.

## Agents and who gets which persona

Personas are **BMW owner archetypes**, not generic people. Each persona owns a specific car in a specific market and everyday environment, and reacts from inside that context. The specs live in [`parallax/agents/roster/`](parallax/agents/roster) as editable JSON with `details_status: "skeleton"`; the details still need to be filled in together. To apply changes, use `cli seed` or `PUT /api/agents/{id}`. Every change is versioned.

| Persona | Market | Car / powertrain | Grounding (real data) | Validation path |
| --- | --- | --- | --- | --- |
| `us-ice-commuter` | US | 540i xDrive · ICE | US G60 owner reviews (ICE) | US_2025 study G60 (held out) |
| `us-bev-early-adopter` | US | i5 eDrive40 · BEV | US G60 reviews (BEV) | US_2025 study G60 |
| `us-phev-pragmatist` | US | 550e · PHEV | US G60 reviews (PHEV) | US_2025 study G60 |
| `us-loyal-enthusiast` | US | 540i / i5 M60 · ICE | US G60 reviews | US_2025 study G60 |
| `us-family-lessee` | US | 530i xDrive · ICE | US G60 reviews | US_2025 study G60 |
| `eu-de-company-car` | EU (DE) | 530e / 520d · PHEV | European G60 reviews + social | CN_EU_2025 study, EU G60 column |
| `eu-gb-bev-company-car` | EU (GB) | i5 eDrive40 · BEV | European G60 reviews (BEV) | CN_EU_2025 EU G60 |
| `eu-it-private-design` | EU (IT) | 520i · ICE | European G60 reviews | CN_EU_2025 EU G60 |
| `eu-se-family-phev` | EU (SE) | 530e · PHEV | European G60 reviews (PHEV) | CN_EU_2025 EU G60 |
| `cn-lwb-chauffeur-owner` | CN | 530Li G68 · ICE | G68 China study (+ G68 reviews) | **none**: output labeled "assumption" |
| `cn-young-tech-professional` | CN | i5 eDrive35L G68 · BEV | G68 China study | none, assumption |
| `cn-family-multigen` | CN | 525Li G68 · ICE | G68 China study | none, assumption |

The company twin is a committee. Regional sales leads only review cases for their own market (and pooled cases).

| Department / worker | Rates | Status of its numbers |
| --- | --- | --- |
| `dept:product-management` | vehicle/market fit, reuse (class boundary 1/5/7 Series, portfolio) | assumed range |
| `dept:design` | vehicle/market fit, impact | assumed range |
| `dept:engineering` | delivery fit, reuse | assumed range (no specs) |
| `dept:sales-eu`, `dept:sales-us`, `dept:sales-cn` | vehicle/market fit, competitive gap, each for its own region | assumed range |
| `dept:quality` | impact (defect severity, reliability, perceived quality) | assumed range |
| `dept:finance` | delivery fit (effort band only, no numbers) | assumed range |
| `agent:drafter` | drafts the 8 fields, scope gate | – |
| `agent:research` / `agent:verifier` | web research, then verification with the strong model | `estimated` competitive gap, only if verified |
| `agent:synthesizer` | PM brief: market vs. internal view, conflicts, evidence vs. simulation | – |
| `judge:1..3` | independent votes using `PARALLAX_JUDGE_MODELS` | recommendation only |
| `agent:challenger` | strongest case against the panel's outcome, with evidence that would change the call | advisory, shown to the PM |

### How the classic product process maps onto Parallax

| Classic step | What the app does | What stays with the human |
| --- | --- | --- |
| 1 Understand customers | Themes from feedback, study and web; synthesis proposes `clinic_questions` | Running clinics and conjoint studies |
| 2 Benchmarking | Competitor evidence (competitor batches), research agent + verifier, `competitive_gap` | Setting the target value |
| 3 Target groups | Market views per theme, owner personas per segment | Choosing the target group |
| 4 Structuring | Proposed `kano_class` + `benchmark_target` per requirement, with rationale | Review and edit (PATCH) |
| 5 Decide | MCDA score with bounds, judge panel, challenger | PM decides; everything lands in the audit trail |

### How personas are validated

The persona describes, in free text, how satisfied it is with each study attribute of its current car. SSR converts that text into a 1–5 rating. The result is compared with the **customer study, which the persona never saw**, using Spearman rank correlation.

A demographics-only twin of the same persona serves as the baseline. Grounding has to beat it, otherwise the persona is not `validated`. China has no feedback and only the G68 study, which already serves as grounding there, so CN personas run as `unvalidated_assumption`. Persona weights are market exposure × validation multiplier (`policy.parallax.persona_weighting`).

## Deployment on nexus-prod (workspace `dehlwes`, group `EHL`)

| Piece | nexus object | Notes |
| --- | --- | --- |
| API | app `parallax-api`, GitHub `eklavyagoyal/ehl-finale-munich-submission`, branch `feat/backend`, subdir `backend` | Dockerfile in this folder; `serve-prod` migrates, syncs agents and listens on `0.0.0.0:$PORT`; `GET /health` is 200 only when the DB answers |
| Database | store `parallax-pg` (pgvector recipe), bound with profile `sql` | Injects `DATABASE_URL`; the app converts it to the psycopg driver |
| Shared config | group `EHL` env | `OPENAI_API_KEY` (operator fills), `PARALLAX_LLM_MODE`, model names |
| Auth | nexus injects `PARALLAX_API_API_TOKEN` (used by the frontend via the mesh) | Every `/api` call needs `Authorization: Bearer <token>` (except `/api/health`, `/api/docs`, `/api/openapi.json`) |
| CLI token | `PARALLAX_CLI_TOKEN`, minted by nexus (`generate`), never seen by an agent | For `push-research` and `smoke`: the operator copies it from the nexus UI into local `backend/.env` as `PARALLAX_REMOTE_TOKEN`. Rotate with `deploy.rotate_secret` (mode `generate`), then redeploy |
| Frontend (later) | app `parallax-web` in group `EHL` | The mesh injects `PARALLAX_API_URL` + `PARALLAX_API_TOKEN` into it; the frontend calls the API server-side with that token and passes `X-Actor` |
| Data | `python -m parallax.cli push-research ../research --url https://<api-host> --token <token>` | Uploads the research contract as a zip to `POST /api/ingest/upload` |

Debugging: `deploy.logs` (runtime) and `deploy.logs kind:build` (image build) on nexus.

## Rules the code enforces

- **LLM permission gate** (`parallax/llm/gate.py`): record text reaches OpenAI only if its source is `accepted` and `export_permissions.external_llm == true`. Exclusions are logged per call.
  - On the current research branch, every source is `pending` with `external_llm: null`, so nothing goes out until a PM accepts sources through `POST /api/sources/.../review`. Without cleared evidence, the drafter works from counts and labels only.
- **Counting:** distinct reviews per feature and cohort, never people or prevalence.
  - Competitor reviews are kept as competitive context and never counted as G60 demand.
  - G68 evidence is **not** counted as China demand by default, matching the research contract. A PM can enable `policy.parallax.market_proxies = {"CN": ["bmw:G68"]}` with an audited policy publish; proxy evidence would still never count as direct G60 evidence. CN personas still drive a G68, as a labeled simulation assumption.
- **Scoring** follows `decision-model.json` exactly:
  - 6 criteria on a 0–5 scale, gates, and bounds with unknown = 0/5 and no renormalization.
  - Simulated and assumed ratings only form ranges.
  - `score` is the midpoint of the bounds, with a ±20 % weight-sensitivity check.
- **Only humans decide** (`X-Actor: pm:*`). Approval needs every gate on `pass`; otherwise the API returns 409.
  - A PM gate override needs a rationale and sticks: automatic checks never revert human-set gates.
  - AI updates never overwrite fields the PM wrote last.
  - The vote is advice: it is capped at `investigate` while gates are unknown.
  - Priority re-ranks are audited (`code:rank`).
- **Audit trail:** `audit_events` has a Postgres trigger that rejects UPDATE and DELETE. It covers changes, decisions, AI actions, evidence reviews and every HTTP access.
  - `llm_calls` stores model, prompt version + hash, input record IDs, tokens and trimmed payloads for every call, including TinyTroupe's.
- **Learning history:** each PM decision stores a snapshot of the AI recommendation, ratings, votes, persona and department stances, plus policy and agent versions. Lessons (PM rationale + embedding) go to future syntheses on similar features. `GET /api/learning/agreement` shows which agents track PM judgment, the basis for later weight calibration.

## Layout

```text
parallax/
  config.py  db.py  models.py      settings, engine, schema (5 layers)
  contract.py  ingest.py           research contract validation + import (+ derived claims from BMW VFC labels)
  themes.py  policy.py  scoring.py deterministic signals, decision policy, MCDA
  requirements.py  decisions.py    lifecycle, versions, gates, PM actions, evidence review
  orchestrator.py  learning.py     runs (stages A–E), decision history, lessons
  audit.py                         append-only events
  llm/      client.py gate.py ssr.py prompts.py
  agents/   roster.py roster/*.json grounding.py market_twin.py company_twin.py research.py
            synthesis.py vote.py drafter.py validation.py
  api/      app.py routers/{evidence,requirements,simulations,agents,governance}.py
  migrations/                      alembic (0001 = full schema + audit trigger)
```

## Open points

- **Data handoff from the research branch:** BMW feedback, study and sales batches plus claims for the social batches are still missing. Until they arrive, only the competitor batches carry claims (competitive context, not G60 demand), so real data produces **no draftable themes yet**. That is the honest state of the evidence.
  - The validation parser expects study metrics as `mean`, or as US scale points named `Attribute | Scale label`. Adjust `agents/validation.py::reference_values` once the format is fixed.
- **TinyTroupe engine:** tested only in mock mode so far, where it falls back to the direct engine. Run one real persona run as soon as the API key is in place. `PARALLAX_PERSONA_ENGINE=direct` is the fallback.
- **Model names** come from `.env`. Check what your key offers with `python -m parallax.cli models`.
