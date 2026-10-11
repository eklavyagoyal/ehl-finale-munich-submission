# cn_nev: Chinese NEV sedans vs BMW 5 Series Li (G68) / i5, market CN

Agent key `cn_nev`. Output: `competitors/raw/cn_nev.jsonl`.

Collected 2026-10-10 using 34 WebFetch calls (including 4 failures) and 15 WebSearch calls. Every record cites a page fetched in this task. Search snippets and search-engine summaries were used only to find URLs.

## Record counts

| Model | competitor | owner reviews (unique `review_ref`) | owner feedback records | press reviews | press feedback records | equipment |
| --- | --- | --- | --- | --- | --- | --- |
| Xiaomi SU7 | 1 | 20 | 97 | 1 (CarNewsChina 2026 test) | 11 | 20 |
| NIO ET7 | 1 | 20 | 82 | 1 (CarNewsChina 2022 owner-journalist report) | 15 | 20 |
| Zeekr 007 | 1 | 20 | 103 | 1 (CarNewsChina 2024 test) | 14 | 20 |
| Luxeed S7 | 1 | 20 | 66 | 0 (none accessible) | 0 | 20 |
| Stelato S9 | 1 | 20 | 59 | 1 (CarNewsChina 2025 test) | 11 | 20 |
| **Total** | 5 | 100 | 407 | 4 | 51 | 100 |

Five owner records carry an explicit BMW comparison (`comparison` = `competitor_advantage`):
- S7: driving pleasure and interior space vs the owner's family BMW 5 Series.
- S9: standard equipment vs a test-driven BMW i5.
- S9: infotainment vs "BBA".
- ET7: acceleration vs a cross-shopped BMW; the model is not named.

There are no `bmw_advantage` records.

Only 3 of the 5 comparison records name a 5 Series or i5: S7 ×2 (F0325, F0326) and S9 i5 (F0381). The other 2 meet the README rule ("BMW / the 5 Series") but not a strict 5 Series/i5 filter:
- ET7 F0141 compares with "the BMW", no model named.
- S9 F0380 compares with "BBA" generally.

## Models covered and why

- **Xiaomi SU7.** On sale. The 2026 update launched 2026-03-19. Sources disagree on what to call it:
  - CarNewsChina's test drive calls it a "new generation".
  - CarNewsChina's launch article only says "updated".
  - Sohu and Autohome list it as 2026款 of the same series.
  - I therefore kept one generation label, `SU7 1st gen (2024-)`, and put the model year on every record.
  - All 20 owner reviews are of the **2024款** 700 km RWD long-range trim. No 2026款 owner review could be fetched (see sources).
  - Position: one price tier below the 5 Series. Sohu shows SU7 at 21.99-30.39万 and BMW 5 Series at 36.8-52.59万 on the same page. Autohome's SU7 page lists 宝马5系 under 热门对比.
- **NIO ET7.** 2022 launch on NT2.0, 2024 refresh (CnEVPost 2024-04-25). Still listed on Sohu at 42.8-45.8万, which overlaps the 5 Series Li/i5 price range directly. All owner reviews are of the 2024款 75 kWh Executive Signature. I found no 2025/2026 update.
- **Zeekr 007.** Launched 2023-12. 2025款, then a 2026 update with 900 V launched 2026-04-10. Sohu lists the 2026款 at 20.39-24.39万. All owner reviews are of the 2025款 RWD 75 kWh. CarNewsChina frames it against the SU7, Tesla Model 3 and BMW i3, not the 5 Series, so it is an indirect competitor.
- **Luxeed S7** (HIMA, Huawei x Chery). Launched 2023-11. Facelifts in 2025-08 (ADS 4, air suspension, CDC; Autohome says the exterior is "basically unchanged") and 2026-03 (896-channel lidar). All owner reviews are of the 2024款 Max RWD long-range ADS trim, i.e. pre-ADS 4. The Autohome launch article names the SU7 as its rival. I included it because Sohu owners explicitly compare it with a family BMW 5 Series and an Audi A6L.
- **Fifth model: Stelato S9** (HIMA, Huawei x BAIC). This deviates from the suggested list:
  - Li Auto and AITO have no sedan.
  - The S9 is the HIMA executive sedan, and it is the only candidate with a fetched source (CnEVPost, 2025-11-20) naming the **BMW 5 Series** as a rival, alongside the E-Class and A6L.
  - Xpeng P7+ and BYD Han L were not researched, to stay within the fetch/search budget.
  - The S9 was refreshed 2025-11 (BEV and EREV). All owner reviews are of the 2024款 BEV Max RWD long-range.

## Sources

| # | URL | Status | Records |
| --- | --- | --- | --- |
| 1 | https://k.autohome.com.cn/6962/ | empty: reviews rendered by JS, 0 visible (page shows only score 4.46 and tag counts) | 0 |
| 2 | https://db.auto.sohu.com/trim_172041/dianping (2 fetches) | ok: 20 最满意 + 20 最不满意 entries with dates | SU7: 97 feedback |
| 3 | https://db.auto.sohu.com/trim_181652/dianping (SU7 2026 Pro) | empty: 0 entries rendered | 0 |
| 4 | https://db.auto.sohu.com/model_5864/dianping (ET7 model level) | unusable: 1 entry, misfiled Mercedes C260L review | 0 |
| 5 | https://db.auto.sohu.com/trim_172513/dianping | ok: 20 + 19 entries | ET7: 82 feedback, competitor |
| 6 | https://db.auto.sohu.com/model_7250 | ok: trim list, dimensions | 007: 1 equipment |
| 7 | https://db.auto.sohu.com/trim_174112/dianping | ok: 20 + 20 | 007: 103 feedback |
| 8 | https://db.auto.sohu.com/trim_172313/dianping (2 fetches; the 2nd was a brand-mention sweep) | ok | S7: 66 feedback, competitor |
| 9 | https://cnevpost.com/2025/11/20/stelato-launches-updated-s9-sedan/ | ok (no equipment detail) | S9 competitor, 2 equipment |
| 10 | https://db.auto.sohu.com/trim_173917/dianping (2 fetches; the 2nd was a brand-mention sweep) | ok | S9: 59 feedback |
| 11 | https://cnevpost.com/2026/03/23/luxeed-launches-updated-r7-s7/ | ok, thin | S7: 1 equipment |
| 12 | https://data.carnewschina.com/database/luxeed/luxeed-s7/2025 | ok, thin | S7: 1 equipment |
| 13 | https://db.auto.sohu.com/model_7250/config | empty: config table rendered by JS | 0 |
| 14 | https://carnewschina.com/2026/03/20/testing-drive-the-new-xiaomi-su7-is-it-the-apple-car-that-apple-never-built/ | ok | SU7: 11 press feedback, 2 equipment |
| 15 | https://db.auto.sohu.com/trim_181651/dianping (SU7 2026 Standard) | empty: 0 entries rendered | 0 |
| 16 | https://carnewschina.com/2024/05/02/test-drive-zeekr-007-fast-and-luxurious/ | ok | 007: 14 press feedback, 9 equipment, competitor |
| 17 | https://carnewschina.com/2025/01/25/sunday-china-drive-stelato-s9-redefining-luxury-evs-with-advanced-tech-and-competitive-pricing/ | ok (uniformly positive, no negatives) | S9: 11 press feedback, 18 equipment |
| 18 | https://cnevpost.com/2024/04/25/nio-launches-2024-et7/ | ok, thin | ET7: 9 equipment |
| 19 | https://carnewschina.com/2022/11/19/i-bought-my-nio-et7-three-months-ago-and-here-is-all-you-should-know/ | ok | ET7: 15 press feedback, 11 equipment |
| 20 | https://www.autohome.com.cn/news/202508/1308427.html | ok | S7: 17 equipment |
| 21 | https://www.dongchedi.com/auto/series/score/9225-x-S1-x-x-x-x | empty: no content returned | 0 |
| 22 | https://chejiahao.autohome.com.cn/info/24825245 | video page, no text | 0 |
| 23 | https://chejiahao.autohome.com.cn/info/25050877 | fetch failed (no output) | 0 |
| 24 | https://chejiahao.autohome.com.cn/info/25029279 | fetch failed (no output) | 0 |
| 25 | https://carnewschina.com/2026/03/19/xiaomi-su7-new-gen-launched-with-up-to-680-hp-starts-at-31870-usd-in-china/ | ok | SU7: 18 equipment |
| 26 | https://cnevpost.com/2026/04/10/zeekr-launches-updated-007-series/ | ok, thin | 007: 10 equipment |
| 27 | https://k.m.autohome.com.cn/6962/ | ok, but "暂无口碑数据" (0 reviews). 热门对比 lists 宝马5系 | SU7 competitor url |
| 28 | https://dianping.yiche.com/xiaomisu7/ | 404 (guessed URL) | 0 |
| 29 | https://hao.yiche.com/wenzhang/94380445/ | fetch failed (no output) | 0 |
| 30 | https://carnewschina.com/2024/03/26/luxeed-s7-gains-highly-capable-self-driving-ability/ | ok, but a news report rather than a hands-on test (no feedback records) | S7: 1 equipment (OTA) |
| 31 | https://carnewschina.com/2026/01/07/xiaomi-su7s-first-facelift-lidar-and-800v-standard-pre-orders-open-today-for-april-2026-launch/ | ok | 0 (used for the SU7 generation decision in C001) |

There were no CAPTCHA or login walls. Autohome k./k.m. pages, Dongchedi and the Sohu config pages are JS-rendered and return no review data to WebFetch. **Sohu trim-level `dianping` pages are the one owner-review channel that works.**

## Headline findings per model (owner reviews; counts are unique reviews out of 20)

### Xiaomi SU7 (2024款 RWD standard)
1. **exterior_design is the purchase driver.** 12/20 like the styling or colours. One reports paint chipping.
2. **ride_handling is split.**
   - 5 like the steering and handling.
   - 7 report low ground clearance (about 12 cm), a firm or bumpy ride without air suspension (Max only), float at 130 km/h, or RWD slip in the wet.
3. **hmi_infotainment / connectivity_app_digital.**
   - Liked: the voice assistant (fast, understands dialect, controls smart-home devices) and the Xiaomi phone ecosystem / screen casting (4).
   - Disliked: occasional infotainment lag (3).
4. **adas_parking.**
   - The standard trim lacks urban NOA.
   - Lane centring struggles at ramps, auto-parking is abrupt, and the 360° camera misses stones, which led to underbody scrapes (2).
   - Press (2026 Max): snow on the lidar shuts off *all* assistance; the reviewer wants an LKA/ACC fallback.
5. **overall_quality_ownership: delivery waits** of 2 to 4+ months in 8/20 reviews (purchase experience). Parts are expensive. Also: no glass-roof sunshade (2), and sentry-mode battery drain (2).

### NIO ET7 (2024款 75 kWh Executive Signature)
1. **range_charging_efficiency is the main pain point.**
   - Real range is about 300 km on the highway / 380 km in the city vs 450-550 km official; winter losses; high consumption (7 reviews Difficult).
   - Battery swapping (about 3 min) is repeatedly said to compensate (5 Likes).
   - Owners want 100 kWh or a PHEV.
2. **interior_design_quality / seats_comfort are strengths.** Upscale-but-understated cabin, Nappa or white leather, ambient light, massage and aviation-style seats, electrochromic roof.
3. **hmi_infotainment.** NOMI is liked (5), plus rear screens and karaoke. One reports NOMI freezing with no soft reboot.
4. **adas_parking.** Highway assist reduces fatigue (7 Likes). Urban assist distrusted (3): needs clear lane markings, gives up in heavy rain.
5. **space_practicality.** Small trunk opening, tight rear seat, no rear recline (4).
   - Explicit comparison: an owner cross-shopped BMW/Mercedes/Audi/Lexus and says the ET7 is quicker and rides more comfortably.

### Zeekr 007 (2025款 RWD 75 kWh)
1. **range_charging_efficiency is the strongest Like (12/20).** 800 V fast charging (10-20 min), honest highway range (about 90%), good winter retention.
2. **adas_parking: highway NZP is liked (10).** One detailed complaint about NZP lane logic and remote parking that cannot steer.
3. **ride_handling.** Precise steering and handling liked (5). Low ground clearance or kerb scrapes are the top complaint (7).
4. **hmi_infotainment.** Eva assistant with LLM and the AR-HUD are liked. Complaints: voice wake-up and recognition, navigation errors, CarPlay connection, wish for more apps.
5. **space_practicality / connectivity.** Trunk too small for families or camping (3). Owners value the free in-car data. One owner had no OTA for a year.

### Luxeed S7 (2024款 Max RWD, Huawei ADS 2.0)
1. **adas_parking dominates (14/20 Likes).**
   - Owners use Huawei ADS for most of their mileage (about 8,000 of 10,000 km) and praise the NCA commute, high-precision-map-free coverage, and remote/auto parking.
   - Negatives (3): slow in dense city traffic, unexpected steering inputs at first.
2. **lighting_visibility: wipers are the most frequent complaint (4).** Unresponsive in heavy or light rain, noisy; mirror view poor in rain.
3. **equipment_value.** Good value vs Tesla/AITO. But driver-only seat ventilation is standard, options are expensive, and Brembo calipers/wheels are not available on Max.
4. **Explicit BMW comparisons.** One owner finds the S7 more enjoyable to drive and roomier than the family's BMW 5 Series. Others say handling is at least as good as a 3 Series, and space is greater than an old Audi A6L.
5. **audio_acoustics / interior.** Frameless doors and single-pane rear glass let noise in. Odour after sun exposure. Many features need a Huawei phone.

### Stelato S9 (2024款 BEV Max RWD long-range)
1. **adas_parking is entirely positive (12/20).**
   - Near-zero-takeover commutes; one trip ran 346 of 352 km on ADS.
   - Valet parking (VPD) that fetches the car, remote parking, parking on unmarked ground.
2. **range_charging_efficiency is positive (8).** About 500 km at -10 °C and about 700 km in spring vs 816 km CLTC; 800 V charging. Range worries faded.
3. **seats_comfort (rear-biased).** The rear zero-gravity seat and heated/ventilated/massage seats are praised. A test driver felt the rear-focused set-up compromises the front passenger.
4. **space_practicality is the main negative.** Narrow trunk opening (3), small frunk, small armrest box. Owners also mention the large body's manoeuvrability (3), and the price is high (2).
5. **Explicit BMW comparisons.**
   - One owner test-drove a BMW i5 and says the S9 includes driver assistance and seat ventilation as standard where BMW charges extra.
   - The same owner says the infotainment outclasses BBA systems.

## Caveats

- **Pairing assumption.** Sohu pages list 最满意 and 最不满意 snippets separately, without review IDs. I paired them into one `review_ref` by matching date and price; the positions matched one-to-one.
  - Where several entries share the same date and price, pairing within that group is by position and may be swapped: S7 2024-07-17/18/20, 007 2024-12-20 and 2025-01-12, S9 2025-01-01. Review counts are unaffected.
  - The two S7 5 Series comparison records came from dimension sections. I attached them to R072, one of the two 2024-07-18 reviews; the assignment between those two is uncertain.
- **WebFetch output is a model-written summary.** Statements paraphrase that summary, not raw page text. Quotes appear only on the 4 explicit-comparison records, where the fetch was asked for verbatim clauses of 12 characters or fewer. Everything else has `quote: null`.
- **Model years of the reviews.**
  - All owner reviews precede the latest updates: SU7 2026, S7 ADS 4 (2025-08 and 2026-03), 007 2026 (900 V), S9 2025-11 refresh.
  - Some complaints may already be fixed, for example SU7 Standard with no lidar or urban NOA, and S7 on ADS 2.0.
  - Filter on `model_year`.
- **SU7 generation: treated as a facelift, but sources conflict.**
  - For facelift: the CarNewsChina 2026-01-07 headline calls the 2026 car the SU7's "first facelift", and its body describes an exterior refresh with subtle headlight changes and new wheels. The 2026-03-19 launch article calls it "updated". Sohu and Autohome list it as 2026款 of the same series.
  - Against: the 2026-01-07 body and the 2026-03-20 test drive say "next/new generation".
  - If downstream treats the 2026 SU7 as a new generation, the 2024 SU7 owner reviews (R001-R020, 97 records) are previous-generation.
- **Single review page per model.** One trim page, about 20 recent reviews (2024-07 to 2025-12), base or mid trims.
  - These are Sohu's most recent and positively skewed snippets. Several 最不满意 entries say "nothing yet".
  - Compare sentiment shares, not counts.
- **Purchase-experience items.** Delivery waits, sales service and parts prices are recorded under `overall_quality_ownership` and flagged "(purchase experience)". Pure pricing remarks are dropped: discount requests, insurance cost, purchase perks. "Price is high" remarks are kept as `equipment_value` / Difficult to Use.
- **Classification conventions.**
  - Negative opinions that are not usability problems, e.g. disliking the wheel design, are typed `Difficult to Use`.
  - Car size / manoeuvrability complaints are under `ride_handling` with `vfc_level2` null.
  - Battery swap has no matching VFC topic and is left null.
- **ET7 press source.** The CarNewsChina article (2022) was written by an owner-journalist about the pre-refresh car. It is tagged `press_review`, tier B.
- **No S7 press test** was accessible: Chejiahao pages failed or were video-only, the Yiche article failed, and the CarNewsChina item is news.
- **S9 press review.** The CarNewsChina S9 drive is uniformly positive (no negatives), so treat its tone with caution.
- **Equipment.**
  - Mostly `unknown`, because config tables (Sohu, Autohome, Dongchedi) are JS-rendered.
  - `standard` is used only where a source says so (all trims / 全系) or for dimensional specs.
  - Several values describe a press test car or an earlier model year; see `trim_scope` and `as_of`.
  - The SU7 F13 `optional` value means "higher trims only".
- **Other agents in the scratchpad.** Another agent overwrote `scratchpad/validate.py` mid-run. My validator now lives at `scratchpad/cn_nev/validate_cn_nev.py`. Final validation: OK. The theme, feedback_type and vfc_level2 values, and the vfc-to-theme consistency, all match themes.json.
