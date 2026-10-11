# eu_german: research log

Agent key `eu_german`, market EU (DE first, then GB and PL). Collected 2026-10-10.

## Models covered

| Model | Generation | Competitor | Feedback A (records / review_refs) | Feedback B (records / review_refs) | Equipment |
|---|---|---|---|---|---|
| Mercedes-Benz E-Class (Limousine W214, T-Modell S214) | W214 | C001 | 24 / 12 | 49 / 2 | 18 |
| Mercedes-Benz EQE Limousine | V295 | C002 | 26 / 7 | 42 / 2 | 18 |
| Audi A6 (combustion/PHEV, Limousine/Avant) | C9 | C003 | 0 / 0 | 39 / 2 | 18 |
| Audi A6 e-tron (Sportback/Avant, PPE) | PPE | C004 | 8 / 3 | 64 / 3 | 20 |

Total: 330 lines (4 competitor, 252 feedback, 74 equipment).

The `model` values are normalised to `E-Class`, `EQE`, `A6` and `A6 e-tron`. Body style (Limousine, T-Modell, Avant) is given in the statements and in the equipment `trim_scope`. The A6 e-tron uses `generation: "PPE"` so it never matches a filter on the combustion A6 `C9`. These string fields were normalised in one scripted pass over the file. The same pass dropped F0231 (an AUTO ZEITUNG remark about the BMW highway assistant whose Audi side was only inferred) and set three summary-derived quotes to null (F0048, F0068, F0245).

Budget used: 36 WebFetch calls, 15 WebSearch calls.

## Method notes

- **ADAC test PDFs.** WebFetch could not read the ADAC Autotest PDFs and saved the fetched binary locally. I read that file in full with `pdftotext`. The statements and the short German quotes in ADAC records come from the PDF text itself, not from a model summary. Each ADAC record cites the PDF URL that was fetched.
- **Other pages.** All other pages were read through WebFetch summaries, with each review or post listed separately. Quotes are `null` for those pages, except where the summary returned short strings marked as verbatim (ADAC Autokatalog Stärken/Schwächen).
- **Equipment.** Equipment records come from the ADAC Autotest equipment lists and texts for the tested German variant, with prices as of the test date. They use `source_type: press_review` and tier B for every model. Manufacturer configurators (mercedes-benz.de, audi.de) were not fetched: they render with JavaScript, and the budget did not allow it.
- **`comparison` field.** Set only where the source compares explicitly with the BMW 5 Series / i5 (sedan or Touring).

## Sources tried

### Mercedes-Benz E-Class W214

| URL | Status | Records |
|---|---|---|
| https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/mercedes-benz/e-klasse/214/330068/ | ok (ADAC Autokatalog, E 220 d T-Modell AMG Line Premium 4MATIC, Autotest 09/2024, grade 1.8) | C001, E0006, E0015 |
| https://assets.adac.de/image/upload/Autodatenbank/Autotest/at6421-mercedes-benz-e-220-d-t-modell-amg-line-premium-4matic-9g-tronic/mercedes-benz-e-220-d-t-modell-amg-line-premium-4matic-9g-tronic.pdf | ok (full PDF text) | F0001-F0035 (R001), 16 equipment |
| https://www.autozeitung.de/audi-a6-avant-bmw-5er-touring-mercedes-e-klasse-t-modell-vergleichstest-206628.html | ok (AUTO ZEITUNG 14/2024: E 220 d T 1st, 520d xDrive Touring 2nd, A6 Avant 3rd) | F0036-F0049 (R002). The Audi in this test is the **C8**, so no Audi records |
| https://www.autocentrum.pl/oceny/mercedes/klasa-e/w214/ | ok (9 owner ratings, PL) | F0050-F0066 (R003-R010). Review 8 is a word-for-word duplicate of review 7 and was skipped |
| https://www.germancarforum.com/threads/official-new-mercedes-benz-e-class-w214.189530/page-114 | ok (posts 01-02/2025; no poster states ownership) | F0067-F0073 (R011-R014) |
| https://www.carbuyer.co.uk/mercedes/e-class/owner-reviews | ok, but only W212/W213 reviews | 0 |
| https://www.carmagazine.co.uk/car-reviews/comparison/2024/mercedes-e-class-vs-bmw-5-series/ | 402 paywall | 0 |
| https://www.auto-motor-und-sport.de/test/bmw-520d-xdrive-und-mercedes-e-220-d-4matic-im-vergleich/ | paywall (ams+, intro only) | 0 |
| https://www.honestjohn.co.uk/owner-reviews/mercedes-benz/e-class-2023/ | 301 redirect to drive.co.uk homepage (Honest John owner reviews gone) | 0 |
| https://www.motor-talk.de/forum/probleme-mit-e-klasse-s214-e300de-und-fragen-t8090835.html | 403 | 0 (domain dropped) |
| https://www.parkers.co.uk/mercedes-benz/e-class/saloon-2023/owner-reviews/ | 402 | 0 |
| https://www.auto-motor-und-sport.de/test/audi-a6-avant-bmw-5er-touring-und-mercedes-e-klasse-t-modell-im-vergleich-oberklasse-kombis-im-test/ | paywall (ams+, 10/2025, C9 vs G61 vs S214) | 0 |

### Mercedes-Benz EQE V295

| URL | Status | Records |
|---|---|---|
| https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/mercedes-benz/mercedes-eqe/ | ok (ADAC EQE test article, grade 1.7) | C002, E0021 |
| https://assets.adac.de/image/upload/v1663925323/ADAC-eV/KOR/Text/PDF/mercedes-benz-eqe-350_agpcku.pdf | ok (full PDF text, EQE 350+, 08/2022) | F0074-F0101 (R015), 17 equipment |
| https://www.autobild.de/artikel/bmw-i5-edrive40-mercedes-eqe-350-test-25141971.html | ok (AUTO BILD 02/2024: i5 eDrive40 635 vs EQE 350 612 of 800) | F0102-F0115 (R016) |
| https://www.autocentrum.pl/oceny/mercedes/eqe/ | ok (4 ratings, all for the saloon; one is a duplicate) | F0116-F0122 (R017-R019) |
| https://www.goingelectric.de/forum/viewtopic.php?p=2324897 ("Kaufberatung EQE", 04/2025) | ok | F0123-F0135 (R020, R021) |
| https://www.goingelectric.de/forum/viewtopic.php?p=2288890 ("Wer fährt einen und wie läuft es?", p.2, 11/2024-06/2026) | ok | F0136-F0141 (R021, R022, R023) |
| https://www.topgear.com/car-news/big-reads/big-electric-exec-saloon-test-mercedes-eqe-vs-bmw-i5 | 403 | 0 |

### Audi A6 C9 (combustion / PHEV)

| URL | Status | Records |
|---|---|---|
| https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/audi/a6/gh-c9/339507 | ok (A6 Avant 2.0 TDI MHEV plus quattro, Autotest 07/2026, grade 1.9) | C003 |
| https://assets.adac.de/image/upload/Autodatenbank/Autotest/AT6627-audi-a6-avant-20-tdi-mhev-plus-quattro-s-tronic/audi-a6-avant-20-tdi-mhev-plus-quattro-s-tronic.pdf | ok (full PDF text, MY2026 car) | F0142-F0177 (R024), 18 equipment |
| https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/audi/a6/gh-c9/340281/ | ok (A6 Avant 2.0 TFSI e-hybrid, Autotest 03/2026, grade 2.0; page summary only, PDF not fetched) | F0178-F0180 (R025) |
| https://www.auto-motor-und-sport.de/oberklasse/vergleich-neuer-audi-a6-gegen-bmw-5er-und-mercedes-e-klasse/ | paywall (ams+, 03/2025) | 0 |
| https://www.autocentrum.pl/oceny/audi/a6/c9/ | ok, but 0 owner reviews ("nikt jeszcze nie dodał opinii") | 0 |
| https://www.parkers.co.uk/audi/a6/avant-2025/owner-reviews/ | 402 | 0 |
| ams Kombi-Vergleichstest 10/2025 (URL above) | paywall | 0 |

### Audi A6 e-tron (PPE)

| URL | Status | Records |
|---|---|---|
| https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/audi/a6/gh-c9/336507/ | ok (A6 Avant e-tron performance, Autotest 05-06/2025, grade 1.6) | C004, E0069, E0071 |
| https://assets.adac.de/image/upload/Autodatenbank/Autotest/at6483-audi-a6-avant-e-tron-performance/audi-a6-avant-e-tron-performance.pdf | ok (full PDF text) | F0181-F0218 (R026), 18 equipment |
| https://www.autozeitung.de/audi-a6-avant-e-tron-bmw-i5-touring-porsche-taycan-sport-turismo-vergleichstest-300168.html | ok (AUTO ZEITUNG 07/2026: i5 xDrive40 Touring 3,305, A6 Avant e-tron quattro 3,292, Taycan ST 3,266) | F0219-F0230, F0232-F0233 (R027) |
| https://www.autoexpress.co.uk/audi/a6/370003/long-term-test-audi-a6-avant-s-line-e-tron-performance | ok (UK long-term test, 2nd report 09/2026, 2,532 miles; page truncated at the end) | F0234-F0243, F0252, F0253 (R028) |
| https://www.goingelectric.de/forum/viewtopic.php?p=2341235 ("Erste Erfahrungswerte A6 AV e-tron quattro", 06/2025) | ok | F0244-F0248 (R029) |
| https://www.goingelectric.de/forum/viewtopic.php?p=2400107 ("Presse- und Fahrberichte", p.8, 02-08/2026) | ok | F0249-F0251 (R029, R030, R031) |
| https://www.goingelectric.de/forum/viewtopic.php?p=2340981 | ok, but the same thread as p=2341235 | 0 |
| https://www.goingelectric.de/forum/viewtopic.php?p=2245617 ("Warum wir auf den A6 e-tron warten", 07/2024) | ok, posts written before delivery, no owners | 0 |
| https://www.germancarforum.com/threads/the-inevitable-comparison-audi-a6-etron-vs-bmw-i5-vs-m-b-eqe-sedan.280069/latest | ok, but no poster claims to have driven or owned the cars | 0 |
| https://www.autocentrum.pl/oceny/audi/a6-e-tron/ | 404 | 0 |

## Headline findings

### Mercedes-Benz E-Class W214

1. **Touch-heavy HMI is the main pain point (`hmi_infotainment`, `climate`).**
   - ADAC calls the steering-wheel touch surfaces "frustrating" and criticises the dropped physical keys, the imprecise volume slider, climate control in the screen and the missing button for the heated steering wheel.
   - AUTO ZEITUNG prefers the BMW iDrive controller (`bmw_advantage`).
   - On the other side, voice control is rated first-class (ADAC). One owner says the assistant talks too much.
2. **Ride and handling beat the 5 Series Touring (`ride_handling`).** AUTO ZEITUNG rates the air suspension and the steering better than the 520d Touring (`competitor_advantage`). ADAC calls the comfort/agility balance unique in the class.
3. **Flush, auto-extending door handles (`access_locking`).** ADAC calls them a "constant annoyance". One PL owner reports a Defect: the handles did not extend, and the car could not be opened with the fob or the phone.
4. **Space is mixed (`space_practicality`).**
   - The estate's boot and rear space beat the 5er Touring (press, `competitor_advantage`).
   - Three forum users report knee contact with the bulky centre console. One says the 5 Series feels roomier (`bmw_advantage`).
   - One PL owner reports non-adjustable headrests that cause neck pain.
5. **Price and powertrain favour BMW (`equipment_value`, `powertrain_performance`).**
   - ADAC calls the car "extremely expensive", with many assistants extra. AUTO ZEITUNG scores it lower on costs (`bmw_advantage`).
   - ADAC says the BMW two-stage-turbo diesel is more rev-happy. The 520d is quicker.

### Mercedes-Benz EQE V295

1. **Ride comfort and quietness are the core strength (`ride_handling`, `audio_acoustics`).**
   - Press and owners agree: one owner calls it a "flying carpet", another calls the standard suspension excellent.
   - AUTO BILD measured it quieter than the i5 (61 vs 63 dB(A), `competitor_advantage`).
2. **Charging is a weakness (`range_charging_efficiency`).**
   - The 400 V system peaks at about 170 kW. AUTO BILD: i5 205 kW; ADAC: "not among the best".
   - Owners want faster DC and 22 kW AC.
   - Range, on the other hand, beats the i5 (404 vs 383 km, AUTO BILD).
3. **Practicality (`space_practicality`).** The small saloon boot opening, 430 l vs 490 l for the i5 and no frunk draw criticism from ADAC and AUTO BILD. One owner needs to fold a seat to fit a golf bag.
4. **HMI and quality (2022 car) (`hmi_infotainment`, `interior_design_quality`).**
   - ADAC 2022: the 18 steering-wheel touch fields are unreliable, a volume knob is missing and menus are deeply nested.
   - ADAC also finds cost-cutting materials. One owner reports interior rattles after 3,500 km.
   - AUTO BILD 2024 praises the displays and voice control.
5. **Head to head the i5 wins.** AUTO BILD scores it 635 vs 612, on handling, braking, boot and price. The EQE wins rear legroom, range and noise.

### Audi A6 C9 (combustion / PHEV)

1. **Ride and handling (`ride_handling`).**
   - Strong with the 2,150 EUR air suspension: ADAC "would not want to drive it without".
   - Rear-axle steering makes it agile.
   - The steering feels synthetic.
2. **Interior quality regressed against the C8 (`interior_design_quality`).** ADAC lists steel instead of aluminium panels, hard plastic, sun visors without fabric, piano black, creaks and a blank panel where the passenger screen would sit ("weniger wertig als sein Vorgänger").
3. **HMI is touch-heavy (`hmi_infotainment`, `climate`).**
   - Light, mirror and locking functions moved to an unreliable touch panel in the door. Climate is screen-only.
   - Praised: the MY2026 return of steering-wheel rollers, the haptic volume knob, the OLED display and the manual search.
4. **Boot below rivals (`space_practicality`).** 475 l, which ADAC rates below average against the 5er Touring and the E-Class T-Modell.
5. **PHEV (`range_charging_efficiency`).** No DC fast charging. High electric consumption: ADAC measured 83 km of electric range vs 104 km WLTP.

No owner reviews found: the car launched in 2025, autocentrum has 0, and Parkers and motor-talk are blocked. No accessible C9 vs 5er comparison: ams is paywalled, and the 2024 AUTO ZEITUNG test used the C8.

### Audi A6 e-tron (PPE)

1. **Efficiency and range are class-leading (`range_charging_efficiency`).**
   - ADAC: 17.9 kWh/100 km, about 580 km.
   - AUTO ZEITUNG: 21.2 vs 23.7 kWh/100 km and 448 vs 343 km against the i5 Touring (`competitor_advantage`).
   - An owner reports more than 450 km on the motorway at about 150 km/h, and over 340 km in winter.
   - Auto Express is less rosy: 3.2 mi/kWh, and about 260 miles at 80 mph.
2. **Charging is fast on paper and for owners (`range_charging_efficiency`).** ADAC: 283 kW peak, 10-80 % in 23 min. An owner saw 280 kW. However, AUTO ZEITUNG says the i5 did better at the charger (`bmw_advantage`), which contradicts its own peak figures; the record keeps the source's wording.
3. **Interior quality is the biggest complaint (`interior_design_quality`).**
   - ADAC: "Materialanmutung ohne Premiumanspruch", with rattles and a plastic key.
   - AUTO ZEITUNG: the most hard plastic in the test (`bmw_advantage`).
   - A forum user who drove it: "no longer premium apart from the prices".
4. **HMI and visibility (`hmi_infotainment`, `lighting_visibility`).**
   - Quick-select fields are hidden behind the steering-wheel rim, the touch keys are unreliable and the instrument cluster is poor.
   - The optional virtual mirrors are impractical (ADAC).
   - Voice control: Auto Express says it failed to understand the tester, while ADAC calls it reliable.
5. **Rear seat posture and ADAS (`space_practicality`, `adas_parking`).**
   - The high floor gives a sharp knee angle (ADAC, Auto Express, AUTO ZEITUNG `bmw_advantage`).
   - Lane guidance is strong, but there is no automatic lane change (ADAC Wants, owner Wants). AUTO ZEITUNG singles out the BMW highway assistant (logged only, no record).
   - Overall the i5 Touring wins narrowly, 3,305 vs 3,292.

## Caveats

1. **Weighting.** The set is heavily weighted toward press (tier B). Four ADAC test PDFs supply 137 records, and the ADAC e-hybrid page summary supplies 3 more. The e-hybrid quotes are ADAC's Stärken/Schwächen labels as returned by the page summary. Owner (tier A) evidence is thin: E-Class 12 refs, EQE 7, A6 e-tron 3, A6 C9 0. Compare shares within a tier, and count `review_ref`s, not records.
2. **Old EQE test.** The ADAC EQE test dates from 08/2022, before the facelift. Later EQE model years changed equipment, prices and output (for example EQE 350+ at 235 kW from 04/2025, per ADAC search data). Its HMI and price criticism may be partly outdated.
3. **Approximate dates.** Autocentrum shows relative dates only. "4/6/7 months ago" became 2026-06, 2026-04 and 2026-03; "over a year ago" became null; "2 years ago" became 2024. Model years are mostly not stated.
4. **Mislabelled autocentrum review.** One W214 review (R006) is labelled E 220 d, but its text describes the E 300 de diesel PHEV. It is recorded as `PHEV`.
5. **GermanCarForum posters.** No W214 poster states ownership; the statements say "ownership not stated". One poster (R014) says they are American, so it is coded `market: US, country: US`.
6. **Repeat posters on GoingElectric.**
   - alex_at (EQE 300) posts in two threads and is kept under one `review_ref` (R021).
   - MG4_electric (A6 e-tron) posts in two threads and is kept under R029.
   - Most GoingElectric posters give no country, so `country` is null, except where Germany is implied (Flexbonus mention, R020) or the A6 e-tron owner thread.
7. **Body styles and BMW counterparts.**
   - The E-Class press tests are of the T-Modell; the owner reviews are mostly saloons.
   - A6 C9 and A6 e-tron tests are all Avant. No Sportback or Limousine test was accessible.
   - The BMW counterparts in two comparison tests are Touring models (G61, i5 Touring), not the G60 saloon.
8. **Equipment.** Values reflect the tested ADAC variant and the price at test date. "Optional (package)" prices are package prices, not single-option prices. `unknown` is used where the source is silent (for example digital key on the E-Class, voice on the A6 C9).
9. **Blocked or paywalled.** motor-talk (403), Top Gear (403), Parkers owner reviews (402), CAR magazine (402), auto-motor-und-sport tests (ams+ paywall), Honest John (owner reviews redirect to drive.co.uk). Reddit, Edmunds and What Car were not tried.
10. **Not attempted.** Driver Power 2025 placements: searches showed none of the four models in the published lists, and no page was fetched. `next_generation` is null for all four competitors, because no forward-looking source was fetched.
