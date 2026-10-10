"""Persona validation against a source the persona never saw.

US personas: grounded on verbatims, checked against the US_2025 G60 study (distributions).
EU personas: grounded on verbatims, checked against the CN_EU_2025 study, EU G60 column (means).
CN personas: grounded on the G68 China study itself, so no independent check exists -> assumption.

Procedure: the persona describes, in its own words, how satisfied it is with each study attribute of
its current car; SSR turns the text into a 1-5 rating; Spearman rank correlation with the study.
A demographics-only twin (same persona, no grounding) is the baseline: grounding must add signal.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.agents.grounding import Grounding, persona_grounding
from parallax.agents.market_twin import INSTRUCTIONS, persona_profile
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.llm import ssr
from parallax.llm.client import LLMClient
from parallax.models import Agent, Record, Source
from parallax.policy import active_policy

PROMPT_VERSION = "persona-validation-v1"
US_SCALE = ["I Hate It", "A Failure", "Unsatisfactory", "Satisfactory", "Excellent", "Delightful", "I Love It"]
SATISFACTION_ANCHORS = [[
    "I am very unhappy with this on my car.",
    "This is somewhat disappointing on my car.",
    "This is okay on my car, nothing special.",
    "I am happy with this on my car.",
    "This is outstanding on my car, I love it.",
]]


class AttributeReaction(BaseModel):
    attribute: str
    reaction: str = Field(description="One or two sentences in first person about your current car.")


class AttributeReactions(BaseModel):
    reactions: list[AttributeReaction]


def reference_values(session: Session, reference: dict) -> dict[str, float]:
    """Attribute -> reference satisfaction. Means are used directly; distributions over the US
    7-point scale (one proportion record per scale point, name 'Attribute | Scale label' or
    'Attribute :: Scale label') become a weighted mean. Adjust once the BMW batch format is final."""
    rows = session.execute(
        select(Record).join(Source, Source.source_id == Record.source_id)
        .where(Record.record_kind == "metric", Source.channel == reference["channel"], Record.superseded_by.is_(None))
    ).scalars().all()
    values: dict[str, float] = {}
    distributions: dict[str, dict[str, float]] = {}
    for record in rows:
        if reference["subject_id"] not in (record.subject_ids or []):
            continue
        if not set(reference["markets"]) & set(record.markets or []):
            continue
        metric = record.metric or {}
        name = (metric.get("name") or "").strip()
        if metric.get("statistic") == "mean":
            values[name] = float(metric["value"])
            continue
        for separator in (" | ", " :: ", " - "):
            if separator in name:
                attribute, label = name.rsplit(separator, 1)
                if label.strip() in US_SCALE:
                    share = float(metric["value"]) / (100.0 if metric.get("statistic") == "percentage" else 1.0)
                    distributions.setdefault(attribute.strip(), {})[label.strip()] = share
                break
    for attribute, dist in distributions.items():
        total = sum(dist.values())
        if total > 0:
            values[attribute] = sum((US_SCALE.index(label) + 1) * share for label, share in dist.items()) / total
    return values


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                result[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return result

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if vx == 0 or vy == 0 else round(cov / (vx * vy), 3)


def _rate_attributes(llm: LLMClient, agent: Agent, grounding: Grounding | None, attributes: list[str],
                     run_id: uuid.UUID, label: str) -> list[float]:
    settings = get_settings()
    system = INSTRUCTIONS + "\n\n" + persona_profile(agent, grounding)
    user = ("Think about your current car. For EACH aspect below, say in one or two sentences how satisfied you are "
            "with it on your car and why.\n" + "\n".join(f"- {a}" for a in attributes))

    def mock(rng):
        return AttributeReactions(reactions=[AttributeReaction(attribute=a, reaction=rng.choice([
            "I am happy with this on my car.", "This is okay, nothing special.", "Honestly a bit disappointing.",
            "Outstanding, I love it."])) for a in attributes])

    out = llm.structured(AttributeReactions, system=system, user=user, model=settings.model_fast,
                         purpose=f"persona_validation_{label}", prompt_version=PROMPT_VERSION, agent_id=agent.id,
                         run_id=run_id, input_record_ids=grounding.record_ids if grounding else [], mock=mock)
    by_attribute = {r.attribute.strip().lower(): r.reaction for r in out.reactions}
    texts = [by_attribute.get(a.lower(), "no answer") for a in attributes]
    return [r["mean"] for r in ssr.rate(llm, texts, SATISFACTION_ANCHORS, run_id=run_id, agent_id=agent.id)]


def validate_persona(session: Session, llm: LLMClient, agent: Agent, run_id: uuid.UUID, actor_id: str,
                     include_examples: bool = False) -> dict:
    policy = active_policy(session).document
    thresholds = policy["parallax"]["persona_validation"]
    path = agent.spec.get("validation", {}).get("path", "none")
    if path == "none":
        result = {"status": "unvalidated_assumption", "path": path,
                  "reason": agent.spec.get("validation", {}).get("note", "No independent reference data.")}
    else:
        reference = reference_values(session, agent.spec["validation"]["reference"])
        attributes = sorted(reference)[:20]
        if len(attributes) < thresholds["min_attributes"]:
            result = {"status": "not_validated", "path": path, "reason":
                      f"Only {len(attributes)} reference attributes available (need {thresholds['min_attributes']}); "
                      "ingest the BMW customer-study batch first."}
        else:
            grounding = persona_grounding(session, agent, policy, get_settings().grounding_quotes_per_persona, include_examples)
            grounded = _rate_attributes(llm, agent, grounding, attributes, run_id, "grounded")
            baseline = _rate_attributes(llm, agent, None, attributes, run_id, "baseline")
            truth = [reference[a] for a in attributes]
            rho = spearman(grounded, truth)
            rho_base = spearman(baseline, truth)
            lift = None if rho is None or rho_base is None else round(rho - rho_base, 3)
            if rho is None:
                status = "failed"
            elif rho >= thresholds["validated_min_rho"] and (lift or 0) > 0:
                status = "validated"
            elif rho >= thresholds["weak_min_rho"]:
                status = "weak"
            else:
                status = "failed"
            result = {"status": status, "path": path, "n_attributes": len(attributes), "rho_grounded": rho,
                      "rho_baseline_demographics_only": rho_base, "lift": lift, "grounding_quotes": len(grounding.quotes),
                      "grounding_gate": grounding.gate,
                      "per_attribute": [{"attribute": a, "reference": round(t, 3), "grounded": round(g, 3), "baseline": round(b, 3)}
                                        for a, t, g, b in zip(attributes, truth, grounded, baseline)],
                      "note": "Spearman rank correlation; reference data never shown to the persona."}
    before = {"validation_status": agent.validation_status}
    agent.validation_status = result["status"]
    agent.validation_metrics = {**result, "agent_version": agent.version, "run_id": str(run_id)}
    record_event(session, category="ai", actor_id=actor_id, action="agent.validate", entity_type="agent", entity_id=agent.id,
                 run_id=run_id, before=before, after={"validation_status": result["status"]},
                 meta={k: v for k, v in result.items() if k != "per_attribute"})
    return result


ValidationStatus = Literal["validated", "weak", "failed", "not_validated", "unvalidated_assumption"]
