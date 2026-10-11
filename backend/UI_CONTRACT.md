# Parallax UI contract: structure, order, text

Status 2026-10-11:

- **Part A** is what Luis asked for. Build it now.
- **Part B** is proposed and waits for Luis' OK. Do not build it before he agrees.

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

### A2. Breadcrumbs and sidebar

- Every page uses the same breadcrumb form: `Vehicles › G60 › <Stage> › <Item>`. Every crumb except the last is a
  link, and "Vehicles" leads to `/`.
- The market is **not** a crumb. It is a filter chip in the header row (US / EU / CN / All).
- In the sidebar, **remove History** (the button; `/history` redirects to `/activity`). Activity stays at the
  bottom.

### A3. Only G60 under G60

The backend now scopes `/api/pipeline`, `/api/coverage` and `/api/vehicles` to the vehicle. The frontend does the
following:

- Sources matrix: columns **US / EU / CN / RoW** from `records_by_channel_bucket`. Countries appear on expand from
  `records_by_channel_market`.
- A collapsed section "Not about the G60" lists `scopes` (competitors, other BMW models, brand-wide) and drills in
  with `/api/coverage?scope=competitor|other_models|brand`.
- On the start page, `stages[0].outside_scope` is one muted line ("+18k not about the G60") that expands.
- Drop the gap warning built on exact tags. It was wrong because DE is not tagged as EU.

### A4. Processing in one glance

A horizontal funnel of the four steps in `stages[1].funnel`:

- Each step shows a number, a label and a muted `hint`; `detail` appears on click.
- `gap` is a side branch ("7,841 without a topic", with detail on click).
- `labeler_quality` is a small badge ("77 % same area as BMW"), with detail on click.
- Nothing else goes on this page.

### A5. Signals on one four-field map

The map from `GET /api/signals/map?market=` sits at the top of the Signals page.

Axes and quadrants:

- Axis labels come from `axes.x.label` / `axes.y.label`, with `hint` on hover.
- x uses a log scale; the threshold lines come from `axes.*.threshold`.
- Quadrant corners: `act` top right, `watch` top left, `protect` bottom right, `background` bottom left. Each
  corner shows its name and count, with the quadrant `hint` on hover.

Dots:

- Colour by `kind` (pain red, request blue, strength green, mixed grey), one size.
- Only the top signals in Act and Protect get a text label. Hover shows label, reviews and %.
- A dot with `requirement_ids` gets a small ring.

Clicking a dot opens `GET /api/signals/{feature_key}?market=` as a side panel:

- `how_sorted` is a vertical six-step list (collected → tagged → counted → classified → placed → grouped). Each
  step shows `label` + `short`; `detail` appears on expand. This answers "how was the pre-sorting done".
- Findings follow, `matches_signal` first, with the others collapsed as "+N other findings".
- Quotes appear on expand, then the "Draft requirement" action.

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

## Part B: proposed, waiting for Luis

- B1. The vehicle goes into the URL: `/v/g60`, `/v/g60/sources`, ..., `/v/g60/decision/[REQ-ID]`. Old routes
  redirect.
- B2. Below the map, one compact list per quadrant (Act first) replaces the three kind columns
  (pain / request / strength).
- B3. The frequency-vs-budget chart moves from Signals to Decision, because it is about simulated requirements.
- B4. Requirement tabs become Decision path · Councils · Evidence · Simulation · Timeline, and Overview folds into
  the header.
