# us_mercedes: research log

Agent `us_mercedes`, market US, collected 2026-10-10.

## Models covered

| Model | Generation | US model years | Powertrains |
| --- | --- | --- | --- |
| Mercedes-Benz E-Class sedan | W214 | MY2024 to MY2027 (MBUSA now shows MY2027) | ICE 48V mild hybrid (E 350, E 450), PHEV (AMG E 53 Hybrid) |
| Mercedes-Benz EQE sedan | V295 | MY2023 to MY2026 (MBUSA shows a 2026 EQE 320+) | BEV |

## Record counts

| Model | competitor | outlook | equipment | owner_review (A) | NHTSA complaints (A, `owner_survey`) | press_review (B) |
| --- | --- | --- | --- | --- | --- | --- |
| E-Class W214 | 1 | 1 | 18 (F15/F16 skipped as BEV-only) | 20 records / 2 reviews | 24 records / 21 complaints | 32 records / 4 articles |
| EQE V295 | 1 | 1 | 20 | 16 records / 3 reviews | 52 records / 49 complaint refs (51 filings) | 45 records / 4 articles |

Total: 189 feedback, 38 equipment, 2 competitor and 2 outlook records.

## Sources

Budget used: 43 WebFetch and 10 WebSearch calls (2 searches errored on blocked domains). `curl` was used only on the NHTSA API, to list model names and download the raw complaint JSON for filtering and checking (scratchpad). Every record cites a URL fetched with WebFetch.

### Owner reviews and forums

| URL | Status | Records |
| --- | --- | --- |
| https://www.cars.com/research/mercedes_benz-e_class-2025/consumer-reviews/ | ok, 1 review | 3 (R002) |
| https://www.cars.com/research/mercedes_benz-e_class-2024/consumer-reviews/ | empty (0 reviews) | 0 |
| https://www.cars.com/research/mercedes_benz-e_class-2026/consumer-reviews/ | empty (0 reviews) | 0 |
| https://www.cars.com/research/mercedes_benz-e_350-2024/consumer-reviews/ | redirected to the Mercedes make hub, no reviews | 0 |
| https://www.kbb.com/mercedes-benz/e-class/2025/consumer-reviews/ | ok, 1 review (Mahony, MY2025 E 350, 3/5) | 17 (R001) |
| https://www.kbb.com/mercedes-benz/e-class/2024/consumer-reviews/ | ok, but the same single MY2025 review | 0 (duplicate) |
| https://www.kbb.com/mercedes-benz/e-class/2026/consumer-reviews/ | ok, but the same single review again | 0 (duplicate) |
| https://www.cars.com/research/mercedes_benz-eqe_350_plus-2023/consumer-reviews/ | ok, 1 review | 4 (R028) |
| https://www.cars.com/research/mercedes_benz-eqe_350-2023/consumer-reviews/ | ok, 1 review | 9 (R029) |
| https://www.cars.com/research/mercedes_benz-eqe_500-2023/consumer-reviews/ | ok, 2 reviews; one is explicitly the EQE SUV and was excluded | 3 (R030) |
| https://www.kbb.com/mercedes-benz/mercedes-eq-eqe/2023/consumer-reviews/ | empty (0 reviews) | 0 |
| https://mbworld.org/forums/e-class-w214/ | 403 | 0 |
| https://www.truedelta.com/Mercedes-Benz-E-Class/pros-and-cons-O65680 | 403 | 0 |
| https://www.mbeqclub.com/threads/2023-mercedes-eqe-vs-2024-bmw-i5.2802/ | 307 redirect to tollbit.mbeqclub.com (paid bot access); not followed | 0 |
| https://www.cargurus.com/Cars/2024-Mercedes-Benz-E-Class-Reviews-c32825 | 406 | 0 |

Not tried, as instructed: Edmunds (403), Reddit, What Car. caranddriver.com, motortrend.com and cnet.com are refused by the search tool for this user agent.

### NHTSA complaints (api.nhtsa.gov, `complaintsByVehicle`)

| Bucket | Status | Kept / total | Records |
| --- | --- | --- | --- |
| `model=E-CLASS&modelYear=2024` | ok | 11 / 25 | 13 (R003 to R013) |
| `model=E 350&modelYear=2025` | ok | 2 / 2 | 2 |
| `model=E 350 4MATIC&modelYear=2025` | ok | 3 / 3 | 4 |
| `model=E-CLASS ICE&modelYear=2026` | ok | 5 / 6 | 5 |
| `model=EQE&modelYear=2024` | ok | 15 / 20 | 17 |
| `model=EQE&modelYear=2023` | ok | 32 filings (30 refs) / 40 | 31 |
| `model=EQE 350+&modelYear=2025` | ok | 2 / 2 | 2 |
| `model=EQE 350 4MATIC&modelYear=2025` | ok | 2 / 2 | 2 |

Excluded entries:

- **E-CLASS 2024 bucket:** 11 EQB complaints (the bucket is fuzzy). Two EQE 500 complaints were moved to the EQE. ODI 11610129 was dropped: a rusted subframe at about 120,000 miles on a 2024 car is implausible.
- **E-CLASS ICE 2026:** ODI 11746559 dropped because it is an E 450 All-Terrain wagon.
- **EQE 2024:** dropped four entries whose product field is an EQE SUV (11766723, 11706004, 11695472, 11710929) and ODI 11544857 (VIN mismatch, not product feedback).
- **EQE 2023:**
  - Dropped 11742216, 11742218, 11731586 and 11590871, because their narratives say SUV.
  - Dropped 11709572 and 11614862, whose product field is an EQE SUV.
  - Dropped 11596511 (empty narrative) and 11571649 (a loaner fire, not the complainant's car).
- **EQE 320+ 2026:** one complaint, not used. The 2026 EQE 320+ is sold as both sedan and SUV, so the body style is unclear.

### Press reviews

| URL | Status | Records |
| --- | --- | --- |
| https://www.caranddriver.com/mercedes-benz/e-class-2025 | blocked ("unable to fetch") | 0 |
| https://www.autoblog.com/features/bmw-540i-vs-mercedes-benz-e450 | 403 | 0 |
| https://autos.yahoo.com/new-vehicles-and-reviews/articles/bmw-540i-vs-mercedes-benz-163100204.html | ok (Autoblog syndicated on Yahoo; 2027 E450 vs 540i, 2026-08) | 15 (R024) + 2 equipment |
| https://autos.yahoo.com/tested-2024-bmw-540i-xdrive-130000225.html | ok (Car and Driver syndicated; 540i test with the E450 as foil, 2024-09) | 3 (R025) |
| https://www.kbb.com/comparison/bmw-5-series-vs-mercedes-benz-e-class/ | ok (2025-03) | 7 (R026) |
| https://www.cars.com/articles/2024-mercedes-benz-e-class-review-luxury-always-changes-483371/ | ok (2024-05) | 7 (R027) + 1 equipment |
| https://www.kbb.com/car-news/2024-mercedes-benz-e-class-most-personal-mercedes-ever | ok, pre-launch and not US-specific | 0 (used in notes only) |
| https://www.jdpower.com/cars/new-car-previews/2024-mercedes-benz-e-class-preview | 403 | 0 |
| https://www.cars.com/articles/2023-mercedes-eq-eqe-sedan-review-smaller-size-same-issues-457269/ | ok (2022-09, EQE 350 4MATIC) | 10 (R080) |
| https://www.autotrader.ca/editorial/20240311/2024-bmw-i5-m60-vs-mercedes-amg-eqe-comparison-test/ | ok (CA, AMG EQE vs i5 M60) | 13 (R081) |
| https://www.auto123.com/en/car-reviews/bmw-i5-mercedes-benz-eqe-comparison/72245/ | ok (CA, AMG EQE vs i5 M60 xDrive) | 10 (R082) |
| https://www.kbb.com/mercedes-benz/mercedes-eq-eqe/ | ok (KBB expert review, MY2025, 2025-01) | 12 (R083) + 20 equipment |
| https://insideevs.com/news/810584/2027-mercedes-benz-eqe-discontinued-us/ | 502, twice | 0 |
| https://mercedesblog.com/the-future-electric-mercedes-e-class-arrives-in-2027-and-replaces-the-eqe/ | ok (2025-11) | 2 outlook |

### Manufacturer and spec pages

| URL | Status | Records |
| --- | --- | --- |
| https://www.mbusa.com/en/vehicles/class/e-class/sedan | ok (MY2027 prices and features, truncated) | C001 + 9 equipment |
| https://www.mbusa.com/en/vehicles/model/e-class/sedan/e450w4 | ok, but no feature data | 0 |
| https://www.mbusa.com/en/vehicles/class/eqe/sedan | ok (2026 EQE sedan: EQE 320+, 96 kWh, 308 mi) | C002 |
| https://www.kbb.com/mercedes-benz/e-class/ | ok (MY2027 spec listing) | 5 equipment |
| https://media.mbusa.com/releases/release-d1fddb0969e53d2029cfa36ecb060390-2024-e-class-sedan-quick-reference-guide | 404 | 0 |

## Headline findings

### E-Class (W214)

1. **hmi_infotainment, Defect.** Screen blackouts are the most frequent NHTSA complaint for MY2024 and MY2025: 8 of 21 complaints report the instrument cluster, central or passenger screen going black or rebooting while driving. Some persist after the 2026 recall software update (26V281 is cited). An owner also finds the touch-sensitive steering-wheel controls too sensitive.
2. **ride_handling, competitor advantage.** The press consistently gives the E-Class the ride-comfort edge over the 5 Series:
   - Autoblog praises the AIRMATIC air suspension.
   - Car and Driver says its adaptive dampers soften more than the BMW's, and that the 540i feels heavier and less airy.
   - Cars.com also praises the air suspension.
   - KBB calls driving feel a matter of taste (parity).
3. **space_practicality and range_charging_efficiency, BMW advantage.**
   - Trunk: 12.7 vs 18.4 cu ft (Autoblog).
   - Rear head- and legroom are lower (KBB).
   - Fuel economy is lower (E450 25 vs 540i 28 mpg combined; E 350 28 vs 530i 31).
   - The KBB owner complains of tight rear foot room and hard entry and exit, and wants a thigh extension.
4. **interior_design_quality and hmi_infotainment.**
   - The E-Class wins on materials, styling and tech showpieces: the Superscreen passenger display and Burmester 4D (Autoblog, KBB).
   - The BMW is credited for keeping a physical rotary controller.
   - Cars.com warns the screen-heavy cockpit may put off traditional buyers.
5. **adas_parking and equipment_value.**
   - Owner and NHTSA reports cover phantom braking from adaptive cruise and automatic emergency braking, lane-keeping that will not switch off, and a weak lane-departure warning.
   - On price, the E450 is $73,700 vs $67,700 for the 540i, options add up quickly, and the powertrain warranty is shorter (4 yr/50k vs 6 yr/70k, per KBB).

### EQE (V295)

1. **powertrain_performance and adas_parking, Defect.** NHTSA complaints are dominated by three things:
   - unintended acceleration, often at parking speed;
   - loss of propulsion or stalling (recall 24V372 is mentioned);
   - phantom automatic emergency braking.

   Together these make up 26 of the 49 complaint refs (16 drivetrain, 10 ADAS). The channel is safety-skewed by design.
2. **interior_design_quality and ride_handling, Defect.**
   - Four sedan complaints (MY2023 to MY2024) report panoramic roofs shattering spontaneously. The E-Class has one at MY2026.
   - Five refs report Pirelli run-flat blowouts or bubbles on 20 and 21-inch wheels.
   - Several report brake fade or no braking in regen or one-pedal situations.
3. **Press vs i5: mostly BMW advantage.** The BMW leads on:
   - rear headroom and space (AutoTrader.ca);
   - trunk (11 vs 17.3 cu ft, KBB);
   - DC charging (170 vs 205 kW peak) and efficiency;
   - styling ("melting", "too conservative");
   - ease of use (BMW system easier than MBUX);
   - value (AMG EQE C$121k vs i5 M60 C$95k to 97.5k).

   The EQE wins on EQE 350+ range (308 vs 295 mi, KBB), interior ambience (Auto123) and raw AMG power. Ride quality is split: Auto123 calls the EQE supple, AutoTrader.ca calls it always firm.
4. **range_charging_efficiency, owner voice.** Owners report about 360 mi of real-world range (two reviews) and like the comfort and speed. One reports repeated Electrify America connection failures and 45 to 50 min charging. One reports a three-week electrical shop stay.
5. **Packaging and HMI, press.**
   - Cars.com criticises the slit-like rear window, rear headroom, a gauge cluster set so high the driver must raise the wheel, driver-camera prompts and a dead brake pedal with regen.
   - KBB praises the Hyperscreen.
   - Outlook: an electric E-Class with three-box body and 800 V / 350 kW (expected) is reported to replace the EQE from 2027.

## Caveats

- **Owner-review volume is extremely thin.** There are 5 real reviews in total (2 E-Class, 3 EQE). cars.com and KBB carry 0 to 2 reviews per page; forum sources are blocked. Theme shares from owner reviews alone are not robust.
- **NHTSA records are a defect registry, so 51 of 52 EQE records are `Defect`.** They are labelled `source_type: owner_survey` and `source_name: "NHTSA complaints"`.
  - Do not pool them with owner reviews when comparing sentiment shares against BMW Source A. Compare them only with BMW defect or safety channels, or exclude them.
  - Each statement starts with the ODI number and the product model as filed.
- **NHTSA vehicle buckets are fuzzy.** Filtering used the `products[].productModel` field plus the narrative.
  - The MY2023 EQE file mixes sedan and SUV: three narratives say SUV under sedan product names. So the MY2023 records are tagged "body style not stated" in the statement, and a few may in fact be EQE SUVs (X294).
  - Two incidents were filed twice (11696247/11696352, and 11579404/11579164, the latter under two different product names). Each pair is one `review_ref`.
- **The WebFetch summary misreported one product model.** ODI 11766723 was summarised as "EQE 350"; the raw JSON says EQE SUV 350+, so it was excluded.
- **NHTSA exposure differs by model year.** MY2024 has about 2.5 years of complaints, MY2026 only a few months.
- **Press sourcing.**
  - Car and Driver and Autoblog content was read through Yahoo Autos syndication, because their own domains block our fetcher.
  - The Car and Driver piece is a 540i test that uses the E450 as a foil, not a formal comparison.
  - Both EQE vs i5 comparisons are Canadian (country `CA`, CAD prices) and cover performance trims (AMG EQE vs i5 M60), not the volume EQE 350+ vs i5 eDrive40.
  - There are 4 press articles per model, one more than the 2 to 3 requested.
- **Conflicting figures.**
  - E-Class trunk: 12.7 cu ft (KBB spec page, Autoblog) vs 19.1 cu ft (KBB comparison article). The 19.1 figure was not used as a record.
  - EQE rear steering: standard on the 2023 Cars.com test car vs optional (KBB 2025).
  - KBB's EQE range table is inconsistent (267 vs 266 to 308 mi).
  - Auto123 gives the i5 range twice with different values, so no range record was taken from it.
- **Label for one owner review.** The KBB E-Class owner review appears on the 2024, 2025 and 2026 pages. It is recorded once (R001), citing the 2025 URL, and covers a MY2025 E 350.
- **Body style for one owner review.** The cars.com EQE 500 review by "AC" (R030) does not state a body style, on a page where another review was explicitly the SUV. It was kept with this caveat.
- **Yahoo syndication is a judgment call.** Autoblog returned 403 and Car and Driver blocks this fetcher. Both articles were then read as licensed syndicated copies on Yahoo Autos. This uses no login, paywall or CAPTCHA, but if the merge step counts it as a workaround, drop R024 and R025 (18 feedback + 2 equipment records).
- **Quotes are not verified word for word.** The `quote` values come from WebFetch's model-written summaries and were not checked against the original pages.
- **Feedback-type mapping.** Negative opinions that are not defects (price, styling, packaging, warranty) are coded `Difficult to Use`. Missing features are coded `Wants`.
- **Equipment gaps.** The MBUSA pages render only partly. Several features are `unknown`:
  - E-Class: HUD, physical climate controls, wireless CarPlay/Android Auto, hands-free highway driving.
  - EQE: HUD, climate controls, voice, CarPlay, OTA, digital key, ventilated and massage seats, air suspension, rear space.

  F15 and F16 were skipped for the E-Class: the AMG E 53 is a PHEV with 43 mi EPA electric range.
- **Unverified and not recorded.**
  - A search result headline says the EQE sedan is dropped from the US line-up for MY2027. InsideEVs returned 502 twice, so this is not recorded. MBUSA still shows a 2026 EQE sedan.
  - Search-snippet material (a Heydealer analysis of about 400 Korean owner reviews, GermanCarForum posts) was not used.
