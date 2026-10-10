# Parallax web

PM cockpit for Parallax (Next.js 16, shadcn/ui). It talks to the backend only through its own server-side proxy, so the browser never sees the API token.

## Run locally

```bash
cp .env.example .env.local      # pick the demo or the live backend
npm ci
npm run dev                     # http://localhost:3000
```

Demo backend with synthetic data (no token): `cd ../backend && scripts/db.sh start && scripts/demo_db.sh && scripts/demo_db.sh serve`.

## How it is wired

| Piece | Where |
| --- | --- |
| Proxy `/bff/<path>` → `${PARALLAX_API_URL}/api/<path>`, adds `Authorization: Bearer ${PARALLAX_API_TOKEN}` (if set) and `X-Actor: pm:<name>` | `src/app/bff/[...path]/route.ts` |
| PM identity: cookie `parallax_pm`, switcher in the sidebar footer, default `pm:luis` | `src/lib/actor.ts`, `src/components/app-sidebar.tsx` |
| Liveness, no auth and no backend call | `GET /health` → `src/app/health/route.ts` |
| Typed client (openapi-fetch) and SWR hooks | `src/lib/api/` |
| Response types (the spec only types requests) | `src/lib/api/types.ts` |

Regenerate the request types after every backend change and commit the result:

```bash
npx openapi-typescript https://parallax.dehlwes.net/api/openapi.json -o src/lib/api/schema.d.ts
```

## Screens

- **My tasks** (`/api/tasks`), **Requirements** (`/api/requirements`), **Activity** (`/api/audit`), **History** (`/api/learning/decisions`, `/api/learning/agreement`).
- **Requirement** (`/api/requirements/{id}`) with tabs Overview, Simulation (lanes per `agent_id`, one blue dot per LLM call from `/llm-calls`), Evidence and Timeline (`/audit`, `/versions`).
- Actions: run (`POST /api/simulations`, polled every 1.5 s), decide (409 shows the blocking gates with an override), challenge (follows the follow-up run), edit (`PATCH`), generate drafts (`/themes/build` + `/requirements/draft`).

Simulated (personas) and assumed (departments) ratings are shown as hypotheses with ranges; scores always show their low–high range.

## Deploy (nexus)

`Dockerfile` builds a standalone server on `node:22.23.3-bookworm-slim`, runs as a non-root user and listens on `0.0.0.0:$PORT`. Runtime env only: `PARALLAX_API_URL`, `PARALLAX_API_TOKEN`. The API stays under `/api` on the same host; the frontend owns everything else.
