# Parallax UI contract: structure, order, text

Agreed with Luis on 2026-10-11. This file fixes page structure, order and how much text appears. It changes only
when Luis agrees. Design follows the minimal style: hairlines, about 10 % text, details on demand. The data comes
from [API.md](API.md).

## 1. Text levels

Every element shows **one label plus one number or one line**. Longer text appears only on click (expand or side
panel, with a quiet "More" affordance). No paragraph is visible by default on any page.

| Level | API fields | Shown |
| --- | --- | --- |
| Label | `label`, `title` | always |
| One line | `headline` (trace), `hint` (funnel, axes, quadrants), `short` (how_sorted) | always, muted |
| Long form | `detail`, `why`, `output`, `caveat`, `description` | on click only |

## 2. Scope lives in the URL

Everything about a vehicle sits under `/v/[code]`. The landing page only picks the vehicle.

| Route | Page |
| --- | --- |
| `/` | Landing: vehicle cards (`GET /api/vehicles`), only G60 clickable |
| `/v/g60` | Vehicle start: five stage cards (`GET /api/pipeline?vehicle=G60`) |
| `/v/g60/sources` | Sources |
| `/v/g60/processing` | Processing |
| `/v/g60/signals?market=US` | Signals (four-field map) |
| `/v/g60/signals/[feature_key]?market=US` | One signal opened (may also be a side panel over the map) |
| `/v/g60/experts` | Expert pipeline |
| `/v/g60/decision` | Decision list |
| `/v/g60/decision/[REQ-ID]` | Requirement, tabs below |
| `/activity` | Global activity (sidebar bottom) |

Old routes (`/pipeline`, `/sources`, `/signals`, `/requirements/...`, `/history`) redirect to the new ones.

## 3. Breadcrumbs

The route defines them, always in this form: `Vehicles › G60 › <Stage> › <Item>`. Every crumb except the last is
a link. The market is **not** a crumb. It is a filter chip in the header row (US / EU / CN / All). The landing page
has no breadcrumb.

## 4. Sidebar

Stages in this order: Sources, Processing, Signals, Expert pipeline, Decision. At the bottom there is only
Activity. **Remove History** (the button and the route; `/history` redirects to `/activity`). The "My tasks"
counter stays top right.

## 5. Pages

**Vehicle start (`/v/g60`).** Five cards, each with a title, one big number and one muted line:

- Sources: the vehicle's own records. `outside_scope` appears as one muted line ("+18k not about the G60") that
  expands.
- Processing: a mini funnel from `funnel`.
- Signals: `by_quadrant` (e.g. "Act 23 · Protect 17").
- Experts: runs.
- Decision: open decisions.

**Sources.** Show only the vehicle's own records; `GET /api/coverage` defaults to `scope=target`.

- Matrix columns are **US / EU / CN / RoW** from `records_by_channel_bucket`. Countries appear on expand from
  `records_by_channel_market`.
- A collapsed section "Not about the G60" lists `scopes` (competitors, other BMW models, brand-wide) and drills in
  with `?scope=competitor|other_models|brand`.
- Drop the gap warning built on exact tags. It was wrong because DE is not tagged as EU.

**Processing.** A horizontal funnel of the four steps in `stages[1].funnel`:

- Each step shows a number, a label and a muted hint; `detail` appears on click.
- `gap` is a side branch ("7,841 without a topic", with detail on click).
- `labeler_quality` is a small badge ("77 % same area as BMW"), with detail on click.
- Nothing else goes on this page.

**Signals.** The four-field map from `GET /api/signals/map?market=` comes first.

Axes and quadrants:

- Axis labels come from `axes.x.label` / `axes.y.label`, with `hint` on hover.
- x uses a log scale; the threshold lines come from `axes.*.threshold`.
- Quadrant corners: `act` top right, `watch` top left, `protect` bottom right, `background` bottom left. Each
  corner shows its name and count, with the quadrant `hint` on hover.

Dots:

- Colour by `kind` (pain red, request blue, strength green, mixed grey), one size, hairline style.
- Only the top signals in Act and Protect get a text label. Hover shows label, reviews and %.
- A dot with `requirement_ids` gets a small ring.

Clicking a dot opens `GET /api/signals/{feature_key}?market=` as a side panel:

- `how_sorted` is a vertical six-step list (collected → tagged → counted → classified → placed → grouped). Each
  step shows `label` + `short`; `detail` appears on expand. This answers "how was the pre-sorting done".
- Findings follow, `matches_signal` first, with the others collapsed as "+N other findings".
- Quotes appear on expand, then the "Draft requirement" action.

Below the map goes one compact list per quadrant (Act first), replacing the three kind columns. The
frequency-vs-budget chart moves to the Decision page, because it is about simulated requirements.

**Expert pipeline.** The requirement list plus run status. A failed run shows its `error` line, e.g. "Interrupted:
the server restarted… Start it again.".

**Decision.** The list plus the frequency-vs-budget chart (`GET /api/budgets`).

**Requirement tabs, in this order:** Decision path (default) · Councils · Evidence · Simulation · Timeline.
Overview folds into the header.

- Decision path: each step shows only `title`, `headline` and the effect arrow. Expanding shows `why`, `output` and
  `caveat`.
- Councils: show only the markets that answered. Since 2026-10-11 a US case is answered by the US owners only,
  matching Sales US (`persona_scope=market`). Add one muted line: "Owners and Sales are asked per market; the other
  departments are global."

## 6. Allowlist (`/bff`)

Add: `GET /api/signals/map`, `GET /api/signals/{feature_key}`, and the new query parameters on `/api/coverage`
(`scope`, `vehicle`), `/api/records` (`scope`, `bucket`, `vehicle`) and `/api/pipeline` (`vehicle`).
