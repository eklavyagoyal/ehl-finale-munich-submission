# BMW G60 verbatims that mention competitors (log)

Agent: `bmw_g60_mentions` · input: `data/G60_feedback_hackathon.xlsx` (sheet `Feedback_Explorer`) · output: `bmw_g60_mentions.jsonl` (`kind: "bmw_mention"`, labels only, no verbatim text).

Cells written as **`a / b`** mean `a` unique BMW feedback IDs / `b` records. Count IDs, not records (one verbatim can carry several competitors or aspects).

## Method

1. Deduplicated 5,005 classification rows to **4,000 unique feedback IDs** (all rows of one ID have the same text).
2. Ran a broad regex prefilter in three passes:
   - Brand and model names, plus common misspellings.
   - Model codes (e.g. E 350, C-200) and KR/JP market names (Grandeur, Sonata, K8 …).
   - Generic comparison phrases ("compared to", "previous car", "other brands", "rivals", "switched from", "cross-shop" …).
   - Fixes made during the review: an `audi` pattern without a word boundary matched "audio", so it was corrected; `g wagon` and hyphenated model codes were added.
3. Every candidate text was read by hand (448 unique IDs across the passes). Discard categories:
   - regex false positives: VW Golf pattern on golf equipment, Samsung phones, substrings such as `etron`, non-Tesla charging networks, loaner/rental cars;
   - comparisons with BMW's own models or earlier BMW generations;
   - the BMW M/Competition trims;
   - generic overall superlatives against unnamed other cars;
   - generic automated-driving wishes that name no brand;
   - non-automotive brands such as phone makers.
4. Coding rules:
   - One record per (feedback ID, competitor, aspect).
   - Directional records (`competitor_advantage` / `bmw_advantage` / `parity`) are written per compared aspect.
   - `cross_shopped` is added when the customer says they considered or test drove the competitor. Its aspect is "Purchase consideration" when the compared aspect already has a directional record.
   - `previous_car` is used **only** when the customer says they came from the brand and makes no directional comparison.
   - Prior or concurrent ownership is tracked separately (table below), so it does not inflate `previous_car`.
   - Source B: only competitors raised by the customer count. Mentions made only by the call-centre writer were dropped.
5. Generic statements (`competitor_brand: "generic"`) are kept only when they make a specific comparison on an aspect.
   - The comparison target is "rivals", "other brands/makes", other cars in the segment, or other cars the customer has driven, and the statement names an aspect such as sound system, build quality or a driver-assist warning.
   - Brand groups that the customer names are kept as such: `Japanese brands`, `Korean brands`, `German brands`.
   - Statements that the customer is considering other brands, with no brand named, are kept as `generic` + `mention_only` + aspect "Considering other brands". Filter them out if you do not need them.
6. `theme` is the compared aspect, judged by hand. The BMW VFC level2 → theme mapping was used only as a hint.
7. `feedback_type` describes the BMW side of that aspect (Likes / Wants / Difficult to Use / Defect).
8. `engine_type` uses BEV for BMW's `BEVE`, consistent with `tools/bmw_baseline.py`.
9. Tesla Supercharger and NACS-adapter mentions are coded as `Tesla` with `competitor_model: null`. The network appears only in the aspect label.

## Prefilter hits vs confirmed

|  | unique feedback IDs |
| --- | ---: |
| unique feedbacks scanned | 4000 |
| prefilter pass 1 (initial) | 425 |
| prefilter pass 2 (fixed Audi boundary, + misspellings, model codes, KR/JP names, rivals) | 410 |
| prefilter final pass (+ hyphenated codes, G-Wagon, Avant/allroad, extra KR names, EU brands, 'another brand') | 423 |
|   of which hit a brand/model pattern | 172 |
|   of which hit only generic comparison phrases | 251 |
| union of all candidates read manually | 448 |
| **confirmed (≥1 record)** | **191** |
|   confirmed with a named brand/group (not `generic`) | 160 |
|   confirmed with `generic` only | 31 |
| comparison with a previous/other vehicle of unknown brand (not recorded) | 35 |
| generic overall superlatives vs unnamed other cars (dropped) | 4 |
| other discards (false positives, BMW-own comparisons, no comparison) | 218 |
| **records written** | **255** |

Per prefilter pattern group (final pass; an ID can hit several groups):

| pattern group | hits (IDs) | confirmed (IDs) | precision |
| --- | ---: | ---: | ---: |
| Generic | 274 | 75 | 27% |
| Tesla | 70 | 66 | 94% |
| Extra v3 | 38 | 23 | 61% |
| Mercedes | 31 | 30 | 97% |
| Audi | 25 | 23 | 92% |
| Generic rivals | 21 | 10 | 48% |
| Misspelled brands | 11 | 11 | 100% |
| KR/JP market | 10 | 4 | 40% |
| Lexus | 10 | 9 | 90% |
| Hyundai/Kia | 8 | 8 | 100% |
| Chinese/Asian | 6 | 0 | 0% |
| Cadillac | 6 | 6 | 100% |
| VW | 6 | 2 | 33% |
| Toyota/Honda | 5 | 5 | 100% |
| Volvo | 4 | 4 | 100% |
| Porsche | 4 | 4 | 100% |
| Genesis | 3 | 3 | 100% |
| Alfa/Maserati/Ferrari | 3 | 3 | 100% |
| Ford/GM | 2 | 2 | 100% |
| Lucid | 2 | 2 | 100% |
| Model codes | 2 | 2 | 100% |
| Jaguar/LR | 1 | 1 | 100% |
| Acura/Infiniti/Lincoln | 1 | 1 | 100% |
| Nissan | 1 | 1 | 100% |
| Rivian | 1 | 1 | 100% |
| Mazda/Subaru | 1 | 1 | 100% |

## Competitor brand × relation

`a / b` = unique IDs / records.

| competitor_brand | IDs | records | competitor_advantage | bmw_advantage | parity | cross_shopped | previous_car | mention_only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tesla | 66 | 81 | 33 / 35 | 27 / 31 | 2 / 2 | 3 / 3 | – | 10 / 10 |
| Mercedes-Benz | 32 | 46 | 14 / 20 | 15 / 21 | 2 / 2 | 2 / 2 | – | 1 / 1 |
| generic | 32 | 34 | 12 / 12 | 15 / 15 | 2 / 2 | 1 / 1 | – | 4 / 4 |
| Audi | 23 | 26 | 8 / 9 | 10 / 10 | – | 3 / 3 | 3 / 3 | 1 / 1 |
| Lexus | 9 | 11 | 4 / 4 | 3 / 3 | 1 / 1 | 2 / 2 | 1 / 1 | – |
| Hyundai | 7 | 8 | 4 / 5 | 1 / 1 | 2 / 2 | – | – | – |
| Cadillac | 6 | 6 | 3 / 3 | 2 / 2 | – | – | 1 / 1 | – |
| Porsche | 4 | 4 | 1 / 1 | 2 / 2 | 1 / 1 | – | – | – |
| Toyota | 4 | 4 | 3 / 3 | 1 / 1 | – | – | – | – |
| Volvo | 4 | 4 | 1 / 1 | 3 / 3 | – | – | – | – |
| Genesis | 3 | 5 | 2 / 2 | 1 / 1 | – | 1 / 1 | 1 / 1 | – |
| Kia | 3 | 3 | 2 / 2 | 1 / 1 | – | – | – | – |
| Lucid | 2 | 3 | – | 2 / 2 | – | 1 / 1 | – | – |
| Ferrari | 2 | 2 | – | 1 / 1 | – | – | – | 1 / 1 |
| Ford | 2 | 2 | – | 2 / 2 | – | – | – | – |
| Japanese brands | 2 | 2 | 2 / 2 | – | – | – | – | – |
| Korean brands | 2 | 2 | 1 / 1 | 1 / 1 | – | – | – | – |
| Bentley | 1 | 1 | – | 1 / 1 | – | – | – | – |
| German brands | 1 | 1 | – | – | 1 / 1 | – | – | – |
| Honda | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Hyundai/Kia | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Jaguar | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Lincoln | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Maserati | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Nissan | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Peugeot | 1 | 1 | – | – | – | – | 1 / 1 | – |
| Rivian | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Subaru | 1 | 1 | 1 / 1 | – | – | – | – | – |
| Volkswagen | 1 | 1 | – | 1 / 1 | – | – | – | – |

### Net view per brand (directional records only)

| competitor_brand | IDs: competitor better | IDs: BMW better | IDs: parity | net (BMW − competitor) |
| --- | ---: | ---: | ---: | ---: |
| Tesla | 33 | 27 | 2 | -6 |
| Mercedes-Benz | 14 | 15 | 2 | 1 |
| generic | 12 | 15 | 2 | 3 |
| Audi | 8 | 10 | 0 | 2 |
| Lexus | 4 | 3 | 1 | -1 |
| Hyundai | 4 | 1 | 2 | -3 |
| Cadillac | 3 | 2 | 0 | -1 |
| Porsche | 1 | 2 | 1 | 1 |
| Toyota | 3 | 1 | 0 | -2 |
| Volvo | 1 | 3 | 0 | 2 |
| Genesis | 2 | 1 | 0 | -1 |
| Kia | 2 | 1 | 0 | -1 |
| Ford | 0 | 2 | 0 | 2 |
| Japanese brands | 2 | 0 | 0 | -2 |
| Korean brands | 1 | 1 | 0 | 0 |
| Lucid | 0 | 2 | 0 | 2 |
| Bentley | 0 | 1 | 0 | 1 |
| Ferrari | 0 | 1 | 0 | 1 |
| German brands | 0 | 0 | 1 | 0 |
| Honda | 1 | 0 | 0 | -1 |
| Hyundai/Kia | 1 | 0 | 0 | -1 |
| Jaguar | 1 | 0 | 0 | -1 |
| Lincoln | 1 | 0 | 0 | -1 |
| Maserati | 1 | 0 | 0 | -1 |
| Nissan | 1 | 0 | 0 | -1 |
| Rivian | 1 | 0 | 0 | -1 |
| Subaru | 1 | 0 | 0 | -1 |
| Volkswagen | 0 | 1 | 0 | 1 |

### Competitor models named

| brand | model | IDs |
| --- | --- | ---: |
| Mercedes-Benz | E-Class | 8 |
| Audi | A6 | 5 |
| Tesla | Model S | 4 |
| Audi | Q8 e-tron | 2 |
| Tesla | Model Y | 2 |
| Tesla | Model 3 | 2 |
| Hyundai | Grandeur | 2 |
| Mercedes-Benz | EQE | 2 |
| Toyota | Prius | 1 |
| Toyota | Camry | 1 |
| Nissan | Altima | 1 |
| Mercedes-Benz | G-Class | 1 |
| Lincoln | MKZ | 1 |
| Mercedes-Benz | C-Class | 1 |
| Audi | A6 allroad | 1 |
| Hyundai | Tucson | 1 |
| Hyundai | Sonata | 1 |
| Honda | Pilot | 1 |
| Genesis | G80 | 1 |
| Cadillac | CT5 | 1 |
| Audi | e-tron | 1 |
| Audi | A8 | 1 |
| Volkswagen | ID.4 | 1 |

### Customer owns or owned the competitor (previous car or second car in the household)

Tracked apart from `relation`, so a former Tesla owner who compares charging is counted here **and** under `competitor_advantage`.

| competitor_brand | IDs |
| --- | ---: |
| Tesla | 26 |
| Mercedes-Benz | 19 |
| Audi | 12 |
| Lexus | 6 |
| Cadillac | 5 |
| Porsche | 4 |
| Toyota | 4 |
| Volvo | 3 |
| Hyundai | 3 |
| Genesis | 2 |
| Ford | 2 |
| Kia | 2 |
| Volkswagen | 1 |
| Jaguar | 1 |
| Nissan | 1 |
| Maserati | 1 |
| Honda | 1 |
| Lincoln | 1 |
| Bentley | 1 |
| Ferrari | 1 |
| Peugeot | 1 |
| Subaru | 1 |

Total: 90 unique feedback IDs with a stated competitor ownership.

## Theme × relation (where competitors are seen as better vs worse)

`a / b` = unique IDs / records.

| theme | IDs | records | competitor_advantage | bmw_advantage | parity | cross_shopped | previous_car | mention_only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ride_handling | 31 | 38 | 3 / 3 | 23 / 28 | 4 / 4 | 1 / 1 | 2 / 2 | – |
| range_charging_efficiency | 30 | 34 | 19 / 21 | 3 / 3 | 1 / 1 | – | – | 9 / 9 |
| overall_quality_ownership | 28 | 39 | 5 / 6 | 19 / 23 | – | 5 / 6 | 4 / 4 | – |
| adas_parking | 20 | 22 | 17 / 18 | 3 / 3 | – | – | – | 1 / 1 |
| hmi_infotainment | 20 | 21 | 12 / 13 | 5 / 5 | 3 / 3 | – | – | – |
| space_practicality | 13 | 16 | 9 / 10 | 2 / 2 | 1 / 1 | 2 / 2 | – | 1 / 1 |
| interior_design_quality | 13 | 15 | 4 / 4 | 6 / 6 | 2 / 2 | 2 / 3 | – | – |
| powertrain_performance | 13 | 13 | 3 / 3 | 8 / 8 | – | – | – | 2 / 2 |
| equipment_value | 12 | 13 | 2 / 2 | 8 / 8 | – | 1 / 1 | – | 2 / 2 |
| seats_comfort | 9 | 12 | 4 / 7 | 5 / 5 | – | – | – | – |
| connectivity_app_digital | 7 | 8 | 7 / 8 | – | – | – | – | – |
| audio_acoustics | 6 | 6 | 4 / 4 | 2 / 2 | – | – | – | – |
| access_locking | 5 | 5 | 4 / 4 | 1 / 1 | – | – | – | – |
| climate | 5 | 5 | 4 / 4 | 1 / 1 | – | – | – | – |
| exterior_design | 4 | 5 | – | 3 / 4 | – | – | 1 / 1 | – |
| safety | 2 | 2 | 1 / 1 | – | – | – | – | 1 / 1 |
| lighting_visibility | 1 | 1 | – | – | – | – | – | 1 / 1 |

### Net per theme (unique IDs, competitor_advantage vs bmw_advantage)

| theme | competitor better | BMW better | net | reading |
| --- | ---: | ---: | ---: | --- |
| range_charging_efficiency | 19 | 3 | -16 | competitors ahead |
| adas_parking | 17 | 3 | -14 | competitors ahead |
| connectivity_app_digital | 7 | 0 | -7 | competitors ahead |
| hmi_infotainment | 12 | 5 | -7 | competitors ahead |
| space_practicality | 9 | 2 | -7 | competitors ahead |
| access_locking | 4 | 1 | -3 | competitors ahead |
| climate | 4 | 1 | -3 | competitors ahead |
| audio_acoustics | 4 | 2 | -2 | competitors ahead |
| safety | 1 | 0 | -1 | competitors ahead |
| seats_comfort | 4 | 5 | 1 | BMW ahead |
| interior_design_quality | 4 | 6 | 2 | BMW ahead |
| exterior_design | 0 | 3 | 3 | BMW ahead |
| powertrain_performance | 3 | 8 | 5 | BMW ahead |
| equipment_value | 2 | 8 | 6 | BMW ahead |
| overall_quality_ownership | 5 | 19 | 14 | BMW ahead |
| ride_handling | 3 | 23 | 20 | BMW ahead |

## Per source (A–D)

Share = confirmed IDs / all unique G60 feedbacks of that source.

| source | G60 feedbacks | confirmed IDs | share | IDs with named brand | records | IDs competitor better | IDs BMW better |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 854 | 79 | 9.3% | 57 | 130 | 40 | 33 |
| B | 2626 | 105 | 4.0% | 98 | 118 | 41 | 47 |
| C | 384 | 7 | 1.8% | 5 | 7 | 5 | 1 |
| D | 136 | 0 | 0.0% | 0 | 0 | 0 | 0 |

## Per country

| country | G60 feedbacks | confirmed IDs | share | records | top named brands (IDs) |
| --- | ---: | ---: | ---: | ---: | --- |
| US | 3610 | 163 | 4.5% | 216 | Tesla 66, Mercedes-Benz 23, Audi 21, Lexus 8 |
| KR | 205 | 16 | 7.8% | 21 | Mercedes-Benz 3, Hyundai 2, Audi 1, Genesis 1 |
| JP | 53 | 5 | 9.4% | 8 | Mercedes-Benz 2, Japanese brands 1, Lexus 1 |
| DK | 20 | 2 | 10.0% | 4 | Mercedes-Benz 2 |
| AU | 3 | 1 | 33.3% | 1 | Kia 1 |
| CA | 18 | 1 | 5.6% | 1 | Mercedes-Benz 1 |
| FI | 9 | 1 | 11.1% | 1 | – |
| FR | 8 | 1 | 12.5% | 1 | Peugeot 1 |
| GB | 36 | 1 | 2.8% | 2 | Audi 1, Mercedes-Benz 1 |

Countries with no confirmed mention (G60 feedbacks): SE (28), NO (8), LV (1), ES (1).

EU subtotal: 5 IDs / 8 records out of 111 EU feedbacks.

## Per engine type

| engine_type | G60 feedbacks | confirmed IDs | share | records | IDs competitor better | IDs BMW better | top named brands (IDs) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BEV | 1363 | 95 | 7.0% | 127 | 46 | 40 | Tesla 64, Mercedes-Benz 10, Audi 6, Hyundai 3 |
| ICE | 2259 | 80 | 3.5% | 111 | 30 | 37 | Mercedes-Benz 19, Audi 15, Lexus 6, Cadillac 4 |
| PHEV | 378 | 16 | 4.2% | 17 | 10 | 4 | Mercedes-Benz 3, Audi 2, Lexus 2, Hyundai 1 |

## Top aspects where competitors are seen as better (`competitor_advantage`)

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Public fast-charging network | range_charging_efficiency | 9 | 9 | Tesla 9 |
| Electric range | range_charging_efficiency | 5 | 5 | Tesla 3, Mercedes-Benz 1, generic 1 |
| Sound system | audio_acoustics | 4 | 4 | Audi 2, generic 1, Toyota 1 |
| Remote app features | connectivity_app_digital | 3 | 4 | Lincoln 1, Mercedes-Benz 1, Hyundai 1, Tesla 1 |
| Rear cross-traffic alert | adas_parking | 3 | 3 | generic 2, Kia 1 |
| Infotainment software and features | hmi_infotainment | 2 | 3 | generic 1, Rivian 1, Tesla 1 |
| Seat comfort and adjustability | seats_comfort | 2 | 3 | Mercedes-Benz 1, Tesla 1, Audi 1 |
| Air suspension | ride_handling | 2 | 2 | Mercedes-Benz 1, Audi 1 |
| Automated driving capability | adas_parking | 2 | 2 | generic 1, Tesla 1 |
| Automated parking | adas_parking | 2 | 2 | Tesla 2 |
| Collision warning and emergency braking | adas_parking | 2 | 2 | Lexus 1, generic 1 |
| In-cabin storage | space_practicality | 2 | 2 | Mercedes-Benz 1, Lexus 1 |
| Infotainment ease of use | hmi_infotainment | 2 | 2 | Tesla 1, Cadillac 1 |
| Interior design and materials | interior_design_quality | 2 | 2 | Jaguar 1, Genesis 1 |
| Overall luxury feel | interior_design_quality | 2 | 2 | Mercedes-Benz 1, Audi 1 |
| Rear seat space | space_practicality | 2 | 2 | Genesis 1, Nissan 1 |
| Blind-spot audible warning | adas_parking | 1 | 2 | Maserati 1, Mercedes-Benz 1 |
| Home charging setup | range_charging_efficiency | 1 | 2 | Mercedes-Benz 1, Tesla 1 |
| Maintenance and repair costs | overall_quality_ownership | 1 | 2 | Japanese brands 1, Korean brands 1 |
| Vehicle size | space_practicality | 1 | 2 | Audi 1, Mercedes-Benz 1 |

### All competitor-better aspects grouped by theme (unique IDs)

- **range_charging_efficiency** (19 IDs): Public fast-charging network 9; Electric range 5; Automatic charge port cover 1; Charging ease and reliability 1; Dealer charging stations 1; Fuel flap unlocking 1; Home charging setup 1; Home charging speed 1
- **adas_parking** (17 IDs): Rear cross-traffic alert 3; Automated driving capability 2; Automated parking 2; Collision warning and emergency braking 2; Blind-spot audible warning 1; Cruise following-distance control 1; Green light alert 1; Lane centering and adaptive cruise 1; Sentry-mode camera recording 1; Side repeater cameras 1; Speed-limit audible warning 1; Speed-limit sign recognition 1
- **hmi_infotainment** (12 IDs): Infotainment ease of use 2; Infotainment software and features 2; Brake light indicator display 1; Clock and compass display 1; Navigation system 1; Physical controls 1; Radio reception 1; Stay-on after door opening 1; Voice assistant 1; Warning messages clarity 1
- **space_practicality** (9 IDs): In-cabin storage 2; Rear seat space 2; Cabin space 1; Frunk storage 1; Trunk space 1; Vehicle size 1; Wagon body style availability 1
- **connectivity_app_digital** (7 IDs): Remote app features 3; Companion app performance 1; OTA update frequency 1; Send-to-car navigation 1; Wireless phone charging 1
- **overall_quality_ownership** (5 IDs): Dealer and sales experience 1; Handover and owner education 1; Maintenance and repair costs 1; Overall vehicle 1; Reliability 1
- **access_locking** (4 IDs): Automatic window closing in rain 1; Geofenced garage door opening 1; Hands-free trunk opening 1; Unlock settings customisation 1
- **audio_acoustics** (4 IDs): Sound system 4
- **climate** (4 IDs): Air conditioning performance 1; Automatic sun shades 1; Dog mode climate hold 1; Remote climate preconditioning control 1
- **interior_design_quality** (4 IDs): Interior design and materials 2; Overall luxury feel 2
- **seats_comfort** (4 IDs): Seat comfort and adjustability 2; Armrest comfort 1; Massage seats 1; Rear seat recline 1; Seat position assistant 1
- **powertrain_performance** (3 IDs): Acceleration and power 1; Drive readiness without start button 1; Transmission 1
- **ride_handling** (3 IDs): Air suspension 2; Lowered sport suspension 1
- **equipment_value** (2 IDs): Standard ventilated seats 1; Value for money 1
- **safety** (1 IDs): Seat belt pre-tensioning 1

### All BMW-better aspects grouped by theme (unique IDs)

- **ride_handling** (23 IDs): Handling and driving dynamics 16; Ride comfort 8; Braking performance 1
- **overall_quality_ownership** (19 IDs): Build quality 11; Overall vehicle 5; Dealer and sales experience 2; Warranty and service plan 1
- **equipment_value** (8 IDs): Value for money 6; Equipment and options 2
- **powertrain_performance** (8 IDs): Acceleration and power 5; Engine start-stop smoothness 2; Regenerative braking 1
- **interior_design_quality** (6 IDs): Interior design and materials 4; Overall luxury feel 2
- **hmi_infotainment** (5 IDs): In-car technology 3; Navigation system 1; Physical controls 1
- **seats_comfort** (5 IDs): Overall comfort 3; Seat comfort and adjustability 1; Ventilated seats 1
- **adas_parking** (3 IDs): Hands-free highway assist 2; Camera and sensor hardware 1
- **exterior_design** (3 IDs): Exterior design 3
- **range_charging_efficiency** (3 IDs): Electric range 2; Fuel economy 1
- **audio_acoustics** (2 IDs): Cabin quietness 2
- **space_practicality** (2 IDs): Vehicle size 2
- **access_locking** (1 IDs): Garage door opener controls 1
- **climate** (1 IDs): Climate control operation 1

## Top aspects where BMW is seen as better (`bmw_advantage`)

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Handling and driving dynamics | ride_handling | 16 | 19 | Tesla 6, Mercedes-Benz 4, Audi 3, generic 2 |
| Build quality | overall_quality_ownership | 11 | 12 | Tesla 8, generic 2, Mercedes-Benz 1, Lucid 1 |
| Ride comfort | ride_handling | 8 | 8 | Mercedes-Benz 4, Tesla 3, Genesis 1 |
| Value for money | equipment_value | 6 | 6 | generic 2, Mercedes-Benz 2, Tesla 1, Hyundai 1 |
| Overall vehicle | overall_quality_ownership | 5 | 8 | Tesla 2, generic 2, Bentley 1, Ferrari 1 |
| Acceleration and power | powertrain_performance | 5 | 5 | Audi 1, Volvo 1, Mercedes-Benz 1, Kia 1 |
| Interior design and materials | interior_design_quality | 4 | 4 | Audi 2, Mercedes-Benz 1, Tesla 1 |
| Exterior design | exterior_design | 3 | 4 | Mercedes-Benz 2, Lexus 1, Tesla 1 |
| In-car technology | hmi_infotainment | 3 | 3 | Audi 2, generic 1 |
| Overall comfort | seats_comfort | 3 | 3 | Tesla 2, Mercedes-Benz 1 |
| Cabin quietness | audio_acoustics | 2 | 2 | Mercedes-Benz 1, generic 1 |
| Dealer and sales experience | overall_quality_ownership | 2 | 2 | Lexus 2 |
| Electric range | range_charging_efficiency | 2 | 2 | Volkswagen 1, Audi 1 |
| Engine start-stop smoothness | powertrain_performance | 2 | 2 | generic 1, Mercedes-Benz 1 |
| Equipment and options | equipment_value | 2 | 2 | generic 1, Tesla 1 |
| Hands-free highway assist | adas_parking | 2 | 2 | Mercedes-Benz 1, Tesla 1 |
| Overall luxury feel | interior_design_quality | 2 | 2 | Cadillac 1, Tesla 1 |
| Vehicle size | space_practicality | 2 | 2 | Cadillac 1, Audi 1 |
| Braking performance | ride_handling | 1 | 1 | Mercedes-Benz 1 |
| Camera and sensor hardware | adas_parking | 1 | 1 | Tesla 1 |

## Parity, cross-shopping, previous car, mention only

**parity**

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Infotainment ease of use | hmi_infotainment | 2 | 2 | generic 1, Mercedes-Benz 1 |
| Ambient and speaker lighting | interior_design_quality | 1 | 1 | Mercedes-Benz 1 |
| Brake dust | ride_handling | 1 | 1 | German brands 1 |
| Fuel economy | range_charging_efficiency | 1 | 1 | Hyundai 1 |
| Handling and driving dynamics | ride_handling | 1 | 1 | Porsche 1 |
| Interior design and materials | interior_design_quality | 1 | 1 | Hyundai 1 |
| Physical controls | hmi_infotainment | 1 | 1 | Tesla 1 |
| Ride comfort | ride_handling | 1 | 1 | generic 1 |
| Sporty driving character | ride_handling | 1 | 1 | Lexus 1 |
| Vehicle size | space_practicality | 1 | 1 | Tesla 1 |

**cross_shopped**

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Purchase consideration | overall_quality_ownership | 5 | 6 | Tesla 3, Lexus 2, Lucid 1 |
| Purchase consideration | space_practicality | 2 | 2 | Audi 2 |
| Interior design and materials | interior_design_quality | 1 | 2 | Audi 1, Mercedes-Benz 1 |
| Purchase consideration | equipment_value | 1 | 1 | Mercedes-Benz 1 |
| Purchase consideration | interior_design_quality | 1 | 1 | Genesis 1 |
| Purchase consideration | ride_handling | 1 | 1 | generic 1 |

**previous_car**

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Overall vehicle | overall_quality_ownership | 2 | 2 | Audi 2 |
| Ride comfort | ride_handling | 2 | 2 | Audi 1, Genesis 1 |
| Build quality | overall_quality_ownership | 1 | 1 | Peugeot 1 |
| Exterior colour | exterior_design | 1 | 1 | Cadillac 1 |
| Reliability | overall_quality_ownership | 1 | 1 | Lexus 1 |

**mention_only**

| aspect | theme | IDs | records | brands (records) |
| --- | --- | ---: | ---: | --- |
| Supercharger adapter use | range_charging_efficiency | 6 | 6 | Tesla 6 |
| Considering other brands | equipment_value | 2 | 2 | generic 2 |
| Tesla home charger compatibility | range_charging_efficiency | 2 | 2 | Tesla 2 |
| Acceleration and power | powertrain_performance | 1 | 1 | Ferrari 1 |
| Adaptive matrix headlights | lighting_visibility | 1 | 1 | Mercedes-Benz 1 |
| Considering other brands | powertrain_performance | 1 | 1 | generic 1 |
| Considering other brands | space_practicality | 1 | 1 | generic 1 |
| Door emergency release | safety | 1 | 1 | Tesla 1 |
| Incidental mention | adas_parking | 1 | 1 | Audi 1 |
| Supercharger access | range_charging_efficiency | 1 | 1 | Tesla 1 |

## Tesla deep-dive (largest named competitor)

| relation | aspect | IDs |
| --- | --- | ---: |
| competitor_advantage | Public fast-charging network | 9 |
| bmw_advantage | Build quality | 8 |
| bmw_advantage | Handling and driving dynamics | 6 |
| mention_only | Supercharger adapter use | 6 |
| cross_shopped | Purchase consideration | 3 |
| competitor_advantage | Electric range | 3 |
| bmw_advantage | Ride comfort | 3 |
| bmw_advantage | Overall vehicle | 2 |
| mention_only | Tesla home charger compatibility | 2 |
| bmw_advantage | Overall comfort | 2 |
| competitor_advantage | Automated parking | 2 |
| mention_only | Door emergency release | 1 |
| competitor_advantage | Remote climate preconditioning control | 1 |
| competitor_advantage | Infotainment software and features | 1 |
| competitor_advantage | Navigation system | 1 |
| parity | Physical controls | 1 |
| competitor_advantage | OTA update frequency | 1 |
| competitor_advantage | Remote app features | 1 |
| competitor_advantage | Seat comfort and adjustability | 1 |
| competitor_advantage | Sentry-mode camera recording | 1 |
| competitor_advantage | Side repeater cameras | 1 |
| competitor_advantage | Home charging setup | 1 |
| competitor_advantage | Speed-limit audible warning | 1 |
| competitor_advantage | Stay-on after door opening | 1 |
| mention_only | Supercharger access | 1 |
| competitor_advantage | Infotainment ease of use | 1 |
| competitor_advantage | Frunk storage | 1 |
| competitor_advantage | Green light alert | 1 |
| bmw_advantage | Regenerative braking | 1 |
| bmw_advantage | Equipment and options | 1 |
| bmw_advantage | Exterior design | 1 |
| bmw_advantage | Hands-free highway assist | 1 |
| bmw_advantage | Interior design and materials | 1 |
| bmw_advantage | Navigation system | 1 |
| bmw_advantage | Overall luxury feel | 1 |
| bmw_advantage | Physical controls | 1 |
| bmw_advantage | Value for money | 1 |
| competitor_advantage | Geofenced garage door opening | 1 |
| competitor_advantage | Acceleration and power | 1 |
| competitor_advantage | Automated driving capability | 1 |
| competitor_advantage | Charging ease and reliability | 1 |
| competitor_advantage | Companion app performance | 1 |
| competitor_advantage | Dog mode climate hold | 1 |
| competitor_advantage | Drive readiness without start button | 1 |
| bmw_advantage | Camera and sensor hardware | 1 |
| parity | Vehicle size | 1 |

## Reading notes

- **Tesla charging access combined:** 14 unique IDs have `competitor_advantage` "Public fast-charging network" or `mention_only` "Supercharger adapter use" / "Supercharger access". All Tesla records on range_charging_efficiency together: 21 IDs.
- **Ownership vs `previous_car`:** 90 IDs state that the customer owns or owned the competitor, but only 7 IDs carry `relation: previous_car`, because that relation is reserved for non-directional cases. Use the ownership table above for conquest analysis.
- **Parity is not always neutral:** 7 of 11 parity IDs carry a non-Likes feedback_type. They mean "BMW has become more like X" (e.g. touch-heavy controls, a less sporty character), which is a negative signal.
- **"Considering other brands"** (generic, mention_only) is a floor for churn intent. Statements that do not name or reference another brand were not counted.
- **ADAS and HMI losses are fragmented.** Most of those competitor-better aspects have only 1–2 IDs, so use the theme net table next to the top-aspect tables.

## Caveats

- **Small numbers.** About 5 % of G60 feedbacks name or compare a competitor. Per-aspect counts are mostly 1–10 IDs. Treat these as qualitative signals, not shares.
- **US-heavy.** About 90 % of the G60 feedback is US, and there are no DE or CN feedbacks. EU and KR/JP add only a few mentions each. KR mentions name Mercedes, Hyundai/Kia, Genesis and Korean brands as a group.
- **Source effects.**
  - Source B is a third-person call-centre paraphrase and only keeps comparisons the customer raised.
  - Sources C and D are structured survey answers and contain few comparisons.
  - Source A is the closest match to competitor owner reviews.
- **BEV selection.** i5 (BEV) owners are over-represented among competitor mentions, mostly Tesla converts. EV charging and range topics therefore dominate `competitor_advantage`.
- **Prior ownership is not loyalty.** Many confirmed IDs come from conquest customers (ex-Tesla, ex-Audi, ex-Mercedes, ex-Lexus) who explain why they switched. That biases the record set toward `bmw_advantage`.
- **Judgement calls.**
  - Relation, theme and aspect were coded by hand from one reading. Borderline cases were coded conservatively: a difference without a stated better/worse became `previous_car` or `parity`, not a directional relation.
  - Generic overall superlatives against unnamed other cars were dropped.
  - 35 comparisons with a previous vehicle of unknown brand were not recorded, because many are likely earlier BMWs.
- **Prefilter recall.** The regex is broad and was run in three passes with misspelling variants. Comparisons that neither name a brand nor use a comparison phrase can still be missed.
- **Confidentiality.** No verbatim text or paraphrase is stored, only IDs and short labels.
