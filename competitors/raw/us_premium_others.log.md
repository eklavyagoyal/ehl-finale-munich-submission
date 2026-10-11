# us_premium_others — research log (market US)

Agent key: `us_premium_others` · Output: `us_premium_others.jsonl` (440 records) · Run date: 2026-10-10
Budget used: 40 of about 45 WebFetch calls (counting failures) and 9 of about 15 WebSearch calls. Search snippets were used only to find URLs. No record cites a search result.

## Models covered

| Model | Generation label used | Competitor | Feedback records (unique reviews/posts) | Equipment |
| --- | --- | --- | --- | --- |
| Genesis G80 incl. Electrified G80 | `RG3` | C001 | 80 owner_review (20) + 11 owner_forum (3) + 28 press (2) | 20 |
| Lexus ES, 7th gen | `XZ10` (MY2019–2025) | C002 | 99 owner_review (25) + 18 press (2) | 20 |
| Lexus ES, 8th gen (on sale in US since MY2026) | `8th gen (MY2026+)` | C003 | 0 owner (none published yet) + 14 press (2) | 20 |
| Cadillac CT5 incl. 2025 refresh, V-Series | `1st gen (MY2020+)` | C004 | 94 owner_review (26) + 12 press (2) | 20 |

**8th-gen ES check.** The 2026 ES is released in the US: ES 350e, ES 500e and ES 350h. The KBB 2026 page, MotorWeek and the Lexus pressroom all confirm it, and the Lexus pressroom calls it the "eighth-generation" ES. None of the fetched pages states a chassis/generation code, so a descriptive label is used instead of inventing one.

**CT5.** None of the fetched pages states an official generation code, so the label `1st gen (MY2020+)` is used.

## Sources

| URL | Status | Records |
| --- | --- | --- |
| cars.com/research/genesis-g80-2024/consumer-reviews/ | empty (0 reviews) | 0 |
| cars.com/research/genesis-g80-2021/consumer-reviews/ | ok, 8 of 8 reviews (fetched twice: once for the list, once for exact wording) | 18 feedback (6 reviews) |
| cars.com/research/genesis-g80-2022/consumer-reviews/ | ok, 4 of 4 | 14 (3) |
| cars.com/research/genesis-g80-2023/consumer-reviews/ | ok, 2 of 2 | 11 (2) |
| kbb.com/genesis/g80/2021/consumer-reviews/ | ok, "8 of 12" shown + 2 featured; page mixes model years | 37 (9) |
| kbb.com/genesis/electrified-g80/2023/consumer-reviews/ | 0 consumer reviews. KBB expert review used (fetched twice) | 12 press + 7 equipment |
| autoguide.com/car-comparisons/genesis-g80-vs-bmw-5-series-comparison | ok (twin test, 2021 G80 3.5T vs 2021 540i xDrive, i.e. G30) | 16 press + 2 equipment |
| genesis.com/us/en/g80 | ok (MY2027 page) | 1 competitor + 11 equipment |
| genesisowners.com/…/2021-genesis-g80-2-5t-owners-opinion.36608/ | ok, 7 posts | 11 owner_forum (3 posters) |
| caranddriver.com/genesis/g80-2025 | blocked (tool cannot fetch domain) | 0 |
| motortrend.com/cars/genesis/g80/2025/ | blocked (tool cannot fetch domain) | 0 |
| cars.com/research/lexus-es-2019/consumer-reviews/ and …/lexus-es-2020/… | empty (wrong slug; generic page) | 0 |
| kbb.com/lexus/es/2019/consumer-reviews/ | ok, "8 of 70" + 2 featured; mixes MY2019–2025. `?page=2` returns page 1 again. A re-ask for an expert review found none | 32 (8) |
| cars.com/research/lexus-es_350-2019/consumer-reviews/ | ok, page 1 of 13 (125 reviews; mixes ES 350/300h years) | 40 (8) |
| cars.com/research/lexus-es_300h-2021/consumer-reviews/ | ok, 10 of 11 | 27 (9) |
| kbb.com/lexus/es/2025/ | ok (KBB expert review, Colin Ryan, 2025-01) | 1 competitor + 9 press + 14 equipment |
| cars.com/articles/2022-lexus-es-350-6-things-we-like-and-4-not-so-much-446863/ | ok (Matt Schmitz, 2022-02) | 9 press |
| kbb.com/lexus/es/2026/ | ok (KBB expert review, Eric Brandt, 2026-05). The single consumer review is not visible | 1 competitor + 10 press + 10 equipment |
| motorweek.org/first-impressions/quick-spins/2026-lexus-es/ | ok | 4 press + 1 equipment |
| pressroom.lexus.com/?p=73364 | ok but only navigation/teasers in the first 100k characters; no specs | 0 (confirms "eighth-generation") |
| cars.com/research/lexus-es_350h-2026/consumer-reviews/ | empty (0 reviews) | 0 |
| cars.com/research/cadillac-ct5-2020/consumer-reviews/ (+ `?page=2`) | ok, pages 1–2 of 3 (25 reviews) | 47 (16) |
| cars.com/research/cadillac-ct5-2025/consumer-reviews/ | ok, 2 of 2 | 8 (2) |
| kbb.com/cadillac/ct5/2020/consumer-reviews/ | ok, "8 of 12" + 1 featured | 39 (8) |
| kbb.com/cadillac/ct5/ | ok (no expert review; specs + news item on redesign) | 1 competitor + 1 equipment |
| consumerreports.org/cars/cadillac/ct5/2026/overview/ | partial: membership/paywall notice; only the free visible text was used | 3 press |
| cars.com/research/cadillac-ct5-2025/ | ok (Cars.com editors' "good & bad" summary + specs; undated) | 9 press + 11 equipment |
| autoguide.com/…/2025-cadillac-ct5-gets-a-new-face-new-technology-44607550 | ok (news, 2023-09) | 1 equipment |
| thecarconnection.com/cars/cadillac_ct5 | 403 | 0 |
| autoblog.com/cars/cadillac/ct5/2026 | 403 | 0 |
| cars.usnews.com/cars-trucks/cadillac/ct5 | timeout | 0 |
| cadillac.com/sedans/ct5 | 403 | 0 |
| news.gm.com 2025 CT5 release (…/2023/sep/0913-ct5.html) | 403 | 0 |
| cadillacforums.com/threads/25-ct5-purchase-dis-satisfaction.1148393/ | 307 redirect to tollbit.cadillacforums.com (paid bot gateway). Not followed | 0 |
| edmunds.com 2026 ES consumer reviews (seen in search) | known blocked, not fetched | 0 |

## Headline findings

### Genesis G80 (RG3)
1. **ride_handling:** owners praise it without exception (10 Likes, 0 negatives). In the AutoGuide twin test the G80 is the better cruiser, but the 540i (G30) is more agile and has better-weighted steering. Comfort favours the G80, dynamics favour BMW.
2. **overall_quality_ownership** is the main pain point:
   - towing incidents at about 4,000 and under 10,000 miles
   - repeated shop stays
   - parts and service delays of up to 5 months
   - dealer-network complaints, including "needs its own dealer network"
3. **adas_parking** is split:
   - Owners report Defects: a driver-attention alert that cannot be switched off, non-working emergency braking, erratic lane control.
   - Press credits the standard ADAS suite against BMW's extra-cost packages.
4. **interior_design_quality, exterior_design, audio_acoustics, space_practicality, equipment_value:**
   - AutoGuide picks the G80 over the 540i on interior, styling, Lexicon audio, rear legroom (38.7 vs 36.5 in) and price.
   - A former 5 Series owner also praises the roomier back seat (`competitor_advantage`).
5. **connectivity_app_digital and equipment_value:**
   - Early cars lacked wireless CarPlay and a wireless charging pad, and owners report CarPlay/Bluetooth bugs.
   - One MY2024 owner notes de-contenting: rear shades and soft-close doors removed.
   - Fuel economy (`range_charging_efficiency`) is mixed. The press notes the 3.5T AWD gets 21 mpg against 26 mpg for the 540i.

### Lexus ES (XZ10)
1. **hmi_infotainment** is the clear weak spot: 9 of 13 records are Difficult to Use and 2 are Defect.
   - Causes: the Remote Touch touchpad, an infotainment system "built for an engineer", non-tactile steering-wheel buttons, a navigation bug and a radio-preset bug.
   - Cars.com says the MY2022 12.3-in touchscreen fixed the main issue.
2. **range_charging_efficiency** (ES 300h 40–44 mpg) and smooth ride (**ride_handling**) are the top Likes.
3. **space_practicality** negatives:
   - tight ingress/egress and headroom
   - limited trunk opening
   - rear seats that do not fold (owner and KBB)
   - a single cupholder
4. **audio_acoustics** is mixed:
   - Quietness and the Mark Levinson system are praised.
   - Defects: wind noise that the dealer could not fix (2020 ES 350) and dead rear speakers/subwoofer (2022 ES 300h).
5. **seats_comfort and powertrain_performance:** owners and press want:
   - rear heated seats and rear climate controls
   - AWD with the V6 (only the ES 250 offers AWD)
   - The F Sport ride is harsher (press). One owner recommends the ES over the 5-Series on price and reliability (`competitor_advantage`; the 5 Series generation is not stated).

### Lexus ES (8th gen, MY2026+)
1. **No owner reviews yet.** Cars.com has 0 reviews and KBB shows one hidden review (2.0/5, comfort 1.0). This is a gap, not a finding.
2. Press criticises **powertrain_performance**: performance is tame, even in the ES 500e. **audio_acoustics:** the hybrid is noisy under hard acceleration.
3. Press praises **climate and hmi_infotainment:**
   - a physical HVAC bar and a roller volume dial
   - a crisper 14-in screen with a home button
   - These matter as a counterpoint to touch-only climate concepts.
4. **space_practicality:** rear legroom is 40.7 in (+1.5 in over XZ10) on a 116.1-in wheelbase. The Executive package adds rear recline, heating, ventilation and massage (F12).
5. **equipment_value:** KBB contrasts the sub-$50k EV ES with the BMW i5 and EQE in the high $60ks (`competitor_advantage`). **interior_design_quality:** the synthetic-suede steering wheel is called odd.

### Cadillac CT5 (MY2020+)
1. The owner sample is overwhelmingly positive: 79 of 94 tier-A records are Likes. Most praised are ride_handling, exterior_design and powertrain_performance (2.0T power, up to 36 mpg). Many of these reviews were written early in ownership (2020–2021).
2. **space_practicality** is the main criticism, from owners and press alike:
   - tight rear seat and rear headroom
   - "cozy" trunk of 11.9 cu ft
   - cramped interior
3. **interior_design_quality** is divided. Some owners praise the materials. Cars.com editors find them less upscale than rivals, and one owner reports smelly imitation leather.
4. **The 2025 refresh** brings a 33-in display, Google built-in and Super Cruise.
   - Cars.com lists the tech and Super Cruise as strengths (adas_parking, hmi_infotainment).
   - One 2025 owner finds the car "too hi-tech" and dislikes the 450-page manual, which is sold for $50.
5. **powertrain_performance:** owners like the 2.0T, but Consumer Reports says the powertrain "lacks polish" and Cars.com calls the base four's acceleration so-so. The only BMW comparison is against the 3 Series (owner cross-shopped it, CT5 judged better), so `comparison` is null.

## Coding conventions and caveats

- **Hybrids:** the schema has no HEV value. Non-plug-in hybrids (ES 300h, ES 350h) are coded `ICE`, and the statement mentions "hybrid". For 8th-gen ES press records that cover both hybrid and EV, `powertrain` is `unknown`. MotorWeek records are `BEV`.
- **Electrified G80:** stored as `model: "G80"` with `powertrain: "BEV"`.
- **feedback_type:** dislikes that are neither broken nor a feature request are coded `Difficult to Use` ("weak performance/dissatisfaction"). In press twin tests, categories the G80 loses are coded `Difficult to Use` + `bmw_advantage`.
- **rating:**
  - Owner reviews: null, because cars.com and KBB show only category sub-scores.
  - Press records: the KBB expert score (e.g. `4.7/5`).
- **model_year:**
  - Taken from the review text where stated.
  - Cars.com G80 and CT5 2020 pages are year-specific, so the page year is used there.
  - KBB pages, and the cars.com `lexus-es_350-2019` and `lexus-es_300h-2021` pages, mix model years. Unstated years are null.
  - KBB appears to pool consumer reviews per generation. The KBB ES 2019 and ES 2025 pages both report the same 70 reviews, the ES 2026 page reports 1, and the KBB CT5 2020 and current CT5 pages both report 12. So null-year KBB reviews are treated as current-generation. No review stating MY2018 or older was used. Misfiles still happen: a GV70 review sat on the G80 page and was excluded.
  - Residual risks:
    - Pooling on the cars.com `lexus-es_350-2019` page (125 reviews, including a 2022 ES 300h) is not verified, so its null-year reviews are assumed XZ10.
    - KBB G80 review R014 (driver-attention alert that cannot be disabled; no trim or year stated) cannot be confirmed as RG3 from its own text, but it supports the G80 adas_parking finding.
- **comparison:**
  - AutoGuide's G80 records compare against the **previous-generation 5 Series (G30, 2021 540i xDrive)**, not the G60.
  - The KBB G80 owner (R020) compares with an earlier 5 Series.
  - The ES owner (R027) names the "5-Series" without a generation.
  - Treat these as brand-level signals.
- **Excluded reviews:**
  - **G80:** cars.com 2021 "Purchased" (describes an SUV). cars.com 2021 "super sleek" (dated Aug 2020, before RG3 US sales; flagged as suspicious). cars.com 2022 "GREAT CARS!" (two weeks of ownership, no car-specific content). KBB "Brand New 2025 GV70" (wrong model). Forum posts by MHT and ctrcbob (workarounds only).
  - **ES:** KBB "Gmoney" and "Simar" (sweepstakes entries). Thin reviews: "Melody22", "Love Lexus Vehicles" (dealer trade-in dispute), "Mary".
  - **CT5:** cars.com "WORST PURCHASE EVER IT IS A 2009" (appears to describe another car). The "Fairfields…" after-sales rant (garbled). "A nice sized SUV…" (hands-free hatch, so not a CT5). "I have only had it one day". KBB "TC Bla" (collision repair only).
- **Conflicts in sources:**
  - KBB ES trunk: 16.7 vs 13.9 cu ft (2025), and 17.4 / 13.3 / 18.2 cu ft (2026).
  - CT5 Super Cruise: standard per the cars.com MY2025 page, "available" per AutoGuide's 2023 launch news.
  - KBB eG80 Level 2 time: 7 h 22 min vs 9 h.
  - All are noted in the equipment `notes`.
- **Equipment:** every model has a row for each of F01–F20. Many are `unknown` because manufacturer pages were 403 (cadillac.com, news.gm.com) or text-poor (genesis.com, pressroom.lexus.com).
  - Most equipment is tier B, from KBB, Cars.com and MotorWeek.
  - Only the Genesis rows are tier C (genesis.com, MY2027 page, which also shows AWD standard and Bang & Olufsen audio replacing Lexicon).
- **Silence is never coded as absence:** `not_available` is used only where a source states it (no moonroof on the Electrified G80, no adaptive dampers on the 8th-gen ES) or where no BEV exists in the lineup (F15/F16 for ES XZ10 and CT5).
- **Owner sample size:** small per model (20–26 reviews). Cars.com and KBB samples skew toward early-ownership enthusiasm (CT5, ES 300h) and toward reliability complaints (G80). Compare theme shares, not counts.
- **WebFetch output is a model-written summary.** Records are built only from per-review listings. Paraphrases follow the summary, and short quotes are those the summary placed in quotation marks.
