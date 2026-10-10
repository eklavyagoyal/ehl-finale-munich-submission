# Customer study: `F70_G60_G68_G70_customer_studies.xlsx`

Customer ratings of the current vehicles across many attributes (2025). There are two sheets with **different layouts and scales**:

| Sheet | Markets | Vehicles | Attributes | Measure |
| --- | --- | --- | ---: | --- |
| `CN_EU_2025` | China, EU | CN: 5 Series **G68**, 7 Series G70 · EU: 1 Series F70, 5 Series G60, 7 Series G70 | 36 + overall satisfaction | **Mean score** per attribute (values 6.5–9.9; inferred 1–10 scale) |
| `US_2025` | USA | 5 Series G60, 7 Series G70 | 103 | **Distribution** (% of respondents) over a 7-point scale |

Observed coverage:

- **G68** (5 Series long wheelbase) appears **only here and only for China**. China has no G60 and no F70.
- **F70** appears only in the EU column. There is no US study for the 1 Series, which is consistent with zero US sales.
- **Sample sizes are not given** in either sheet. The US "Sample total" row is always 1 (100 %).

## Sheet `CN_EU_2025`

Layout quirks (observed): wide format with stacked header rows. Row 2 holds the country (`China` over columns B–C, `EU` over columns D–F), and row 3 holds the vehicle names. Each attribute is a label row followed by a `Mean` row. Numbers are stored as text in the first rows, so cast them to float when reading.

### Mean scores (rounded)

| Attribute | CN · 5 Series G68 | CN · 7 Series G70 | EU · 1 Series F70 | EU · 5 Series G60 | EU · 7 Series G70 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Overall product satisfaction** | **8.77** | **9.64** | **8.46** | **8.32** | **7.98** |
| Exterior styling | 8.19 | 8.79 | 9.01 | 9.83 | 8.38 |
| Interior styling | 8.69 | 8.57 | 8.90 | 8.55 | 8.92 |
| Quality of interior and materials used | 8.44 | 8.43 | 8.65 | 7.75 | 9.11 |
| Level of equipment | 7.49 | 9.82 | 8.26 | 7.77 | 9.24 |
| Safety | 8.17 | 8.97 | 9.03 | 9.15 | 9.28 |
| Freedom from faults/ squeaks/ rattles | 8.48 | 8.44 | 8.86 | 8.41 | 8.61 |
| Value for money | 7.92 | 8.29 | 7.82 | 7.36 | 6.47 |
| Reliability | 8.84 | 8.22 | 9.40 | 9.25 | 9.67 |
| All round visibility | 8.70 | 8.43 | 8.89 | 8.64 | 8.30 |
| Easy to read and use instruments/ controls/ displays | 8.34 | 8.43 | 8.41 | 8.07 | 8.19 |
| Smartphone integration/ connectivity | 8.14 | 8.43 | 8.59 | 8.46 | 8.36 |
| Features of information and entertainment system including in-car apps | 8.37 | 8.21 | 8.23 | 8.19 | 8.29 |
| Easy to use information and entertainment system including in-car apps | 8.35 | 8.10 | 8.16 | 8.26 | 7.99 |
| Integrated navigation system | 8.52 | 8.18 | 8.30 | 8.59 | 8.82 |
| Overall seating comfort | 8.67 | 8.72 | 8.98 | 8.81 | 9.29 |
| Interior storage for small items | 8.53 | 8.41 | 8.10 | 7.72 | 7.96 |
| Acceleration | 8.60 | 8.83 | 8.21 | 8.85 | 8.94 |
| Roadholding | 8.92 | 8.60 | 8.29 | 8.15 | 8.94 |
| Fuel economy/ energy efficiency | 8.43 | 8.18 | 9.30 | 7.45 | 7.68 |
| Braking | 7.38 | 7.82 | 8.89 | 8.25 | 9.60 |
| Sportiness | 8.86 | 8.64 | 9.34 | 7.64 | 6.97 |
| Prestige/ manufacturer reputation | 8.90 | 9.17 | 9.21 | 8.95 | 9.23 |
| Manoeuvrability | 8.48 | 8.38 | 8.87 | 8.73 | 8.97 |
| Quality of ride | 8.45 | 8.62 | 9.20 | 9.95 | 9.52 |
| Front interior roominess | 7.77 | 7.69 | 9.20 | 8.88 | 9.69 |
| Rear interior roominess | 8.71 | 7.52 | 8.59 | 7.46 | 9.41 |
| Ease of loading/ unloading luggage | 7.25 | 7.46 | 7.50 | 7.24 | 8.67 |
| Luggage capacity | 8.73 | 7.66 | 7.07 | 7.54 | 7.41 |
| Ease of entry into and out of car | 8.51 | 8.71 | 8.76 | 7.91 | 9.25 |
| Environm. friendliness | 7.49 | 7.44 | 7.55 | 7.59 | 7.51 |
| Heating/ ventilation/ air conditioning | 7.58 | 8.82 | 7.30 | 7.47 | 8.80 |
| Overall build quality | 8.81 | 9.36 | 7.95 | 7.67 | 8.78 |
| Quietness when driving | 7.52 | 9.39 | 7.62 | 7.79 | 9.78 |
| Driving position | 8.69 | 8.80 | 9.18 | 9.17 | 9.13 |
| Connected services | 7.35 | 7.32 | 7.36 | 7.37 | 7.86 |
| Interior versatility | 8.35 | 8.04 | 8.57 | 8.14 | 8.32 |

### Lowest- and highest-rated attributes per column (observed)

| Column | Lowest 4 | Highest 3 |
| --- | --- | --- |
| CN · G68 | Ease of loading luggage 7.25 · Connected services 7.35 · Braking 7.38 · Level of equipment 7.49 | Sportiness 8.86 · Prestige 8.90 · Roadholding 8.92 |
| CN · G70 | Connected services 7.32 · Environm. friendliness 7.44 · Ease of loading luggage 7.46 · Rear roominess 7.52 | Build quality 9.36 · Quietness 9.39 · Level of equipment 9.82 |
| EU · F70 | Luggage capacity 7.07 · HVAC 7.30 · Connected services 7.36 · Ease of loading luggage 7.50 | Fuel economy 9.30 · Sportiness 9.34 · Reliability 9.40 |
| EU · G60 | Ease of loading luggage 7.24 · Value for money 7.36 · Connected services 7.37 · Fuel economy 7.45 | Reliability 9.25 · Exterior styling 9.83 · Quality of ride 9.95 |
| EU · G70 | Value for money 6.47 · Sportiness 6.97 · Luggage capacity 7.41 · Environm. friendliness 7.51 | Reliability 9.67 · Front roominess 9.69 · Quietness 9.78 |

Patterns across all five columns: **Connected services** (7.3–7.9), **Environmental friendliness** (7.4–7.6) and **luggage loading/capacity** sit near the bottom in every column.

## Sheet `US_2025`

Layout (observed): long format, 934 rows, columns `A` = label, `B` = `"% of column, sample base"`, `C` = **BMW 5 Series G60**, `D` = **BMW 7 Series G70** (the header label carries a trailing space: `'BMW 7 Series G70 '`). Vehicle headers appear only once, in row 1. Each attribute block has 9 rows:

```
<Attribute name>
Sample total      1       1
I Hate It         0.005   0.005
A Failure         0.007   0.011
Unsatisfactory    …
Satisfactory      …
Excellent         …
Delightful        …
I Love It         …        (each block sums to 1.0, verified)
```

**Scale (7-point):** I Hate It < A Failure < Unsatisfactory < Satisfactory < Excellent < Delightful < I Love It. Useful aggregates are the top-2 box (Delightful + I Love It), the bottom-3 box (I Hate It + A Failure + Unsatisfactory), or a weighted mean (1–7).

### The 103 attributes (in sheet order, grouped by us)

- **Exterior:** Overall exterior styling · Size/ proportions · Appearance of tires/ wheels · Exterior door handles · Headlight/ taillight design · Sound of doors/ trunk/ hatch shutting
- **Driving:** Overall driving performance · Ground clearance · Riding comfort · Turning radius · Handling/Maneuverability · If applicable: 4WD/AWD performance · Off-Road capability · Overall power and pickup · Acceleration from stop · Passing capability
- **Interior design & quality:** Overall interior styling/ aesthetics · Interior colors · Interior trim and finish · Interior lighting · Overall interior workmanship · Quality of seat materials · Quality of interior materials · Interior door handles
- **Seats, space & practicality:** Overall comfort of the seats · Comfort of front seat · Comfort of 2nd row seat · Overall interior design / layout · Ease of front seat entry · Front seat roominess · Ease of 2nd row seat entry · 2nd row seat roominess · Passenger seating capacity · Interior roominess · Interior storage · Trunk lid/ tailgate and liftgate operations · Ease of loading/unloading cargo · Cargo capacity/usefulness · Instrument panel (IP) · Cupholders · Provides a sense of wellbeing · Overall interior versatility/seat stowaway · Driver seat adjustability · Passenger seat adjustability
- **Climate & audio:** Overall performance of climate control system · Heater performance · Air conditioner performance · Operation of heater/ AC controls · Overall performance of sound system · Design and integration of speakers · Audio clarity · Bass performance
- **Controls, NVH & quality:** Placement/ ease of reading and using controls · Intuitiveness of controls · Overall noise/vibration/harshness · Overall vehicle sound · Active noise cancellation · Freedom from squeaks and rattles · Sound of engine · Freedom from wind and road noise · Smoothness of transmission · Overall impression of durability/reliability · Solid vehicle construction · Freedom from electrical problems
- **Safety & visibility:** Overall safety of the vehicle · Front visibility · Rear visibility · Braking · Warranty coverage · Headlight function/ brightness
- **Value & brand:** Technical innovations · Level of standard equipment · Overall value for money · Price/deal offered · Future trade-in or resale value · Gas or electric mileage (fuel economy) · Economical to own (cost of ownership) · Affordable to buy · Overall brand image · Reputation/prestige of manufacturer · Overall vehicle image
- **Driver assistance:** Overall driver assist features · If applicable: Backup system (camera, sensors, etc.) · Safety monitoring features (blind spot warning, lane departure warning, etc.) · Adaptive driving assists (lane keeping, cruise, braking)
- **HMI, infotainment & connectivity:** Overall driver-vehicle interaction (HMI) · If applicable: Navigation system · Bluetooth/ smartphone pairing · WiFi hotspot in vehicle · Mirroring of smartphone content on vehicle display · Place for phone · Phone charging · Ease of reading and using screen interface · Head-up Display · Position/ integration of displays in dashboard · Menu structure of infotainment system · If applicable: Interactive information system (e.g., OnStar, mbrace, iDrive) · Performance of voice recognition · Vehicle's Mobile App
- **Other:** Overall environmental friendliness · If applicable: Flat tire preparedness (spare, run flat, etc.) · If applicable: Sunroof/ moonroof · If applicable: Ease of customization

(The source spells "blid spot warning"; corrected above.)

## Gotchas for the pipeline

- The two sheets **cannot be compared directly**: CN/EU uses means on an inferred 10-point scale, the US uses distributions on a 7-point scale. Normalize within a sheet (rank, z-score, gap to the best vehicle) before combining.
- Attribute names differ between the sheets (e.g. "Quietness when driving" vs "Freedom from wind and road noise"), so a mapping table is needed to link them, and to link both to the feedback VFC topics.
- With no sample sizes, report study results as relative signals, not statistically tested ones.
