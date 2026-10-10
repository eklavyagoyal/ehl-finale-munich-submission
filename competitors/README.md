# Competitor research — BMW 5 Series (G60, China: G68)

Competitor vehicles for the 5 Series and what their customers and the press say about them, structured so it can be compared with BMW's own G60 feedback.

| Market | BMW baseline | Competitor feedback sources |
| --- | --- | --- |
| EU | G60 feedback (thin, mostly GB/SE/DK) + DE option list | owner reviews, owner forums, press tests |
| US | G60 feedback (rich, Sources A–D) | owner reviews, owner forums, press tests |
| CN | **G68** (long wheelbase) — no BMW feedback, so G68 owner reviews are collected from the web as baseline | Autohome / Dongchedi / Sohu / Yiche owner reviews, press |

## How comparability works

1. **Same theme axis.** [`themes.json`](themes.json) defines 18 coarse themes. Every BMW VFC level2 topic is mapped to one theme ([`tools/build_themes.py`](tools/build_themes.py)), and every competitor finding is tagged with a theme from the same list.
2. **Same feedback types** as BMW: `Likes`, `Wants`, `Difficult to Use`, `Defect`.
3. **One topic per record.** Like the BMW files (one row per classification), a review that covers three topics becomes three records sharing one `review_ref`. Count unique `review_ref`s, not records.
4. **Compare shares, not counts.** Competitor owner-review volume is far smaller than BMW's. Compare the sentiment mix per theme. The closest BMW baseline for competitor owner reviews is **BMW Source A** (owner reviews); Sources B–D (dealer/survey channels) have no competitor equivalent.
5. **Same generation.** All model years of the current generation count; the generation code is on every record.

## Files

| File | Content |
| --- | --- |
| `themes.json` | Theme taxonomy, VFC → theme mapping, feedback types, evidence tiers |
| `raw/<agent>.jsonl` | Records from one research agent (one JSON object per line) |
| `raw/<agent>.log.md` | What that agent searched, fetched, found and could not access |
| `tools/` | Scripts (theme build, merge, validation) |

## Record schema (`raw/*.jsonl`)

### `kind: "feedback"`: one statement about one theme

| Field | Type | Notes |
| --- | --- | --- |
| `record_id` | str | `<agent>-F0001` |
| `review_ref` | str | `<agent>-R001`: groups records from the same review/post |
| `kind` | `"feedback"` | |
| `market` | `EU` \| `US` \| `CN` | |
| `country` | ISO-2 | country of the source/reviewer if known (`GB`, `DE`, `US`, `CN`, …) |
| `brand`, `model`, `generation` | str | e.g. `Mercedes-Benz`, `E-Class`, `W214` |
| `model_year` | str \| null | |
| `powertrain` | `ICE` \| `PHEV` \| `BEV` \| `unknown` | |
| `source_type` | `owner_review` \| `owner_forum` \| `owner_survey` \| `press_review` | |
| `source_name` | str | e.g. `cars.com`, `Autohome`, `Car and Driver` |
| `url` | str | **a page the agent fetched itself** |
| `published` | `YYYY-MM` \| `YYYY` \| null | |
| `feedback_type` | `Likes` \| `Wants` \| `Difficult to Use` \| `Defect` | `Wants` = request/missing feature; `Difficult to Use` = usability pain or weak performance; `Defect` = something broken |
| `theme` | theme id | from `themes.json` |
| `vfc_level2` | str \| null | best-matching BMW VFC level2 topic (keys of `vfc_level2_to_theme`), if one fits well |
| `comparison` | `competitor_advantage` \| `bmw_advantage` \| `parity` \| null | only when the source explicitly compares with BMW / the 5 Series |
| `statement` | str | English paraphrase, 1–2 sentences, one topic, e.g. "Owner states the air suspension makes the ride very smooth on highways." |
| `quote` | str \| null | optional original-language excerpt, **under 15 words** |
| `language` | `en` \| `de` \| `zh` \| … | language of the source |
| `rating` | str \| null | e.g. `4/5` if the review carries one |
| `evidence_tier` | `A` \| `B` | A = customer voice, B = press |

### `kind: "equipment"`: one customer-facing feature of one vehicle in one market

`record_id` (`<agent>-E0001`), `kind`, `market`, `brand`, `model`, `generation`, `trim_scope` (e.g. `entry trim`, `all trims`, `i5 eDrive40`), `feature`, `theme`, `availability` (`standard` \| `optional` \| `not_available` \| `unknown`), `value` (e.g. `"270 kW DC peak"`), `source_type` (`manufacturer` \| `press_review`), `url`, `as_of` (`YYYY-MM`), `evidence_tier` (`C` \| `B`), `notes`.

Use these fixed `feature` ids so vehicles line up (value text free-form):

| id | feature | theme |
| --- | --- | --- |
| `F01_display_layout` | central display(s): size, layout, passenger screen | hmi_infotainment |
| `F02_hud` | head-up display | hmi_infotainment |
| `F03_physical_climate_controls` | physical buttons/knobs for climate (yes/no) | climate |
| `F04_voice_assistant` | natural-language / LLM voice assistant | hmi_infotainment |
| `F05_wireless_carplay_aa` | wireless Apple CarPlay / Android Auto (CN: Huawei/Carlife equivalents) | connectivity_app_digital |
| `F06_ota_updates` | over-the-air software updates (scope) | connectivity_app_digital |
| `F07_digital_key` | phone-as-key / digital key (UWB/NFC) | access_locking |
| `F08_hands_free_highway` | hands-free / navigate-on-autopilot highway assist (speed limit, region) | adas_parking |
| `F09_automated_parking` | automated / remote parking | adas_parking |
| `F10_ventilated_front_seats` | ventilated front seats | seats_comfort |
| `F11_massage_seats` | massage seats | seats_comfort |
| `F12_rear_comfort` | rear seat comfort (heated/ventilated/recline/rear screens/rear controls) | seats_comfort |
| `F13_air_suspension` | air suspension | ride_handling |
| `F14_rear_wheel_steering` | rear-wheel steering | ride_handling |
| `F15_bev_range` | BEV range, best variant (state cycle: WLTP/EPA/CLTC) | range_charging_efficiency |
| `F16_dc_charging` | BEV DC peak kW, 10–80 % time, 400/800 V | range_charging_efficiency |
| `F17_rear_space` | wheelbase / rear legroom (mm) | space_practicality |
| `F18_trunk_volume` | trunk volume (l), frunk | space_practicality |
| `F19_premium_audio` | premium audio brand / speakers | audio_acoustics |
| `F20_panoramic_roof` | panoramic/glass roof | interior_design_quality |

### `kind: "competitor"`: why a vehicle is in the competitor set

`record_id` (`<agent>-C001`), `kind`, `market`, `brand`, `model`, `generation`, `powertrains`, `launched`, `rationale`, `next_generation` (announced successor/facelift, or null), `next_generation_evidence_tier` (`D`), `url`.

### `kind: "outlook"`: what is coming in the next 3–5 years (forward-looking)

`record_id` (`<agent>-O001`), `kind`, `markets`, `brand`, `model`, `current_generation`, `announcement` (successor / facelift / new model and expected timing), `customer_facing_changes` (list of short strings), `theme` (main theme affected), `url`, `published`, `evidence_tier` (`D`), `confidence` (`announced` \| `reported` \| `rumoured`).

### `kind: "bmw_mention"`: a BMW G60 verbatim that names a competitor (labels only, no text)

`record_id`, `kind`, `bmw_feedback_id`, `source` (A–D), `country`, `engine_type`, `competitor_brand`, `competitor_model`, `relation` (`competitor_advantage` \| `bmw_advantage` \| `parity` \| `previous_car` \| `cross_shopped` \| `mention_only`), `theme`, `feedback_type` (about the BMW), `aspect` (label of at most 8 words).

## Rules for collection

- Every record cites a URL that was actually fetched. Search snippets are not records. Zero results is a valid outcome; it gets logged.
- No CAPTCHA, login or bot-block workarounds. Known blocked: Edmunds (403), Reddit, What Car (paywall).
- Store paraphrases, not copied review text; quotes stay under 15 words.
- BMW verbatim text from `data/` never goes into committed files, only IDs and labels.
