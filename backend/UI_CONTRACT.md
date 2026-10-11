# Parallax UI contract: structure, order, text

Status 2026-10-11 (second round, after Luis' feedback):

- **Part A** is what Luis asked for. Build it now. A2, A4 and A5 were replaced in the second round.
- **Part B** is proposed. B1 is now part of A2; B2–B4 are **not** to be built.
- The Expert pipeline stays as it is; Luis reviews it together with the backend.

Design follows the minimal style: hairlines, about 10 % text, details on demand. The data comes from
[API.md](API.md). Any structure change beyond this file goes through Luis first.

## Part A: requested by Luis

### A1. Text levels

Every element shows **one label plus one number or one line**. Longer text appears only on click (expand or side
panel, with a quiet "More" affordance). No paragraph is visible by default on any page.

| Level | API fields | Shown |
| --- | --- | --- |
| Label | `label`, `title` | always |
| One line | `headline` (trace), `hint` (funnel, axes, quadrants), `short` (how_sorted) | always, muted |
| Long form | `detail`, `why`, `output`, `caveat`, `description` | on click only |

### A2. Overview first, then the vehicle

1. **`/` Overview** (no breadcrumbs, no stage sidebar) shows which data we have, across all vehicles: streams
   (BMW, social, competitors), scopes (this vehicle, other BMW models, competitors, brand-wide) and the triage state
   (vehicle checked, owner yes/no, relevant yes/no; see `/api/triage/summary` once deployed). Below that come the
   vehicle cards; only G60 is clickable.
2. **Inside a vehicle** (`/v/g60`, `/v/g60/sources`, ..., `/v/g60/decision/[REQ-ID]`) everything is filtered to
   that vehicle.
   - Breadcrumbs: `Overview › G60 › <Stage> › <Item>`.
   - The market is a filter chip, not a crumb.
   - Old routes redirect.
3. **Sidebar** (inside a vehicle): the stages Sources, Processing, Signals, Expert pipeline, Decision. At the
   bottom only Activity. **History is removed** (the button; `/history` redirects to `/activity`). The "My tasks"
   counter stays top right.

### A3. Only G60 under G60

The backend now scopes `/api/pipeline`, `/api/coverage` and `/api/vehicles` to the vehicle. The frontend does the
following:

- Sources matrix: columns **US / EU / CN / RoW** from `records_by_channel_bucket`. Countries appear on expand from
  `records_by_channel_market`.
- A collapsed section "Not about the G60" lists `scopes` (competitors, other BMW models, brand-wide) and drills in
  with `/api/coverage?scope=competitor|other_models|brand`.
- On the start page, `stages[0].outside_scope` is one muted line ("+18k not about the G60") that expands.
- Drop the gap warning built on exact tags. It was wrong because DE is not tagged as EU.

### A4. Processing as a flow, not four numbers

Draw `stages[1].flow` as a left-to-right flow (Sankey-like, thin bands, hairline style). `nodes[]` have `key`,
`label`, `count`, `hint`, `detail`; `links[]` have `source`, `target`, `value`.

- The bands show the connection: reviews split into BMW labels / our AI labeler / no topic; the labelled ones flow
  into signals; par### A5. Signals: one big map

- The four-field map from `GET /api/signals/map?market=` spans the full page width and is the first thing on the
  page. The market switch (US / EU / CN / All) sits above it.
- Axes, threshold lines and quadrant corners come from the response: `act` top right, `watch` top left, `protect`
  bottom right, `background` bottom left. The corners show name and count; hints appear on hover.
- Dots are coloured by `kind` (pain red, request blue, strength green, mixed grey). Only the top signals in Act and
  Protect get a text label. Hover shows label, reviews and %.
- Clicking a dot selects it (ring) and opens `GET /api/signals/{feature_key}?market=` as a side panel:
  - `how_sorted` as six steps (label + short; detail on expand)
  - then the findings (`matches_signal` first, others collapsed)
  - then quotes on expand
- **"Draft requirements (n)" appears top right only when at least one signal is selected.** There is no permanent
  button.
- Below the map the pain / request / strength columns stay (Luis understands them), with checkboxes that feed the
  same selection.
- The explanatory text (`basis`) and the legend go to the very bottom of the page, small and muted.

### A6. Requirement pages

- Decision path: each step shows only `title`, `headline` and the effect arrow. Expanding shows `why`, `output` and
  `caveat`.
- Councils: show only the markets that answered. A US case is now answered by the US owners only, matching Sales
  US (`persona_scope=market`). Add one muted line: "Owners and Sales are asked per market; the other departments
  are global."
- Expert pipeline: a failed run shows its `error` line ("Interrupted: the server restarted… Start it again.").

### A7. Allowlist (`/bff`)

Add: `GET /api/signals/map`, `GET /api/signals/{feature_key}`, and the new query parameters on `/api/coverage`
(`scope`, `vehicle`), `/api/records` (`scope`, `bucket`, `vehicle`) and `/api/pipeline` (`vehicle`).

## Part B: decided

- B1 (vehicle in the URL) is part of A2.
- Not to be built: B2 (quadrant lists instead of kind columns), B3 (moving the budget chart) and B4 (new tab order).
