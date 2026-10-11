# Docs

Everything we received from BMW for the EHL Munich 2026 final (TUM.ai): the challenge, the data and the conversation with BMW, sorted.

**Start here:** [challenge/brief.md](challenge/brief.md) holds the full challenge (mission, scope, deliverables, BMW's process) in one file.

## Structure

```
docs/
├── README.md                          ← you are here
├── challenge/
│   ├── brief.md                       ← THE challenge: briefing + mission text + slides, consolidated
│   └── sources/                       ← originals from BMW
│       ├── BMW_Hackathon_Briefing_Short.pdf
│       ├── slide-data-and-sources.png
│       ├── slide-billions-of-findings-to-one-vehicle.webp
│       └── slide-the-process.webp
├── datasets/                          ← what is in the provided data (raw files live in /data, not in git)
│   ├── README.md                      ← inventory, vehicle codes, coverage matrix, key quirks
│   ├── customer-feedback.md           ← *_feedback_hackathon.xlsx (verbatims + VFC classification)
│   ├── customer-studies.md            ← F70_G60_G68_G70_customer_studies.xlsx (CN/EU means, US distributions)
│   ├── sales-volumes.md               ← sales_volumes.xlsx (full tables)
│   └── option-lists/                  ← *_OptionList.PDF extracted to Markdown (DE price lists, July 2026)
│       ├── F70-1-series.md
│       ├── G60-5-series.md
│       └── G70-7-series.md
├── bmw-pm-interview/                  ← conversation with a BMW product manager
│   ├── conversation-with-bmw-prod-manager.md   ← raw notes
│   └── bmw-product-manager-groundwork.md       ← structured write-up
└── competitors/
    └── README.md                      ← 5 Series competitor analysis (EU/US/CN), findings and caveats; data in /competitors
```

## Where to find what

| Question | Go to |
| --- | --- |
| What exactly do we have to deliver? | [brief.md § 6 Deliverables](challenge/brief.md#6-deliverables) |
| Which fields does every requirement need? | [brief.md § 6.2](challenge/brief.md#62-expected-deliverables-s2-section-5) |
| What's in or out of scope? | [brief.md § 4 Scope](challenge/brief.md#4-scope-s2-section-2) |
| Where does BMW expect AI vs human review? | [brief.md § 9 Process](challenge/brief.md#9-bmws-requirements-process-s5) |
| How will we be judged? | [brief.md § 12 Evaluation criteria](challenge/brief.md#12-evaluation-criteria-s6) |
| What are PMs' real pain points? | [brief.md § 13](challenge/brief.md#13-pm-pain-points-and-the-process-timeline-s7) |
| Which vehicle/market has which data? | [datasets/README.md](datasets/README.md#coverage-at-a-glance) |
| How do BMW PMs actually prioritize? | [bmw-pm-interview/](bmw-pm-interview/bmw-product-manager-groundwork.md) |
| What does the car offer today (standard vs optional)? | [datasets/option-lists/](datasets/option-lists/) |
| Who are the 5 Series competitors and how do they compare? | [competitors/README.md](competitors/README.md) |

## Research collection handoff

Use [the data contract](research-data-contract.md) and [agent prompt index](../research/README.md) to prepare consistent, source-linked BMW, competitor, and social evidence batches.
