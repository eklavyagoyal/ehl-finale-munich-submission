# Datasets

Documentation of the data BMW provided for the challenge: schemas, value distributions, coverage and quirks.

> **The raw files are not in git.** They live locally in `/data/` (ignored via `.gitignore`). Download them from the BMW challenge Google Drive folder:
> <https://drive.google.com/drive/folders/1AyPzFu7qoNuCTW0tqlBCJggbmG_MZUem>
> These docs describe the files and show only short examples, no raw dumps (except the small sales and CN/EU study tables).

## Inventory

| Dataset (BMW name) | File in `data/` | Size | Vehicles | Doc |
| --- | --- | ---: | --- | --- |
| Customer verbatims | `F70_feedback_hackathon.xlsx` | 472 KB | 1 Series F70 | [customer-feedback.md](customer-feedback.md) |
| | `G60_feedback_hackathon.xlsx` | 706 KB | 5 Series G60 | 〃 |
| | `G70_feedback_hackathon.xlsx` | 615 KB | 7 Series G70 | 〃 |
| Customer study | `F70_G60_G68_G70_customer_studies.xlsx` | 52 KB | F70, G60, G68, G70 | [customer-studies.md](customer-studies.md) |
| Sales volumes | `sales_volumes.xlsx` | 22 KB | F70, G60+G68, G70 | [sales-volumes.md](sales-volumes.md) |
| Equipment list | `F70_OptionList.PDF` | 1.8 MB | 1 Series F70 | [option-lists/F70-1-series.md](option-lists/F70-1-series.md) |
| | `G60_OptionList.PDF` | 2.4 MB | 5 Series sedan G60 | [option-lists/G60-5-series.md](option-lists/G60-5-series.md) |
| | `G70_OptionList.PDF` | 2.2 MB | 7 Series G70 | [option-lists/G70-7-series.md](option-lists/G70-7-series.md) |

## Vehicle codes

| E-code | Vehicle | Where it appears |
| --- | --- | --- |
| F70 | BMW 1 Series (5-door hatch, ICE only in the data) | feedback, study (EU), sales, option list |
| G60 | BMW 5 Series sedan (ICE, PHEV, BEV i5) | feedback, study (EU, US), sales (with G68), option list |
| G68 | BMW 5 Series long wheelbase (China) | study (CN) and sales (combined with G60) only |
| G70 | BMW 7 Series (ICE, PHEV, BEV i7) | feedback, study (CN, EU, US), sales, option list |

## Coverage at a glance

| | EU | CN | US |
| --- | --- | --- | --- |
| **F70** | sales · study · feedback (mostly GB) | no sales | no sales |
| **G60 / G68** | sales · study (G60) · thin feedback | sales · study (G68) · **no feedback** | sales · study (G60) · **rich feedback** |
| **G70** | sales · study · thin feedback | sales · study · **no feedback** | sales · study · **rich feedback** |

Details and demo-scope implications: [sales-volumes.md](sales-volumes.md#data-coverage-by-vehicle-and-market).

## Key quirks (read before building on the data)

1. **Feedback files have one row per classification.** Count unique `ID`s, not rows (F70: 4,076 rows → 2,128 feedbacks).
2. **No China and no German customer feedback.** US dominates G60/G70 feedback (~90 %).
3. **Sources B, C and D are US-only**, and F70 has only Source A. BMW does not say what the sources are; [our reading](customer-feedback.md#feedback-sources).
4. **The two study sheets use different scales** (CN/EU: means, inferred 10-point; US: 7-point distributions). No sample sizes are given.
5. **Sales volumes have no powertrain split**, despite the BMW slide describing it that way. 5 Series G60 and G68 are combined.
6. **Option lists are German-market catalogs (July 2026, EUR, in German).** Other markets' equipment is not provided. Pricing is out of scope; standard vs optional per trim is the useful signal.
   - F70: 6 models (4 petrol, 2 diesel; no PHEV/BEV), 68 option codes.
   - G60: 10 models (i5 BEV, 530e/550e PHEV, mild-hybrid petrol/diesel), 79 codes.
   - G70: 7 models, 92 codes. **Its equipment tables cover only 4 models** (i7 50xDrive, i7 60xDrive, 740 xDrive, i7 M70 xDrive); 750e, M760e and 740d are listed as "available from November" without equipment data.
   - Each file ends with *Extraction notes*: contradictions inside the catalogs and cells marked `?`. Check them before relying on a single cell.

## Using the data locally

```bash
python3 -m venv .venv && .venv/bin/pip install pandas openpyxl
```

```python
import pandas as pd
fb = pd.read_excel("data/G60_feedback_hackathon.xlsx", dtype=str)
feedbacks = fb.drop_duplicates("ID")          # one row per verbatim
labels = fb[["ID", "Feedback Type", "Vfc level2 Name", "Vfc level3 Name"]]
```
