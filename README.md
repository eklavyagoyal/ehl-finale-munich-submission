# BMW hackathon

Start with the [challenge, datasets, and BMW interview](docs/README.md). Raw source files belong in the local ignored `data/` directory.

## Shared research handoff

Read [research/README.md](research/README.md) for the collection contract, templates, agent prompts, and validation commands. The [full design](docs/research-data-contract.md) explains evidence-to-claim links, counting rules, the initial LLM packet, and proposed decision criteria.

Give each workstream its prompt:

- [BMW workbook agent](research/prompts/agent-bmw.md)
- [Competitor research agent](research/prompts/agent-competitors.md)
- [Social and app-review agent](research/prompts/agent-social.md)

First collect one representative batch per workstream. Review scope and mappings before scaling, then build the context exporter and a PM-reviewed successor-vehicle demo for one model and market.

## Checks

With Python and `uv` available, run from the repository root:

```sh
uv run --with 'jsonschema[format]==4.26.0' python scripts/validate_research.py research/examples
uv run --with 'jsonschema[format]==4.26.0' python -m unittest discover -s tests -v
```

The examples are invented format fixtures, not research findings. Validate real collections by replacing `research/examples` with your submissions root.
