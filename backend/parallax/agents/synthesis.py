"""Synthesizer: crystallizes market twin, company twin, research and scores into one PM brief."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from parallax.config import get_settings
from parallax.llm.client import LLMClient, to_json
from parallax.llm.prompts import SAFETY, SCOPE, UNITS
from parallax.models import Requirement

PROMPT_VERSION = "synthesis-v1"


class MarketView(BaseModel):
    market: str
    summary: str
    simulated_importance_0_5: float | None
    observed_evidence: Literal["strong", "moderate", "weak", "none"]


class Conflict(BaseModel):
    between: str = Field(description="e.g. 'US personas vs Engineering'")
    description: str


class Tension(BaseModel):
    topic: str
    customers_say: str = Field(description="What the customer council says, with markets.")
    company_says: str = Field(description="What the company council says, naming departments.")
    resolution_options: list[str]


class SynthesisOut(BaseModel):
    headline: str = Field(description="One sentence the PM can read first.")
    customer_view: str = Field(description="The customer council in 2-3 sentences: who wants it, who does not, budget share.")
    company_view: str = Field(description="The company council in 2-3 sentences: which departments are for/against and why.")
    tensions: list[Tension] = Field(description="Where customers and company disagree, e.g. 'everyone wants it, Finance: too expensive'.")
    market_views: list[MarketView]
    internal_view: str = Field(description="What the departments think, including disagreements.")
    research_view: str = Field(description="What verified research adds; say if nothing was verified.")
    conflicts: list[Conflict]
    assumptions: list[str] = Field(description="Forward-looking assumptions (3-5 year horizon).")
    uncertainties: list[str]
    evidence_vs_simulation: str = Field(description="Which conclusions rest on real evidence and which only on simulation.")
    suggested_requirement_edit: str | None
    acceptance_criteria_suggestions: list[str] = Field(description="Customer-facing, measurable only if evidence supports it.")
    clinic_questions: list[str] = Field(description="Questions worth testing in a customer clinic or conjoint study; "
                                                    "the app prepares them, it does not replace them.")
    prioritization_rationale: str
    recommended_next_action: Literal["pm_review", "investigate", "defer"]


SYSTEM = f"""\
You prepare a decision brief for a BMW product manager. You receive a proposed customer requirement,
deterministic evidence counts, real owner quotes, simulated owner reactions (market twin), simulated
department memos (company twin), verified/unverified web research, multi-criteria scores with bounds
and gate states, and lessons from earlier PM decisions on similar topics.
Rules: keep real evidence and simulation strictly apart; simulated reactions are hypotheses, never
evidence. Unverified research must not be presented as fact. Name conflicts explicitly. The PM decides;
you only recommend a next action.
{SCOPE}
{UNITS}
{SAFETY}"""


def synthesize(llm: LLMClient, requirement: Requirement, package: dict, evidence_record_ids: list[str],
               run_id: uuid.UUID) -> SynthesisOut:
    settings = get_settings()

    def mock(rng):
        markets = package.get("market_twin", {}).keys() or ["US", "EU", "CN"]
        return SynthesisOut(
            headline=f"[mock] {requirement.title}: mixed signals, PM review recommended.",
            customer_view="[mock] US and EU owners want it; China is lukewarm.",
            company_view="[mock] Engineering for, Finance against (too expensive).",
            tensions=[Tension(topic="cost vs demand", customers_say="[mock] most owners call it a must-have",
                              company_says="[mock] Finance: too expensive for the volume", resolution_options=["[mock] option"])],
            market_views=[MarketView(market=m, summary=f"[mock] {m} view", simulated_importance_0_5=round(rng.uniform(1, 4), 2),
                                     observed_evidence=rng.choice(["strong", "moderate", "weak", "none"])) for m in markets],
            internal_view="[mock] Engineering sees moderate effort; Sales sees good fit in CN.",
            research_view="[mock] Nothing verified in mock mode.",
            conflicts=[Conflict(between="US personas vs Finance", description="[mock] value vs effort")],
            assumptions=["[mock] Customers in 2030 expect this as standard."],
            uncertainties=["[mock] No China feedback; CN view is simulated only."],
            evidence_vs_simulation="[mock] Demand rests on real reviews; importance in CN is simulated.",
            suggested_requirement_edit=None, acceptance_criteria_suggestions=["[mock] criterion"],
            clinic_questions=["[mock] Would you pay extra for this in your next 5 Series?"],
            prioritization_rationale="[mock] High observed demand, uncertain delivery fit.",
            recommended_next_action=rng.choice(["pm_review", "investigate"]),
        )

    return llm.structured(SynthesisOut, system=SYSTEM, user="Decision package:\n" + to_json(package),
                          model=settings.model_strong, purpose="synthesis", prompt_version=PROMPT_VERSION,
                          agent_id="agent:synthesizer", run_id=run_id, requirement_id=requirement.id,
                          input_record_ids=evidence_record_ids, mock=mock)
