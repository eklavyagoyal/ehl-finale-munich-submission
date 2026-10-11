# cn_german_g68: research log

Agent `cn_german_g68`, market CN, collected 2026-10-10.
Output: `competitors/raw/cn_german_g68.jsonl` (485 records: 5 competitor, 380 feedback, 100 equipment).
Budget used: 41 WebFetch and 14 WebSearch calls.

## Models covered

| Model | Generation | Role | Feedback records | Unique reviews (review_ref) | Equipment |
| --- | --- | --- | --- | --- | --- |
| BMW 5 Series Li (525Li/530Li, i5 eDrive35L/40L) | G68 | BMW baseline (C001) | 155 (149 owner, 6 press) | 36 ICE owner + 5 i5 owner + 1 press | 20 |
| Mercedes-Benz E-Class L (E 260 L / E 300 L) | V214 | competitor (C002) | 117 (105 owner, 12 press) | 31 owner + 2 press | 20 |
| Audi A6L (40/45/55 TFSI) | C8 L | competitor, outgoing (C003) | 90 (87 owner, 3 press) | 28 owner + 1 press | 20 (mostly unknown) |
| Audi A6L, new generation (PPC) | C9 L | competitor, on sale since 2026-03 (C004) | 18 (5 owner, 13 press) | 1 owner + 2 press | 20 |
| Audi A6L e-tron | PPE (A6L e-tron) | BEV competitor, pre-sale from 2026-03 (C005) | 0 | 0 (no owner reviews exist on Sohu) | 20 |

Generation assignment:
- **E-Class L.** The new long-wheelbase car launched in December 2023 (China Daily). Every review used is a 2024款 or later trim.
- **A6L C8 L.** 2024–2026款 40/45/55 TFSI trims. One 2026 owner explicitly writes "2026款 C8".
- **A6L C9 L.** 2026款 "2.0T 臻选型" (204 hp) and "2.0T 尊享型" (272 hp). These outputs match the 150/200 kW of the new PPC car, and the Autohome editors and one owner call the car C9. "C9" is media/owner usage, not an official Audi code.
- **BMW 5 Series.** The 2022款 525Li page and the imported 525i pages (not G68) were excluded.

## Sources

| URL | Status | Records |
| --- | --- | --- |
| https://k.autohome.com.cn/65 | empty (JS-rendered; only aggregate tags visible) | 0 (context only) |
| https://k.m.autohome.com.cn/65/ | empty ("暂无口碑数据") | 0 |
| https://db.auto.sohu.com/trim_171205/dianping (G68 2024款 530Li 领先型 豪华) | ok, fetched twice for per-entry detail | 28 (8 reviews) |
| https://db.auto.sohu.com/trim_171247/dianping (G68 2024款 525Li 豪华) | ok | 14 (4 reviews) |
| https://db.auto.sohu.com/trim_175834/dianping (G68 2025款 525Li M) | ok | 38 (9 reviews) |
| https://db.auto.sohu.com/trim_175838/dianping (G68 2025款 530Li 领先型 M) | ok | 50 (15 reviews) |
| https://db.auto.sohu.com/trim_181246/dianping (G68 2026款 改款 530Li) | empty (0 reviews) | 0 |
| https://db.m.auto.sohu.com/model_7248/dianping (i5 Li) | ok (5 reviews, no dates shown) | 19 |
| https://db.auto.sohu.com/trim_175838/config, https://db.auto.sohu.com/trim_171247/config | 404 | 0 |
| https://car.autohome.com.cn/config/series/65.html | empty (no config data rendered) | 0 |
| https://www.press.bmwgroup.com/global/article/detail/T0439257EN/... | ok (manufacturer) | C001, 2 equipment |
| https://carnewschina.com/2024/01/18/bmw-set-to-launch-new-5-series-models-in-china-with-enhanced-features/ | ok (press, descriptive only) | 2 equipment |
| https://sina.cn/detail/niizvnu8930337 | empty (redirected to the Sina homepage) | 0 |
| https://www.autohome.com.cn/drive/202502/1303735.html (Autohome 530Li vs E 300 L instrumented test, 2025-02) | ok (press B) | 6 BMW + 7 Mercedes |
| https://news.yiche.com/hao/wenzhang/107220917/ | empty (JS) | 0 |
| https://www.bitauto.com/article/1003107246358/ (2026款 5 Series Li launch, author-provided) | ok | 16 BMW equipment |
| https://db.auto.sohu.com/model_2976/dianping (E-Class model page) | wrong content (shows a mis-filed C 260 L review) | 0 |
| https://db.auto.sohu.com/trim_174681/dianping (V214 2025款 E 260 L) | ok | 9 (2 reviews) |
| https://db.auto.sohu.com/trim_170153/dianping (V214 2024款 E 300 L 时尚型) | ok | 27 (6 reviews) |
| https://db.auto.sohu.com/trim_170604/dianping (V214 2024款 E 260 L) | ok | 8 (2 reviews) |
| https://db.auto.sohu.com/trim_174685/dianping (V214 2025款 E 300 L 时尚型) | ok | 10 (2 reviews) |
| https://db.auto.sohu.com/trim_170600/dianping (V214 2024款 E 300 L 豪华型) | ok | 51 (19 of 20 reviewers used; 1 low-information entry skipped) |
| https://www.chinaservicesinfo.com/s/202312/18/WS657ffb07498ed2d7b7ea3110/mercedes-benz-launches-new-e-class-l.html (China Daily) | ok (press) | C002, equipment |
| https://www.bitauto.com/article/1003107306091/ (E-Class L buying guide, author-provided) | ok (press B) | 5 feedback + equipment |
| https://db.auto.sohu.com/model_2051/dianping (A6L model page) | wrong content (same mis-filed C 260 L review) | 0 |
| https://db.auto.sohu.com/trim_178149/dianping (C8 2026款 45 TFSI 臻选动感) | ok | 24 (7 reviews) |
| https://db.auto.sohu.com/trim_173656/dianping (C8 2025款 45 TFSI 臻选动感) | ok (8 snippets, all one reviewer) | 5 (1 review) |
| https://db.auto.sohu.com/trim_170032/dianping (C8 2024款 45 TFSI 臻选动感) | ok | 58 (20 reviews) |
| https://db.auto.sohu.com/trim_181747/dianping (C9 2.0T 臻选型) | empty (0 reviews) | 0 |
| https://db.auto.sohu.com/trim_181755/dianping (C9 2.0T 尊享型) | ok (1 review) | 5 |
| https://www.bitauto.com/article/1003104100060/ (2026款 A6L C8 launch, author-provided, 2025-10) | ok (press B, thin) | 3 feedback + 20 C8 equipment |
| https://carnewschina.com/2026/03/26/new-audi-a6l-started-sales-in-china-with-v6-powered-hev-system-for-386-hp/ | ok (press, descriptive) | C004, equipment, C003 next_generation |
| https://cnevpost.com/2026/03/25/audi-begins-pre-sales-a6l-e-tron-china/ | ok (press, descriptive) | C005, equipment |
| https://db.auto.sohu.com/model_6115 (A6L e-tron) | ok (trim list only) | used in equipment notes |
| https://db.auto.sohu.com/trim_181760/dianping (A6L e-tron 超长续航版) | empty ("口碑共0条") | 0 |
| https://www.autohome.com.cn/18/0/0-0-1-0/ (A6L article index) | ok (mojibake; used only to find URLs) | 0 |
| https://www.autohome.com.cn/drive/202605/1314244.html and -2.html (C9 3.0T first test) | ok (press B) | 10 |
| https://www.autohome.com.cn/advice/202605/1314555.html (C9 buying guide) | ok (press B) | 3 + equipment |

Not tried, because of budget or because they render with JS like Autohome/Yiche: dongchedi.com, yiche koubei, bmw.com.cn, mercedes-benz.com.cn, audi.cn. No instrumented press test of the C8 A6L was found within budget; the only C8 press source is a thin contributed BitAuto launch article.

## Headline findings

### BMW 5 Series Li G68 (baseline)
1. **ride_handling / powertrain_performance.** Driving feel, steering and the 2.0T/8AT are the most frequent Likes. In Autohome's instrumented test the 530Li beats the E 300 L on power (263 PS measured), 0-100 km/h, fuel use and child-dummy AEB. It loses on braking (rated "average"), the moose test (body bounce, **no rear anti-roll bar**) and static-car AEB. One 2024 owner independently complains about body roll and a "removed anti-roll bar".
2. **equipment_value.** This is the dominant negative theme: de-contenting and paid digital features.
   - Hardware: sunroof that cannot be opened (3 owners), no ventilated seats on 525Li/530Li 领先型 (3), basic or de-contented audio (4), no keyless entry or 360° camera on 525Li, budget tyres.
   - Paid digital: remote climate/remote start at extra cost (about 2,300 yuan) with only 3 months of data; streaming and heated steering wheel as paid unlocks on the i5.
   - Positive value statements come from heavy discounts ("5 Series for 3 Series money", cheaper than E 260 L / E 300).
3. **Braking defects (ride_handling, Braking).** Brake squeal, noise or judder is reported by 4 of 15 reviewers on the 2025 530Li page, and by 1 on the 2025 525Li page (clicking from the brake pedal area). Steering creak at standstill appears on 2 of 9 reviewers on the 2025 525Li page.
4. **audio_acoustics.** Wind, tyre or general cabin noise is a repeated complaint (5 reviews). There are also Harman Kardon sound complaints: "muddy" sound, and no user EQ on the i5.
5. **interior_design_quality.** Opinion is split.
   - Liked: crystal ambient lighting. Three owners rate the interior above the A6(L), the E-Class or both.
   - Against: three owners concede the interior is less luxurious than the E-Class. Faux leather and hard plastics draw criticism.
   - Also recurring: annoying auto start-stop (4 owners) and a raised rear centre tunnel.

### Mercedes-Benz E-Class L V214
1. **interior_design_quality.** Luxury materials and ambient lighting are the top Likes, but rattles, squeaks and new-car odour recur: 7 Defect records from 6 owners, plus one rear-door noise.
2. **space_practicality.** A high rear centre floor/tunnel is the most frequent space complaint. It has 4 dedicated records, and about 8 of the 31 owners mention it in the fetched text. The BMW and the A6L C8 draw the same complaint.
3. **exterior_design.** Five owners rate E-Class styling above BMW's (competitor_advantage); two of them did not consider the 5 Series because of its looks. One E 260 L owner rates its headlights the weakest among BMW, Mercedes and Audi.
4. **ride_handling.** Comfort is praised. Light, vague steering and a boat-like feel are criticised by owners, Autohome and BitAuto ("lacks the 5 Series' connection", bmw_advantage).
5. **equipment_value.** Owners complain about firm pricing and small discounts. Key comfort items are reserved for 豪华型: front ventilation, rear seat heating/ventilation/adjustment, Burmester. Digital headlights are missing on 豪华型 and there is no AWD on the E 300 L.

### Audi A6L C8 L
1. **equipment_value.** Price is the Audi owners' main argument against BMW: five owners call the A6L cheaper or better value than the 5 Series and E-Class. Two more preferred the Audi's looks or found the new 5 Series unappealing. One owner concedes that resale value trails BMW and Mercedes.
2. **powertrain_performance.** Low-speed jerkiness, cold-start shudder and idle shake are the most frequent complaints (11 records from 11 owners).
3. **hmi_infotainment / connectivity.** Owners call the infotainment dated or laggy. Reported faults include head-unit crashes and hum, and CarPlay freezes.
4. **seats_comfort / space.** Complaints include an upright rear backrest, firm seats with short thigh support, the rear floor hump and limited front storage.
5. **Likes.** Exterior styling, matrix LED lights and the triple-screen interior.
6. **Press (BitAuto, 2025-10).** Standard 5G fixes the earlier slow 4G connectivity. The 2026 top trim lost its leather dashboard and quilted seats. The line-up offers only basic ACC and lane keeping (F08 not_available).

### Audi A6L C9 L (new generation) and A6L e-tron
1. **Thin owner evidence.** There is only one owner review: it likes the much younger design, the space and the ride, and finds fuel use high. Autohome's first test of the 3.0T flagship measured 4.68 s 0-100 km/h, 35.1 m braking and a 78.9 km/h moose test. These figures come from a different test and car from the 530Li figures, so they are not directly comparable.
2. **equipment_value / powertrain.** Autohome's buying guide says the entry price of 32.29万 undercuts the 5 Series and E-Class bases by a wide margin. It also says a 3.0T V6 hybrid is offered where rivals have only 2.0T. Air suspension and rear-wheel steering are paid options even on the top trim.
3. **hmi_infotainment / adas_parking.** Autohome calls the menus logical and the voice assistant accurate. Huawei Qiankun ADS (NOA) is optional on the C9 and standard on the 乾崑 trims of the A6L e-tron.
4. **A6L e-tron (spec only, no reviews).** 800 V, 270 kW DC, 107 kWh, up to 815 km and an AR-HUD. The fetched i5 eDrive35L figure is 567 km.

## Caveats
- **Sohu review structure.**
  - Review counts and scores on Sohu are model-level. Reviews are listed per trim page.
  - A reviewer was identified by date + 裸车价 + 平均油耗. On some pages WebFetch inferred the section labels (最满意 / 最不满意 / 外观 …), so `feedback_type` was set from the content.
- **Suspected copy-paste reviews were excluded.**
  - 530Li page: 2024-03-07 / 2024-03-26 and 2024-02-23 / 2024-03-12, identical wording with different dates.
  - 525Li page: 2024-02-02 / 2024-04-13.
  - Four E-Class 豪华型 entries (2024-01-24, 01-30, 03-10, 03-18) have a similar polished style. They were kept, but they may be templated.
- **WebFetch output.** Statements are paraphrases of model-written summaries. The 4 Chinese quotes are short phrases that the tool returned in quotation marks; all other quotes are null.
- **Model pages are unreliable.** The Sohu model-level pages for the E-Class and A6L showed the same mis-filed C 260 L review, so only trim pages were used.
- **Coding conventions** (applied consistently, mirroring the BMW LEVEL3 override):
  - Price/discount complaints: `Wants` / equipment_value.
  - Missing or de-contented features: `Wants` / equipment_value, with the feature's `vfc_level2`.
  - Styling dislikes: `Wants`.
  - Noise and weak performance: `Difficult to Use`.
  - Broken parts, abnormal noises and odour: `Defect`.
  - Dealer service and running costs: overall_quality_ownership.
  - Fuel or energy consumption: range_charging_efficiency with `vfc_level2` null.
- **Comparison values.**
  - `comparison` is always from BMW's perspective.
  - Comparisons with "BBA" as a group are included.
  - One E-Class record (R065) compares with a BMW X3, not the 5 Series.
  - The Autohome test compares a 2024 530Li 尊享型 M Sport with a 2024 改款 E 300 L 豪华型. Its records share `review_ref` R037 across both models.
- **i5 reviews.** The mobile page shows no dates (`published` null) and covers both eDrive35L and eDrive40L.
- **Equipment.**
  - Values come from press articles (three BitAuto pieces are "author-provided" content) and one BMW press release. Many entries are `unknown`, especially for the C8 L (only F08, F12, F15 and F16 are known).
  - When a second source adds detail, it is named with its URL in `notes`; `value` holds only what the cited `url` states.
  - The carnewschina 2024 article's power figures (212/287 hp) conflict with BMW's own figures (190/258 PS) and were not used.
- **No BMW-supplied Chinese feedback exists.** The G68 records are the web baseline only and are not comparable in volume with BMW Source A–D data.
