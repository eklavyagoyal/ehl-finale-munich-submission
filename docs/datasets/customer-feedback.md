# Customer verbatims: `*_feedback_hackathon.xlsx`

Free-text customer feedback on the current vehicle, already tagged by BMW with a feedback classification (VFC). One file per vehicle:

| File | Vehicle | Rows | Unique feedbacks (IDs) | Max rows per ID |
| --- | --- | ---: | ---: | ---: |
| `data/F70_feedback_hackathon.xlsx` | BMW 1 Series (F70) | 4,076 | 2,128 | 11 |
| `data/G60_feedback_hackathon.xlsx` | BMW 5 Series (G60) | 5,005 | 4,000 | 18 |
| `data/G70_feedback_hackathon.xlsx` | BMW 7 Series (G70) | 4,690 | 4,000 | 17 |

Each file has a single sheet, `Feedback_Explorer`.

> **One row = one classification, not one feedback.** A verbatim that mentions several topics appears once per topic, with the same `ID` and the same text. Always count unique `ID`s when you count feedbacks. All rows of one ID carry identical text (verified).

Labels: **observed** means checked in the data. **Inferred** means our reading; BMW has not confirmed it.

## Columns

| Column | Meaning | Values (observed) |
| --- | --- | --- |
| `ID` | Feedback ID, `<e-code>-<nnnn>` | F70-0001…F70-2128, G60-0001…G60-4000, G70-0001…G70-4000 |
| `Source` | Anonymized feedback channel | `Source A`–`Source D` (see below) |
| `Brand` | Brand | always `[BMW]` |
| `Sales Description` | Model series | `[BMW 1 Series]`, `[BMW 5 Series]`, `[BMW 7 Series]` (one per file) |
| `Country` | ISO country code of the customer | see coverage below |
| `Derivate (e-code)` | Vehicle derivative | `F70`, `G60`, `G70` (one per file; **no G68 rows** in the G60 file) |
| `Engine Type` | Powertrain | `ICE`, `PHEV`, `BEVE` (inferred: BEVE = battery-electric, i.e. i5 / i7) |
| `Feedback Type` | Coarse sentiment/type | `Likes`, `Difficult to Use`, `Defect`, `Wants`, empty |
| `Customer Feedback` | The verbatim (English) | median ~140–150 characters, max 1,554 (F70) / 3,498 (G60) / 4,260 (G70) |
| `Vfc level2 3 Name` | `"<level2> : <level3>"` concatenated | redundant with the next two columns (matches in >99.9 % of rows) |
| `Vfc level2 Name` | **Topic / component** (what the feedback is about) | 120 (F70), 221 (G60), 211 (G70) distinct values; 226 across all files; plus `no_class_found` or empty |
| `Vfc level3 Name` | **Nature of the statement** (like / defect / request …) | 57 (F70), 82 (G60), 77 (G70) distinct values |

## Feedback sources

BMW does not explain the sources. The descriptions below are **inferred** from how the texts read.

| Source | Style of text | Countries | Vehicles | Inferred channel |
| --- | --- | --- | --- | --- |
| **A** | First person, mostly lowercase, review-like: *"really solid build, lots of attention to detail. i only knock off one mark because there's no paper user manual."* | Many (GB, JP, KR, US, SE, FR, …) | F70, G60, G70; **the only source for F70** | Owner reviews / online or app feedback |
| **B** | Third-person paraphrase: *"Customer stated the vehicle provides a quiet, peaceful ride."* | US only | G60, G70 | Dealer, call-centre or interview notes |
| **C** | Survey answers: *"I had a very serious problem with \<item> - \<symptom>: "…""*, plus open questions such as *"What is the primary reason for your nps rating?"* | US only | G60, G70 | Quality / NPS survey with severity levels |
| **D** | *"\<answer>. That is the one thing I love most about / could be most improved about \<area> of my vehicle."* | US only | G60, G70 | Structured survey open-ends |

### Unique feedbacks per source

| Source | F70 | G60 | G70 |
| --- | ---: | ---: | ---: |
| A | 2,128 | 854 | 695 |
| B | – | 2,626 | 2,853 |
| C | – | 384 | 314 |
| D | – | 136 | 138 |

## Coverage

### Countries (unique feedbacks)

| Vehicle | Countries |
| --- | --- |
| F70 | GB 1,293 · JP 672 · SE 71 · FR 53 · AU 16 · FI 8 · DK 8 · KR 4 · ZA 3 |
| G60 | US 3,610 · KR 205 · JP 53 · GB 36 · SE 28 · DK 20 · CA 18 · FI 9 · NO 8 · FR 8 · AU 3 · LV 1 · ES 1 |
| G70 | US 3,792 · KR 137 · JP 40 · CA 8 · GB 8 · FR 3 · AU 2 · DK 2 · SE 2 · FI 2 · ZA 2 · NO 1 · ES 1 |

Implications (observed):

- **No China feedback at all**, and **no German feedback** in any file.
- **G60/G70 feedback is ~90 % US.** Europe is thin (GB/SE/DK/FR/FI/NO/ES/LV, a few dozen per vehicle).
- **F70 has no US feedback.** That matches sales: the 1 Series is not sold in the US or China ([sales-volumes.md](sales-volumes.md)). For F70, Europe here means mainly GB, plus SE/FR/DK/FI.

### Powertrains (unique feedbacks)

| Vehicle | ICE | PHEV | BEVE |
| --- | ---: | ---: | ---: |
| F70 | 2,128 | – | – |
| G60 | 2,259 | 378 | 1,363 |
| G70 | 2,568 | 303 | 1,129 |

## Classification (VFC)

### `Feedback Type` → `Vfc level3 Name`

Rows per Feedback Type:

| Feedback Type | F70 | G60 | G70 |
| --- | ---: | ---: | ---: |
| Likes | 1,630 | 1,951 | 1,890 |
| Difficult to Use | 595 | 1,306 | 1,119 |
| Defect | 491 | 435 | 481 |
| Wants | 273 | 582 | 518 |
| *(empty)* | 1,087 | 731 | 682 |

Level-3 values that occur under each type (all files combined):

- **Likes:** Like: function · Like: performance · Like: Efficiency · Like: usability · Like: Range · Like: Space / spatial impression · Like: storage space · Like: sound · Like: odor · Like: responsiveness · Like: price-performance ratio · Like: vehicle equipment · Like: view/panoramic view · Likes comfort · Likes size · Look / design appeals · Workmanship appeals
- **Wants:** Customer request: function / usability / comfort / compatibility / design / material quality / performance / size / sound / space / spatial impression · Dislike: price-performance ratio · Vehicle equipment: not available · Vehicle equipment: not standard / too costly · Permanent switch-off not possible · Workmanship does not appeal · too few
- **Difficult to Use:** Not user-friendly · Size not user friendly · Ergonomics do not appeal · Information / accuracy insufficient (incl. "(electric range)") · Range, not OK · Charging infrastructure inadequate · Fuel / power consumption too high · Drive power/driving performance not OK · Response characteristics (not OK / too fast / too jerky / too sluggish) · Shift characteristics not OK · insufficient storage space · View/restricted panoramic view · Not comfortable · Installation and set-up: difficult · Accidental triggering · Switch off not possible · Too slow · Noise · Malfunction · Connection fault · … (34 values)
- **Defect:** Malfunction · Damage · Noise · Wind noise · Vibration, oscillation · Battery discharge · Capacity loss · Blank / frozen screen · Connection fault · Communication fault · Leak (air / water ingress) · Odor/smoke · Opening, closing: not possible · Warning / notification active · Pulls to one side · … (25 values)

> **Wants is the most direct "unmet need" signal**, while Difficult to Use and Defect are the pain points. Note that some "Customer request: …" labels also appear under Difficult to Use.

### Unclassified rows

| Case | F70 | G60 | G70 | Notes |
| --- | ---: | ---: | ---: | --- |
| `Vfc level2 Name = no_class_found`, Feedback Type empty | 1,087 | 525 | 470 | The classifier found no topic. **The text is still usable**, e.g. general praise. |
| `Vfc level2 Name` empty, Feedback Type empty | 0 | 200 | 200 | Only Sources C and D: open survey answers that were never classified |
| Feedback Type empty but level3 = `Not user-friendly` | 0 | 6 | 12 | Minor inconsistency |

### Most frequent topics (`Vfc level2 Name`, rows, excluding unclassified)

| # | F70 | G60 | G70 |
| ---: | --- | --- | --- |
| 1 | Drivetrain (548) | Drivetrain (419) | Drivetrain (352) |
| 2 | Drive, driving dynamics and chassis, overall technology (475) | Handling / Riding (227) | Handling / Riding (249) |
| 3 | Handling / Riding (216) | Body equipment, overall technology (213) | Exterior design (178) |
| 4 | Touch screen, operation (154) | Exterior design (157) | Body equipment, overall technology (173) |
| 5 | ConnectedDrive and Infotainment, overall technology (128) | Drive, driving dynamics and chassis, overall technology (126) | Interior design (111) |
| 6 | Body equipment, overall technology (100) | Seats (105) | Seats (103) |
| 7 | Seats (98) | Interior design (101) | Drive, driving dynamics and chassis, overall technology (91) |
| 8 | Owner's Manual (66) | Electric Range (96) | Interior comfort (71) |
| 9 | Impression of safety (59) | Touch screen, operation (72) | ConnectedDrive and Infotainment, overall technology (67) |
| 10 | Exterior design (56) | My Modes / driving experience (59) | Exterior (60) |

Other notable topics: *G60:* Operating concept / operating system, Public charging / external providers, Apple CarPlay, non-contact trunk lid opening, Highway assistant, Ambient light. *G70:* Automatic doors, Rear seat entertainment, Personal eSIM, Panorama glass roof, Space / spatial impression, Highway assistant.

## Example rows (shortened)

| ID | Source | Country | Engine | Feedback Type | Level 2 : Level 3 | Text |
| --- | --- | --- | --- | --- | --- | --- |
| F70-0002 | A | GB | ICE | Likes | Body equipment, overall technology : Workmanship appeals | "really solid build, lots of attention to detail. i only knock off one mark because there's no paper user manual." |
| F70-0002 | A | GB | ICE | Difficult to Use | Owner's Manual : Not user-friendly | *(same text: the second classification of the same feedback)* |
| G60-0002 | B | US | ICE | Likes | Interior acoustics : Like: sound | "Customer stated the vehicle provides a quiet, peaceful ride." |
| G70-0004 | B | US | BEVE | Wants | Audio mode, sound : Customer request: function | "Customer stated that at higher volume levels, the Bowers & Wilkins Diamond Surro…" |

## Gotchas for the pipeline

- De-duplicate by `ID` before any text analysis (embeddings, LLM extraction) and keep the classification rows as labels.
- `Source` affects how to read the text: B is second-hand paraphrase ("Customer stated…"), while C and D wrap the answer in survey boilerplate that should be stripped.
- Source C encodes **severity** in the text ("very minor problem" … "very serious problem"), which could feed into scoring.
- Countries are very unbalanced. Any market-level claim needs the counts shown next to it, and statements about China cannot be backed by feedback.
- The VFC taxonomy (226 topics × 84 natures across all files) is BMW's own classification. It can serve as a starting cluster structure or as ground truth for checking our own clustering.
