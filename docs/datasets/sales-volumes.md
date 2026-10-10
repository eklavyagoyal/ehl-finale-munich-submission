# Sales volumes: `sales_volumes.xlsx`

Units per market. There is one sheet per vehicle, each with the same columns: `market`, `market_code`, `volume_2024`, `volume_2025`, `volume_2030`.

> The BMW data slide describes this dataset as "units by powertrain and region", but **the file has no powertrain split**, only markets. Powertrain mix has to come from elsewhere (e.g. the `Engine Type` share in the feedback files, which is not a sales share).
> `volume_2030` is presumably a **forecast/plan** (inferred; not stated).

## F70: BMW 1 Series (sheet `F70`)

| Market | Code | 2024 | 2025 | 2030 |
| --- | --- | ---: | ---: | ---: |
| Europe | EU | 80,000 | 85,000 | 87,000 |
| China | CN | 0 | 0 | 0 |
| USA | US | 0 | 0 | 0 |
| Rest of World | RoW | 25,000 | 28,000 | 31,000 |
| **Total** | | **105,000** | **113,000** | **118,000** |

## G60 / G68: BMW 5 Series (sheet `G60_G68`, sedan and long wheelbase combined)

| Market | Code | 2024 | 2025 | 2030 |
| --- | --- | ---: | ---: | ---: |
| Europe | EU | 110,000 | 115,000 | 127,000 |
| China | CN | 68,000 | 75,000 | 78,000 |
| USA | US | 75,600 | 78,000 | 80,000 |
| Rest of World | RoW | 25,000 | 28,000 | 31,000 |
| **Total** | | **278,600** | **296,000** | **316,000** |

## G70: BMW 7 Series (sheet `G70`)

| Market | Code | 2024 | 2025 | 2030 |
| --- | --- | ---: | ---: | ---: |
| Europe | EU | 11,000 | 13,000 | 17,000 |
| China | CN | 8,000 | 10,000 | 12,000 |
| USA | US | 10,000 | 12,000 | 14,000 |
| Rest of World | RoW | 5,000 | 7,000 | 9,000 |
| **Total** | | **34,000** | **42,000** | **52,000** |

## What this means for choosing a demo scope

- **1 Series = Europe (+ RoW) only.** A 1 Series demo only makes sense for EU. Its feedback is mostly GB, and its customer study covers EU only.
- **5 Series is the volume car**: ~2.6× the 1 Series in 2025 and selling in all three focus markets. In China it is the G68 long wheelbase; China has customer-study data (G68) but no feedback.
- **7 Series is small in volume (~42k)** but the most balanced across EU/CN/US. It has the most US feedback and has study data in all three regions.
- Projected growth 2025 → 2030: F70 +4 %, G60/G68 +7 %, G70 +24 %.
- The 5 Series sheet mixes G60 and G68, so per-derivative volumes are not available.

## Data coverage by vehicle and market

| | EU | CN | US |
| --- | --- | --- | --- |
| **F70** | sales ✓ · study ✓ · feedback (GB, SE, FR, DK, FI) | no sales | no sales |
| **G60** | sales ✓ · study ✓ · feedback thin | sales (as G68) | sales ✓ · study ✓ · feedback ✓✓ |
| **G68** | – | sales (combined with G60) · study ✓ · no feedback | – |
| **G70** | sales ✓ · study ✓ · feedback thin | sales ✓ · study ✓ · no feedback | sales ✓ · study ✓ · feedback ✓✓ |
