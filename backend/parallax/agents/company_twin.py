"""Company twin: department agents (design, engineering, sales, finance) review each requirement.

Departments work from the same requirement and evidence summary, in parallel and independently
of the market twin. Their criterion ratings are always low/high ranges with status "assumed":
an LLM cannot establish engineering feasibility, cost or competitor facts by intuition.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from parallax.config import get_settings
from parallax.llm.client import LLMClient, to_json
from parallax.llm.prompts import SAFETY, SCOPE, UNITS
from parallax.models import Agent, Requirement

PROMPT_VERSION = "company-twin-v1"

Criterion = Literal["demand", "impact", "competitive_gap", "vehicle_market_fit", "delivery_fit", "reuse"]


class RangeRating(BaseModel):
    criterion: Criterion
    low: float = Field(ge=0, le=5)
    high: float = Field(ge=0, le=5)
    rationale: str


class InfoRequest(BaseModel):
    question: str
    why: str


class DepartmentMemoOut(BaseModel):
    stance: Literal["support", "neutral", "oppose", "unsure"]
    summary: str = Field(description="3-5 sentences from the department's perspective.")
    criterion_ratings: list[RangeRating] = Field(description="Only the criteria this department owns; use wide ranges when unsure.")
    effort_band: Literal["low", "medium", "high", "unknown"]
    risks: list[str]
    conditions: list[str] = Field(description="What would need to be true for this to be a good idea.")
    info_requests: list[InfoRequest] = Field(default_factory=list, description="Facts worth researching on the web (max 2).")
    suggested_edit: str | None = Field(default=None, description="Optional sharper wording of the requirement.")


def department_system_prompt(agent: Agent) -> str:
    spec = agent.spec
    role = spec.get("role", {})
    owned = ", ".join(spec.get("criteria", []))
    must_not = "; ".join(spec.get("must_not", []))
    region = f"\nYou speak for the {spec['market']} market only; say so when the requirement matters elsewhere." if spec.get("market") else ""
    return f"""\
You are the {role.get('title')} in the {agent.display_name} department at BMW, reviewing a proposed
customer requirement for the successor of the BMW 5 Series (G60, G68 long wheelbase in China).{region}
Mandate: {role.get('mandate')}
Perspective: {role.get('perspective')}
You rate only these decision criteria (0-5 scale, give a low/high range): {owned}.
Never: {must_not}.
{SCOPE}
{UNITS}
{SAFETY}"""


def requirement_brief(requirement: Requirement, evidence: dict) -> str:
    return to_json({
        "requirement": {
            "id": requirement.id, "title": requirement.title, "description": requirement.description,
            "customer_problem": requirement.customer_problem, "market": requirement.market or "all focus markets",
            "target_model": requirement.target_model, "acceptance_criteria": requirement.acceptance_criteria,
        },
        "evidence_summary": evidence,
    })


def review(llm: LLMClient, agent: Agent, requirement: Requirement, evidence: dict, evidence_record_ids: list[str],
           run_id: uuid.UUID, challenge: str | None = None) -> DepartmentMemoOut:
    settings = get_settings()
    owned = agent.spec.get("criteria", [])
    user = "Review this requirement:\n" + requirement_brief(requirement, evidence)
    if challenge:
        user += f"\n\nThe product manager challenges the proposal with: {challenge}"

    def mock(rng):
        ratings = []
        for criterion in owned:
            low = round(rng.uniform(1, 3), 1)
            ratings.append(RangeRating(criterion=criterion, low=low, high=round(min(5, low + rng.uniform(0.5, 2)), 1),
                                       rationale=f"[mock] {agent.display_name} view on {criterion}"))
        return DepartmentMemoOut(
            stance=rng.choice(["support", "neutral", "oppose", "unsure"]),
            summary=f"[mock] {agent.display_name} assessment of {requirement.id}.",
            criterion_ratings=ratings, effort_band=rng.choice(["low", "medium", "high", "unknown"]),
            risks=["[mock] integration risk"], conditions=["[mock] validate with customer clinic"],
            info_requests=[InfoRequest(question=f"How do Mercedes E-Class and Audi A6 handle '{requirement.title}'?",
                                       why="competitive gap")] if rng.random() < 0.3 else [],
        )

    memo = llm.structured(
        DepartmentMemoOut, system=department_system_prompt(agent), user=user, model=settings.model_fast,
        purpose="department_review", prompt_version=PROMPT_VERSION, agent_id=agent.id, run_id=run_id,
        requirement_id=requirement.id, input_record_ids=evidence_record_ids, mock=mock,
    )
    # Departments may only rate what they own.
    memo.criterion_ratings = [r for r in memo.criterion_ratings if r.criterion in owned]
    for rating in memo.criterion_ratings:
        rating.low, rating.high = min(rating.low, rating.high), max(rating.low, rating.high)
    memo.info_requests = memo.info_requests[:2]
    return memo
