# Agent `us_tesla_audi`: US market, Tesla Model S / Model 3 and Audi A6 family

Output: `competitors/raw/us_tesla_audi.jsonl` (341 records: 4 competitor, 257 feedback, 80 equipment). The file passes a schema check covering theme ids, feedback types, the `vfc_level2` key→theme match, id formats, evidence tiers, and a rule that every URL appears in the list of pages fetched in this task.

Budget used: 41 WebFetch calls and 12 WebSearch calls. Two of the searches errored on blocked domains.

## Models covered

| Model | Generation label used | Why this generation | Powertrain |
| --- | --- | --- | --- |
| Tesla Model 3 | `Highland` | US MY2024+ refresh. The cars.com 2024/2025 pages and the press tests describe refresh features: no stalks, rear screen, touchscreen gear selector. | BEV |
| Tesla Model S | `Model S (2021 refresh)` | MY2021+ refresh: yoke, 17-in screen, Plaid. Only the MY2022/2023 cars.com pages were used in full. On the 2021 page and the KBB page, a review was kept only if it shows a refresh cue (yoke / "jet-style" wheel, Plaid). | BEV |
| Audi A6 Sportback e-tron (incl. S6 Sportback e-tron) | `A6 e-tron (PPE, MY2025+)` | The current US BEV A6. The US gets only the Sportback body; there is no Avant. No pages fetched print an internal code, so the label is descriptive. | BEV |
| Audi A6 (sedan) | `C9` | The all-new MY2026 sedan replaces the C8 sedan in the US. cars.com calls it "Redesigned for 2026" and KBB "all-new generation". The code "C9 / ninth generation" appears in Audi USA and AudiWorld titles seen in search results; the Audi media page itself rendered empty. | ICE (3.0 V6, 362 hp, quattro; only US powertrain) |

**Not covered:** the C8 A6 sedan. It is no longer the current US sedan (C8 continues only as the A6 allroad and RS 6 Avant), so under rule 7 it is out of scope. No C9 owner reviews exist yet: cars.com and KBB both show 0.

## Sources (per URL)

| # | URL | Status | Records (unique reviews) |
| --- | --- | --- | --- |
| 1 | https://www.cars.com/research/tesla-model_3-2024/consumer-reviews/ | ok, 9 reviews | 39 feedback (8 reviews). 1 review skipped: it is about dealer financing of an Acura. |
| 2 | https://www.cars.com/research/tesla-model_3-2025/consumer-reviews/ | ok, 5 reviews | 31 feedback (3 reviews). 2 skipped as model-year inconsistent ("driven for three years" and "2 years in" on a MY2025 page, so likely pre-Highland). |
| 3 | https://www.cars.com/research/tesla-model_3-2026/consumer-reviews/ | empty (0 reviews) | 0 |
| 4 | https://www.kbb.com/tesla/model-3/2024/consumer-reviews/ | ok, but mixed model years (2019/2020 cars on a "2024" page) | 0. None of the 10 visible reviews could be tied to a Highland car. |
| 5 | https://teslamotorsclub.com/tmc/threads/is-the-new-model-3-highland-holding-up-well.338685/ | 403 | 0 |
| 6 | https://www.caranddriver.com/tesla/model-3-2024 | blocked for the fetcher | 0 |
| 7 | https://www.thedrive.com/car-reviews/2024-tesla-model-3-review | ok | 19 feedback, 20 equipment |
| 8 | https://insideevs.com/reviews/719484/tesla-model3-long-range-review/ | 502, twice | 0 |
| 9 | https://www.cars.com/research/tesla-model_3-2024/ (expert review summary) | ok | 9 feedback, 1 competitor |
| 10 | https://www.tesla.com/model3 | 403 | 0. All Tesla equipment is therefore press-sourced, tier B. |
| 11 | https://www.greencarreports.com/news/1144345_2024-tesla-model-3-highland-ev-test-drive-review | 403 | 0 |
| 12 | https://www.i4talk.com/threads/tesla-model-3-highland-build-quality-review.10357/ | redirect to tollbit (paid bot access); not followed | 0 |
| 13 | https://www.teslaownersonline.com/threads/the-range-of-model-3-highland-lr.32465/ | redirect to tollbit; not followed | 0 |
| 14 | https://www.cars.com/research/tesla-model_s-2022/consumer-reviews/ | ok, 7 reviews | 35 feedback (7 reviews) |
| 15 | https://www.cars.com/research/tesla-model_s-2023/consumer-reviews/ | ok, 4 reviews | 15 feedback (4 reviews) |
| 16 | https://www.cars.com/research/tesla-model_s-2024/consumer-reviews/ | empty (0 reviews) | 0 |
| 17 | https://www.cars.com/research/tesla-model_s-2021/consumer-reviews/ | ok, 3 reviews | 3 feedback (1 review with a yoke cue). 2 skipped: no refresh cue. |
| 18 | https://www.clublexus.com/forums/ev-chat/1045765-my-review-of-bmw-i5-vs-tesla-model-s.html | 403 | 0. This i5 vs Model S owner thread would have been the best comparison source. |
| 19 | https://www.autoblog.com/cars/tesla/model-s/2025 | 403 | 0 |
| 20 | https://www.consumerreports.org/cars/tesla/model-s/2025/overview/ | ok (free summary; scores are paywalled) | 7 feedback |
| 21 | https://www.kbb.com/tesla/model-s/2025/ | ok | 13 feedback, 20 equipment, 1 competitor |
| 22 | https://www.kbb.com/tesla/model-s/2024/consumer-reviews/ | ok, 10 visible, mixed model years | 15 feedback (2 reviews: Plaid with yoke; Plaid bought new in 2021). 8 skipped: pre-refresh or no cue. |
| 23 | https://www.thedrive.com/new-cars/41492/2022-tesla-model-s-plaid-review-a-new-1020-hp-chapter-in-american-luxury | ok | 14 feedback |
| 24 | https://www.cars.com/research/audi-a6_e_tron-2025/consumer-reviews/ | ok, 1 review | 6 feedback (1 review) |
| 25 | https://www.cars.com/articles/2026-audi-a6-s6-sportback-e-tron-review-electric-maturity-512401/ | ok | 10 feedback, 15 equipment, 1 competitor |
| 26 | https://www.kbb.com/audi/a6-sportback-e-tron/2025/consumer-reviews/ | empty (0 reviews) | 0 |
| 27 | https://www.e-tronforum.com/threads/honest-opinion-of-a6-e-tron.10319/ | redirect to tollbit; not followed | 0 |
| 28 | https://www.thedrive.com/car-reviews/2025-audi-a6-e-tron-rwd-sportback-review | ok | 11 feedback, 1 equipment |
| 29 | https://roadethos.com/car-buying/2027-audi-a6-e-tron-vs-bmw-i5 | 403 | 0 |
| 30 | https://www.cars.com/research/audi-a6-2026/ (C9 expert review + specs) | ok; 0 consumer reviews | 8 feedback, 14 equipment, 1 competitor |
| 31 | https://media.audiusa.com/releases/645 | empty (JS page, only logo) | 0. No manufacturer (tier C) equipment for Audi either. |
| 32 | https://www.cars.com/research/audi-s6_e_tron-2025/consumer-reviews/ | empty (0 reviews) | 0 |
| 33 | https://www.kbb.com/audi/a6/2026/ (pre-drive expert preview) | ok; 0 consumer reviews | 3 feedback, 6 equipment |
| 34 | https://api.nhtsa.gov/products/vehicle/models?modelYear=2025&make=audi&issueType=c | ok (model-name lookup) | 0 |
| 35 | https://api.nhtsa.gov/complaints/complaintsByVehicle?make=AUDI&model=A6%20E-TRON&modelYear=2025 | ok, 2 complaints | 3 feedback (2 complaints) |
| 36 | https://api.nhtsa.gov/complaints/complaintsByVehicle?make=AUDI&model=S6%20SPORTBACK%20E-TRON&modelYear=2025 | ok, 1 complaint | 1 feedback |
| 37 | https://api.nhtsa.gov/complaints/complaintsByVehicle?make=AUDI&model=A6%20SEDAN&modelYear=2026 | 400 | 0 |
| 38 | https://api.nhtsa.gov/complaints/complaintsByVehicle?make=TESLA&model=MODEL%20S&modelYear=2024 | 400 | 0 |
| 39 | https://www.kbb.com/reviews/driving-the-2025-audi-a6-sportback-e-tron/ | ok | 15 feedback, 4 equipment |

NHTSA complaints are recorded as `source_type: owner_survey`, `source_name: NHTSA complaints`, tier A, matching the `us_mercedes` agent.

**Leads not used:**
- Fleetnews UK twin test, A6 e-tron Avant vs i5 Touring (https://www.fleetnews.co.uk/features/twin-test-audi-a6-vs-bmw-i5). It is UK-market and uses estate bodies, so it is relevant to an EU agent, not here.
- Autocar's Model S Plaid vs EQS vs i5 M60 test (UK).

## Headline findings

### Tesla Model 3 (Highland): 11 owner reviews, 2 press reviews
1. **range_charging_efficiency.** Strongest positive. Owners and press praise cheap home charging, range (341 mi EPA LR AWD) and Supercharging ("plug in and walk away", 250 kW). One owner reports phantom battery drain.
2. **hmi_infotainment.** The stalkless turn-signal buttons are the most frequent complaint (3 owners, 2 press). Two owners say they adapted easily. Press criticize the touchscreen gear selector and small look-alike icons, and one owner wants a HUD.
3. **ride_handling.** Split view. Owners and cars.com praise the smoother, quieter refreshed ride. The Drive finds it brittle and less composed than a BMW i4 (bmw_advantage), with artificial steering. A Minnesota owner reports poor snow and rough-road behaviour.
4. **interior_design_quality / overall_quality_ownership.** Polarised: "improved materials, no rattles" vs "cheap interior, rattly, door rattle, thin paint". The Drive says the BMW i4 has the nicer interior (bmw_advantage).
5. **adas_parking / connectivity.** Owners like the self-driving features and OTA updates. Press report FSD errors and say Super Cruise is better. One owner reports an FSD incident.

### Tesla Model S (2021 refresh): 14 owner reviews, 3 press reviews
1. **powertrain_performance.** Near-universal praise (16 Likes). The Drive says the Plaid's straight-line speed is in a different class from the BMW M5 (competitor_advantage).
2. **interior_design_quality.** Yoke and cabin are the main negatives. Press (CR, KBB, The Drive) and some owners find the yoke awkward for parking and multi-point turns, though two owners like it. KBB, CR and The Drive call the cabin plain or sparse versus legacy-brand rivals.
3. **overall_quality_ownership.** Build quality is a recurring Defect theme: >10 delivery defects, a rear-seat rattle, a dead battery on delivery. KBB cites panel gaps, paint flaws and long service waits. Other owners report no issues.
4. **range_charging_efficiency.** Range (402 mi EPA) and Supercharger access are praised throughout. KBB and CR say CarPlay/Android Auto is not supported (logged as Wants).
5. **space_practicality.** The hatchback and cargo space are liked. KBB notes rear legroom of 35.5 in is barely more than the Model 3. Tyre wear (camber) appears in 2 KBB owner reviews.

### Audi A6 Sportback e-tron (PPE): 1 owner review, 3 NHTSA complaints, 3 press reviews
1. **range_charging_efficiency.** KBB says it beats BMW and Mercedes rivals on range "quite easily" (up to 392 mi), so competitor_advantage vs i5. The car has 800 V and 10-80% in 21 min. The Drive measured only about 292 mi real-world in its test.
2. **space_practicality.** KBB gives 26 cu ft of cargo vs 17.3 cu ft for the BMW i5 (competitor_advantage). The hatchback is praised by The Drive and the owner.
3. **hmi_infotainment.** MMI is called clear and intuitive (cars.com), and voice control handles 800+ commands. Press dislike that almost no physical controls remain, and The Drive calls the screens generic.
4. **ride_handling.** The air-suspension ride is praised by all three press reviews. Steering is called light and digital (cars.com, The Drive).
5. **Defects (NHTSA).** Rear door and phone-key unlock failure (software fix pending), unexpected braking-like lurch with a driving-dynamics warning, and an S6 electrical failure with a fire-risk warning and no gear engagement.

### Audi A6 (C9, ICE, MY2026): 2 press sources, no owner data yet
1. **powertrain_performance.** The 362-hp V6 and smooth DCT are praised, but cars.com finds it not much fun.
2. **ride_handling.** Air suspension is praised. Sport Plus and rear-wheel steering add little.
3. **Comparisons vs G60 (KBB preview).** The BMW 540i xDrive wins on fuel economy (28 vs 23 mpg combined). The 5 Series and E-Class have slightly larger trunks. Both are bmw_advantage.
4. **interior_design_quality / equipment_value.** Gloss-black overuse, "cheap in places", and a roughly $6k price rise, partly offset by more standard equipment.

## Caveats
- **Small samples.** cars.com and KBB owner reviews are few, short and partly generic ("praises comfort"). Records are built from WebFetch summaries, so statements are paraphrases of summaries, not of the raw review text. Quotes are review titles only; none are taken from review bodies.
- **Model-year labels.** cars.com assigns reviews to model-year pages, and at least 2 Model 3 reviews contradicted their page's MY and were skipped. KBB pages mix model years, so only reviews with explicit refresh cues were kept. KBB R026 has no model year (null), but the yoke and Plaid prove it is a refresh car.
- **Owner forums inaccessible.** TMC (403), ClubLexus (403), and the VerticalScope forums (i4talk, teslaownersonline, e-tronforum and likely AudiWorld) redirect to tollbit, a paid bot gate, which was not followed. Reddit and Edmunds were not attempted (known blocked). As a result there are no forum-sourced records, and Audi owner voice is very thin (1 review plus 3 NHTSA complaints).
- **`comparison` field.** It names other BMW models in some records: i4 (Model 3, The Drive), i3 (Model 3 owner), M5 (Model S, The Drive), 540i xDrive / 5 Series (A6 C9, KBB), i5 (A6 e-tron, KBB). The BMW model is always named in the statement. Filter on the statement if only 5 Series / i5 comparisons are wanted.
- **Model S availability.** KBB's 2025 Model S page carries a news item (2026-01-29) saying Tesla will end Model S/X production the next quarter. Check whether the Model S is still sold in the US in late 2026. This is recorded in `next_generation` (tier D).
- **Equipment.** All of it is press-sourced (tier B), because tesla.com returned 403 and media.audiusa.com rendered empty. Many features are `unknown`. Some press figures conflict: A6 e-tron cargo (KBB 26/39.9 cu ft vs The Drive 29.95/39.87 cu ft), C9 trunk (13.5 vs 17.8 cu ft on the same KBB page), and Model S range (402 vs 410 mi). Unit conversions to l/mm were done by the agent.
- **KBB 2026 A6 is a pre-drive preview** (updated 2025-05), so only its explicit comparisons and one design judgement were recorded.
- **Classification choices.** Turn-signal buttons are mapped to `hmi_infotainment` / "Multi-function steering wheel operation". The yoke shape is mapped to `interior_design_quality` / "Steering wheel". Price/value complaints are typed `Difficult to Use`, because there is no "Dislike" type.
