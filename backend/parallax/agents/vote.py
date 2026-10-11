"""Judge panel: heterogeneous models vote independently (no debate, which tends to herd).
Majority wins; ties and gate problems cap the outcome. The result is a recommendation to the PM."""

import uuid
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from parallax.llm.client import LLMClient, to_json
from parallax.llm.prompts import SAFETY, SCOPE
from parallax.models import Requirement

PROMPT_VERSION = "vote-v1"


class Driver(BaseModel):
    source: Literal["evidence", "customers", "company", "research", "scores", "challenger", "gates"]
    statement: str = Field(description="What this input says, one sentence with numbers where available.")
    effect: Literal["supports", "against", "neutral"] = Field(description="Effect on approving the requirement now.")
    weight: Literal["high", "medium", "low"]


class VoteOut(BaseModel):
    vote: Literal["approve", "reject", "investigate", "defer"]
    rationale: str = Field(description="3-5 sentences.")
    key_points: list[str]
    drivers: list[Driver] = Field(description="3-6 inputs that drove the vote, most important first.")
    what_would_change_it: str = Field(description="The evidence or decision that would flip the vote.")


SYSTEM = f"""\
You are one independent judge on a panel advising a BMW product manager. Vote on whether the
requirement should be recommended for approval now (approve), dropped (reject), needs more evidence
first (investigate), or should wait for a later cycle (defer). Name the drivers of your vote explicitly:
which input (evidence counts, customer council budget/verdicts, company tensions, research, scores,
challenger, gates) pushed in which direction, so the PM can trace the decision. Base your vote on real evidence first;
treat simulated owner and department views as hypotheses. A challenger's strongest counter-case is
included under "challenge": weigh it explicitly and say in your rationale whether it changes your vote.
Your vote is advice; the PM decides.
{SCOPE}
{SAFETY}"""


def cast(llm: LLMClient, judge_id: str, model: str, requirement: Requirement, package: dict,
         evidence_record_ids: list[str], run_id: uuid.UUID) -> VoteOut:
    def mock(rng):
        return VoteOut(vote=rng.choice(["approve", "approve", "investigate", "reject"]),
                       rationale=f"[mock] {judge_id} rationale", key_points=["[mock] point"],
                       drivers=[Driver(source="evidence", statement="[mock] 39 complaint reviews", effect="supports", weight="high"),
                                Driver(source="customers", statement="[mock] 5/100 budget", effect="against", weight="high"),
                                Driver(source="challenger", statement="[mock] narrow evidence", effect="against", weight="medium")],
                       what_would_change_it="[mock] clinic result")

    return llm.structured(VoteOut, system=SYSTEM, user="Decision package:\n" + to_json(package), model=model,
                          purpose="vote", prompt_version=PROMPT_VERSION, agent_id=judge_id, run_id=run_id,
                          requirement_id=requirement.id, input_record_ids=evidence_record_ids, mock=mock)


def tally(votes: list[tuple[str, VoteOut]], gates: dict[str, str], tie_breaker: str = "investigate") -> dict:
    counts = Counter(v.vote for _, v in votes)
    ranked = counts.most_common()
    if not ranked:
        outcome, reason = tie_breaker, "no votes"
    elif len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        outcome, reason = tie_breaker, "tie"
    else:
        outcome, reason = ranked[0][0], "majority"
    blocking = {g: v for g, v in gates.items() if g != "pm_review"}
    cap = None
    if outcome == "approve" and "fail" in blocking.values():
        outcome, cap = "defer", "a gate failed; gate policy: defer or reject with reason"
    elif outcome == "approve" and "unknown" in blocking.values():
        outcome, cap = "investigate", "a gate is unknown; gate policy: investigate before commitment"
    minority = [{"judge": j, "vote": v.vote, "rationale": v.rationale} for j, v in votes if v.vote != ranked[0][0]] if ranked else []
    return {"recommendation": outcome, "counts": dict(counts), "reason": reason, "gate_cap": cap, "minority": minority}


class ChallengeOut(BaseModel):
    counter_position: str = Field(description="One sentence: the strongest case against the panel's outcome.")
    strongest_arguments: list[str]
    overlooked_segments: list[str] = Field(description="Markets, personas or departments whose view argues against the outcome.")
    evidence_that_would_change_the_call: list[str]
    risk_if_outcome_is_wrong: Literal["low", "medium", "high"]


CHALLENGER_SYSTEM = f"""\
You are the challenger (devil's advocate) for a BMW product decision. The synthesis proposes a next
action; your job is to make the strongest honest case AGAINST it before the judges vote, so they and
the product manager see what could make it wrong: weak or one-sided evidence, segments that disagree,
simulated views mistaken for evidence, unverified research, open gates. Do not invent facts. If the
proposal is well supported, say so and keep the risk low.
{SCOPE}
{SAFETY}"""


def challenge(llm: LLMClient, requirement: Requirement, package: dict, outcome: dict, evidence_record_ids: list[str],
              run_id: uuid.UUID, model: str) -> ChallengeOut:
    def mock(rng):
        return ChallengeOut(
            counter_position=f"[mock] '{outcome.get('proposed_next_action')}' rests on simulated views more than on evidence.",
            strongest_arguments=["[mock] Few direct target-model reviews", "[mock] CN view is assumption only"],
            overlooked_segments=["[mock] persona:cn-lwb-chauffeur-owner"],
            evidence_that_would_change_the_call=["[mock] Clinic result for rear-seat users"],
            risk_if_outcome_is_wrong=rng.choice(["low", "medium", "high"]),
        )

    user = "Proposal to challenge:\n" + to_json(outcome) + "\n\nDecision package:\n" + to_json(package)
    return llm.structured(ChallengeOut, system=CHALLENGER_SYSTEM, user=user, model=model, purpose="challenge",
                          prompt_version="challenger-v1", agent_id="agent:challenger", run_id=run_id,
                          requirement_id=requirement.id, input_record_ids=evidence_record_ids, mock=mock)
