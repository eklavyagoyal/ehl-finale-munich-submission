# BMW hackathon

Start with the [challenge, datasets, and BMW interview](docs/README.md). Raw source files belong in the local ignored `data/` directory.

## Parallax (the app)

AI cockpit for BMW product managers: real customer feedback → signals → requirements → simulated customer and
company councils → recommendation → the PM decides. Live at https://parallax.dehlwes.net.

| Part | Where |
| --- | --- |
| Backend (FastAPI, Postgres, agents) | [backend/README.md](backend/README.md), API contract [backend/API.md](backend/API.md) |
| Frontend (Next.js PM cockpit) | [frontend/README.md](frontend/README.md), page structure [backend/UI_CONTRACT.md](backend/UI_CONTRACT.md) |
| BMW Excel → research batches | `scripts/export_bmw.py` |
| Scrapers (YouTube, app stores) | [scrapers/README.md](scrapers/README.md) |
| Competitor research | [competitors/](competitors/) |
| Validation plan for new sources | [backend/NEW_SOURCE_VALIDATION.md](backend/NEW_SOURCE_VALIDATION.md) |

## Shared research handoff

Read [research/README.md](research/README.md) for the collection contract, templates, agent prompts, and validation commands. The [full design](docs/research-data-contract.md) explains evidence-to-claim links, counting rules, the initial LLM packet, and proposed decision criteria.

Give each workstream its prompt:

- [BMW workbook agent](research/prompts/agent-bmw.md)
- [Competitor research agent](research/prompts/agent-competitors.md)
- [Social and app-review agent](research/prompts/agent-social.md)

First collect one representative batch per workstream. Review scope and mappings before scaling, then use the offline context exporter. The current working scope is G60 only, with evidence separated by market. Follow the [orchestrator checklist](research/INTEGRATION.md) to prepare the first synthesis and PM review.

## Checks

With Python and `uv` available, run from the repository root:

```sh
uv run --with 'jsonschema[format]==4.26.0' python scripts/validate_research.py research/examples
uv run --with 'jsonschema[format]==4.26.0' python scripts/build_research_context.py research/examples --demo
uv run --with 'jsonschema[format]==4.26.0' python -m unittest discover -s tests -v
```

The examples are invented format fixtures, not research findings. Validate real collections by replacing `research/examples` with your submissions root.
