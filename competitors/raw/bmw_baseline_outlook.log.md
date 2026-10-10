# Agent log: `bmw_baseline_outlook`

Task: (1) BMW 5 Series equipment baseline (F01–F20) for EU (G60, DE price list), US (G60) and CN (G68 5 Series Li / i5 Li); (2) a forward-looking outlook (2026–2030) for the competitor lines and for BMW's own Neue Klasse direction.
Run date: 2026-10-10. Output: `competitors/raw/bmw_baseline_outlook.jsonl`.

## Result counts

| Kind | Market | Records | Notes |
| --- | --- | --- | --- |
| equipment | EU | 21 | All 20 features. F18 has two rows (ICE/PHEV 520 l, BEV 490 l). Source: local DE price list, July 2026 |
| equipment | US | 21 | All 20 features. F18 has two rows (530i, i5). Sources: BMW US press release (2023) plus MY2027 pages from cars.com, KBB, bmwblog and fueleconomy.gov |
| equipment | CN | 20 | All 20 features. Sources: CarNewsChina 2026 i5 database, Autohome creator article on the Feb 2026 launch, Xinhua |
| outlook | — | 19 | 16 competitor/BMW lines plus 3 `industry` trends |

Availability across the 62 equipment rows, by market:

| Market | standard | optional | not_available | unknown |
| --- | --- | --- | --- | --- |
| EU | 12 | 6 | 1 (massage) | 2 (F03, F13) |
| US | 12 | 5 | 1 (physical climate controls) | 3 (OTA, digital key, massage) |
| CN | 11 | 1 | 1 (rear-wheel steering on i5 Li) | 7 |

Outlook confidence across the 19 records: 13 announced, 4 reported, 2 rumoured.

The many `unknown` values in CN come from the Autohome config pages, which render with JS and obfuscated fonts. They were not used.

## Conventions used

- `model` = "5 Series" in all markets. `generation` = G60 (EU/US) or G68 (CN). Powertrain and trim go in `trim_scope`.
- **Entry trim**:
  - EU: 520i. The i5 eDrive40 is used for the BEV features F15 and F16.
  - US: 530i. The i5 eDrive40 is used where the only MY2027 source (cars.com) covers the i5.
  - CN: 525Li / i5 eDrive35L. The i5 Li is used where the source only covers the i5.
- **F09 convention**: `availability` describes basic automated parking. Remote/smartphone parking and other advanced tiers are described in `value`.
- **Features missing from the DE price list**:
  - Massage is recorded as `not_available` ("not in DE July 2026 price list"). It would appear as an SA option if offered.
  - Air suspension (F13) and physical climate controls (F03) are recorded as `unknown`. They could be unlisted standard hardware, since the standard list is only "ausgewählt".
- **Source types**:
  - Local list, BMW press releases and fueleconomy.gov (the official EPA rating) are `manufacturer` / tier C.
  - Third-party spec pages (cars.com, KBB, CarNewsChina database) and press/creator articles are `press_review` / tier B.
- **Outlook confidence**:
  - `announced` = an official OEM or regulator act (launch, pre-sale, OEM press release, CEO statement on an earnings call, MIIT approval), even when read through a press report of that act.
  - `reported` = credible press, not officially confirmed.
  - `rumoured` = blogger or insider analysis.
- Outlook records carry an extra `notes` field for caveats and secondary URLs.
- Secondary URLs named in `notes` were all fetched in this task.

## Budget

- WebFetch: 40 calls, 31 OK and 9 failed (budget ~45).
- WebSearch: 18 calls (budget ~20).
- Search snippets were used only to find URLs. Facts in records come from fetched pages. A few `notes` mention snippet-only facts, and these are explicitly marked "not verified by fetch".

## Source status

| # | URL | Status | Used for |
| --- | --- | --- | --- |
| – | docs/datasets/option-lists/G60-5-series.md (local) | OK | EU E0001–E0021 |
| 1 | https://www.bmwusa.com/vehicles/5-series/sedan/overview.html | FAIL (timeout 60 s) | — |
| 2 | https://www.bmwblog.com/2026/07/14/2027-bmw-5-series-price-specs-changes/ | OK | US F02, notes (MY2027 packages, B&W $1,000, DAP $650) |
| 3 | https://www.press.bmwgroup.com/usa/article/detail/T0418778EN_US/the-new-bmw-5-series-sedan?language=en_US | OK (May 2023) | US F01, F03, F05, F06, F08, F09, F13, F14, F16, F18, F19 |
| 4 | https://insideevs.com/news/802185/2027-bmw-i5-range-increase/ | FAIL (HTTP 502) | — (MY2027 NACS port therefore unverified) |
| 5 | https://www.cars.com/research/bmw-i5-2027/specs/ | OK | US F10, F11, F12, F17, F20 (MY2027 i5 packages and prices) |
| 6 | https://www.fueleconomy.gov/feg/PowerSearch.do?...year1=2027...baseModel=i5 | OK | US F15 (EPA 328 mi) |
| 7 | https://www.caranddriver.com/bmw/5-series-2026 | FAIL (fetch tool blocked) | — |
| 8 | https://www.kbb.com/bmw/5-series/2027/specs/ | OK | US F04, F07 (MY2027 530i) |
| 9 | https://www.autohome.com.cn/news/202601/1312034.html | OK, no specs | — (says only that more comfort items become standard in 2026) |
| 10 | https://auto.sina.cn/2026-07-22/detail-iniispne4767376.d.html | FAIL (HTTP 404) | — |
| 11 | https://data.carnewschina.com/database/bmw/bmw-i5/2026/params | OK | CN F01, F02, F05, F07, F08, F11, F13–F20 |
| 12 | https://data.carnewschina.com/database/bmw/bmw-5-series/2026/params | FAIL (404, guessed URL) | — |
| 13 | https://chejiahao.autohome.com.cn/info/24819297 | OK (Autohome creator / self-media, 2026-02-03) | CN F03, F09, F10, F12 |
| 14 | https://www.news.cn/auto/20250427/7a444691d682422ca0393c88deb32195/c.html | OK (Xinhua, 2025-04-27) | CN F04, F06 (DeepSeek) |
| 15 | https://db.auto.sohu.com/trim_179233/ | OK, overview only | — (2026 530Li 尊享型, 52.59万 CNY, marked 停售; a "改款" version exists) |
| 16 | https://www.electrive.com/2025/08/20/mercedes-launches-the-electric-e-class-a-year-earlier-than-planned | OK | O001 |
| 17 | https://www.autocar.co.uk/car-news/new-cars/mercedes-benz-eqe-saloon-and-suv-production-end-2026 | FAIL (HTTP 402 paywall) | — |
| 18 | https://cnevpost.com/2026/03/25/audi-begins-pre-sales-a6l-e-tron-china/ | OK | O003 |
| 19 | https://www.kbb.com/car-news/audi-a6-e-tron-and-q6-e-tron-lineups-see-big-tech-upgrades-for-2027 | OK | O002 |
| 20 | https://www-ak-ms.foxbusiness.com/fox-news-auto/tesla-ends-production-model-s-model-x-vehicles-focus-robots-2026 | OK | O004 notes |
| 21 | https://www.thestar.com.my/tech/tech-news/2026/09/08/slovenia-clears-tesla039s-fsd-driver-assistance-ahead-of-eu-vote | OK (Reuters) | O005 |
| 22 | https://www.lexus.com.au/news/2026/07/all-new-lexus-es-a-new-generation-of-luxury-sedan | FAIL (HTTP 403) | — |
| 23 | https://global.toyota/en/newsroom/lexus/42650696.html | OK | O007 |
| 24 | https://electrek.co/2025/09/10/genes-delaying-this-next-generation-ev/ | OK | O006 |
| 25 | https://www.kbb.com/car-news/2026-volvo-es90-the-classic-volvo-luxury-sedan-electrified | OK (Feb 2025 preview) | O008 notes |
| 26 | https://theweeklydriver.com/2026/04/volvo-google-gemini-2026-rollout | OK | O008, O018 |
| 27 | https://www.press.bmwgroup.com/global/article/detail/T0454649EN/the-bmw-ix3-ushers-in-next-generation-innovations-at-ces-2026?language=en | OK | O015 |
| 28 | https://cnevpost.com/2026/03/19/xiaomi-launches-next-gen-su7-further-challenge-tesla/ | OK | O009 |
| 29 | https://en.aletihad.ae/news/business/4587378/xiaomi-to-consider-selling-cars-outside-china-from-2027--ceo | OK (Reuters) | O010 |
| 30 | https://eletric-vehicles.com/nio/nio-et7-long-fade-from-flagship-star-to-eleven-units-sold-a-month/ | FAIL (HTTP 403) | — |
| 31 | https://cnevpost.com/2026/04/02/zeekr-starts-pre-sales-updated-007-series/ | OK | O011 |
| 32 | https://cnevpost.com/2026/04/01/nio-to-launch-2026-es6-ec6-et5-et5t-apr-2/ | OK | gap evidence only (ET7 not in 2026 update wave) |
| 33 | https://cnevpost.com/2025/12/23/arcfox-deepal-secure-1st-dedicated-license-plates-l3/ | OK | O017 |
| 34 | https://carnewschina.com/2026/03/02/huawei-will-put-worlds-highest-line-count-mass-produced-lidar-on-its-updated-maextro-s800-and-aito-m9/ | OK | O013 |
| 35 | https://www.bimmerfile.com/2026/05/26/the-next-bmw-5-series-a-major-update-now-a-bigger-change-coming/ | OK | O016 |
| 36 | https://www.electrive.com/2025/03/18/byd-introduces-megawatt-charging-for-electric-cars | OK | O019 |
| 37 | https://carnewschina.com/2025/09/29/huawei-qiankun-ads-sets-2027-target-for-large-scale-l3-autonomous-driving-rollout/ | OK | O014 |
| 38 | https://cnevpost.com/2026/03/23/luxeed-launches-updated-r7-s7/ | OK | O012 |
| 39 | https://www.etvbharat.com/en/technology/tesla-ends-production-of-model-s-and-model-x-at-fremont-plant-enn26051101437 | OK | O004 |
| 40 | https://www.motorauthority.com/news/1145818_electric-mercedes-benz-e-class-release-date | FAIL (HTTP 403) | — |

## Gaps and caveats

**US baseline is partly 2023**
- The richest US source is the May 2023 launch press release.
- MY2027 changes were checked against bmwblog (Jul 2026), cars.com, KBB and fueleconomy.gov. BMW says MY2027 technology "carries over unchanged".
- The following could not be verified for the US:
  - wireless CarPlay
  - Digital Key
  - OTA scope
  - massage seats
  - the MY2027 native NACS port (InsideEVs returned 502)

**CN baseline is thin for the ICE 5 Series Li**
- Most CN rows describe the i5 Li (CarNewsChina database). ICE 525Li/530Li rows come from one Autohome creator (self-media) article on the 2 Feb 2026 launch.
- Not verified for CN:
  - CarPlay/CarLife
  - digital key
  - OTA
  - trunk volume
  - DC kW / voltage
  - massage
  - air suspension on ICE Li models
- The DeepSeek LLM assistant was announced for Q3 2025. Its delivery status in 2026 is not verified.
- Search snippets claim the Feb 2026 relaunch made the following standard across the range (BMW China "8 new standard items"): front ventilation, rear seat heating, 4-zone climate, Parking Assistant Pro and 5G. The fetched article states this only for the entry trims.

**CarNewsChina speaker counts**
- The database lists Harman Kardon with "6 speakers" on the i5 eDrive35L, which looks implausible. It is flagged in E0061.

**Outlook lines without a record**
- **NIO ET7 successor: gap.** No credible source for an ET7 successor or facelift was found.
  - NIO's April 2026 update wave covers ES6, EC6, ET5 and ET5 Touring, plus ES9 and a 5-seat ES8, and does not mention the ET7.
  - The one article on ET7 decline returned 403.
  - The NIO ET9 (launched 2025) is the de-facto flagship sedan, but no record was created for it.
- **Xiaomi large sedan ("SU7 L")**: only search snippets, so no record.
- **Mercedes MB.OS / E-Class facelift**: no fetched source. The Autocar and Motor Authority pages were blocked.
- **Euro NCAP physical-controls trend**: not researched because of budget. Of the three industry trends, LLM assistants, China L3 and megawatt charging were chosen.

**F03 market split comes from sourcing**
- The US row is `not_available`: BMW's US release says climate is touch-operated on the control display.
- EU and CN rows are `unknown` for the same dashboard, because their sources are silent.
- Do not read this as a market difference.

**Schema extension**
- Outlook records carry an extra `notes` field that is not in the README schema.

## Suspicious or inconsistent findings

1. **OS naming differs by market.**
   - The DE price list says BMW Operating System 8.5.
   - Xinhua (BMW China announcement) calls the CN 5 Series LWB / i5 system "ninth-generation BMW operating system".
   - BMW's Alexa+ assistant is scoped to OS 9 / OS X (DE/US, H2 2026), which suggests today's EU/US G60 (OS 8.5) may not get it before the LCI.
2. **Lidar counts conflict.** The updated Maextro S800 is called the "world's highest line-count" lidar at 500 lines (MIIT filing), while the Mar 2026 Luxeed S7 is reported with an 896-channel lidar. Channel and line counts probably differ.
3. **2026 5 Series Li pricing is in two waves.** Sohu lists a discontinued 2026 530Li 尊享型 at 52.59万 CNY. The Feb 2026 relaunch is quoted at 36.8–44.8万 CNY, which the article says is 7–9万 lower than the previous model.
4. **Volvo ES90 in the US is unclear.** The Gemini rollout starts in the US, but ES90 US sales are unconfirmed (Consumer Reports snippet only).
5. **The Mercedes electric E-Class timing (H2 2027) is second-hand.** electrive cites a blog that cites a CEO statement.

## What the 5 Series successor will face

- **Charging is table stakes at 10–15 min**
  - *Theme: range_charging_efficiency. Confidence: announced.*
  - Chinese rivals already ship 10–80 % in about 10 min (Zeekr 007, 900 V/6C), 670 km in 15 min (Xiaomi SU7 Max), and BYD's 1,000 kW platform (~400 km CLTC in 5 min).
  - The current i5 does 205 kW, 30 min (EU) or 30–80 % in 0.6 h (CN).
  - BMW's own Gen6 (800 V, 400 kW, 21 min) closes most, but not all, of the gap.
- **Assisted driving moves from hands-off to eyes-off in China**
  - *Theme: adas_parking. Confidence: announced (Huawei/MIIT); Counterpoint forecast for further approvals.*
  - MIIT approved the first L3 cars in Dec 2025, with more expected in 2026.
  - Huawei targets L3 at scale by 2027. Standard lidar plus Thor/ADS 4–5 is now common at 5 Series Li prices (Xiaomi SU7, Luxeed S7, Maextro S800).
  - Even Audi's A6L e-tron uses Huawei urban NOA. The G68 lists L2 only.
- **Europe: supervised point-to-point assist arrives**
  - *Theme: adas_parking. Confidence: reported.*
  - Tesla FSD (Supervised) is approved in at least 6 European countries (Sept 2026) and an EU-wide vote is pending.
  - By comparison, G60 hands-off is optional (EUR 5,350 stack on a 520i) and limited to German Autobahn up to 130 km/h.
- **LLM voice assistants become standard and arrive by OTA**
  - *Theme: hmi_infotainment. Confidence: announced.*
  - Volvo has Gemini on 16 models (from Apr 2026), Mercedes has ChatGPT in MBUX, BMW announced DeepSeek in China and Alexa+ in DE/US (H2 2026).
  - The successor needs this on day one in all three markets.
- **Physical controls are coming back**
  - *Theme: hmi_infotainment / climate. Confidence: announced.*
  - Audi restores physical steering-wheel buttons and a scroll wheel for MY2027. Lexus ES adds "Responsive Hidden Switches".
  - The G60's touch-only climate (BMW US release) runs against this trend.
- **Long wheelbase and generous standard equipment define CN**
  - *Theme: equipment_value / space_practicality. Confidence: announced.*
  - Audi A6L e-tron 3,076 mm, Xiaomi SU7 3,000 mm, Lexus ES 2,950 mm.
  - BMW China already made ventilation, rear heating, 4-zone climate and remote parking standard on entry trims in Feb 2026, while in DE these are EUR 2,750 (Comfort Paket) plus EUR 1,150 (5DW, which also needs the EUR 1,900 Travel Paket).
- **The large-sedan BEV field thins in the West**
  - *Theme: powertrain_performance. Confidence: announced (Tesla, Lexus), reported (Mercedes), rumoured (Genesis).*
  - Tesla Model S is gone (May 2026) and the next Genesis G80 has slipped to 2029+.
  - Mercedes merges EQE into an electric E-Class (H2 2027), and Lexus ES adds a BEV with only 150 kW charging.
  - The direct rivals for an NK-based 5 Series around 2030 are the electric E-Class, the A6 e-tron (refreshed) and Chinese entrants (Xiaomi plans overseas sales from 2027).
- **BMW's own bridge: the LCI before Neue Klasse**
  - *Theme: hmi_infotainment. Confidence: rumoured.*
  - The G60 LCI (reportedly July 2027) brings Panoramic Vision, an optional passenger display and city/highway assist options.
  - The full NK 5 Series (NC0, reportedly July 2030) brings 800 V and Panoramic iDrive X.
