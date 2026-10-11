"""Research loop: an agent asks for a fact, the research agent searches the web, and a more
expensive verifier checks every claim against its source before it may influence anything."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from parallax.config import get_settings
from parallax.llm.client import LLMClient
from parallax.llm.prompts import SAFETY, SCOPE
from parallax.models import Requirement

PROMPT_VERSION = "research-v1"


class Finding(BaseModel):
    claim: str
    source_url: str
    source_title: str
    published: str | None = None
    excerpt: str = Field(description="Short paraphrase or quote from the source supporting the claim.")
    market: str | None = None


class CompetitiveGap(BaseModel):
    applicable: bool = Field(description="True only if the findings compare matched competitor models directly.")
    low: float = Field(ge=0, le=5)
    high: float = Field(ge=0, le=5)
    rationale: str


class ResearchOut(BaseModel):
    answer_summary: str
    findings: list[Finding]
    limitations: list[str]
    competitive_gap: CompetitiveGap


class ClaimCheck(BaseModel):
    claim: str
    verdict: Literal["verified", "partially_verified", "unverified", "refuted"]
    note: str
    source_url: str


class VerificationOut(BaseModel):
    checks: list[ClaimCheck]
    overall: Literal["verified", "partially_verified", "unverified", "refuted"]
    notes: str


def research(llm: LLMClient, requirement: Requirement, question: str, why: str, requested_by: str,
             run_id: uuid.UUID) -> ResearchOut:
    settings = get_settings()
    system = f"""\
You are a careful automotive market researcher. Use web search to answer the question with
specific, sourced facts (model, model year, market, trim where relevant). Prefer manufacturer pages,
established automotive press and official data. Every finding needs a real URL you actually saw.
If you cannot find support, say so in limitations instead of guessing.
{SCOPE}
{SAFETY}"""
    user = (f"Requirement under review: [{requirement.id}] {requirement.title}: {requirement.description}\n"
            f"Requested by: {requested_by}\nQuestion: {question}\nWhy it matters: {why}")

    def mock(rng):
        return ResearchOut(
            answer_summary=f"[mock] Research summary for: {question}",
            findings=[Finding(claim="[mock] Competitor X offers this as standard on 2026 models.",
                              source_url="https://example.com/mock-source", source_title="Mock source", excerpt="[mock]")],
            limitations=["Mock mode: no web search performed."],
            competitive_gap=CompetitiveGap(applicable=rng.random() < 0.5, low=1.0, high=3.0, rationale="[mock]"),
        )

    return llm.structured(ResearchOut, system=system, user=user, model=settings.model_fast, purpose="web_research",
                          prompt_version=PROMPT_VERSION, agent_id="agent:research", run_id=run_id,
                          requirement_id=requirement.id, web_search=True, mock=mock, reasoning_effort="low")


def verify(llm: LLMClient, requirement: Requirement, question: str, findings: ResearchOut,
           run_id: uuid.UUID) -> VerificationOut:
    settings = get_settings()
    system = f"""\
You are a strict fact checker. For each claim, open or search for the cited source and decide:
verified (source clearly supports it), partially_verified (supports part, or is outdated/other market),
unverified (cannot confirm), refuted (source contradicts it). Judge only what the sources say.
{SAFETY}"""
    user = (f"Question that was researched: {question}\n"
            f"Requirement context: [{requirement.id}] {requirement.title}\n"
            f"Findings to check:\n" + findings.model_dump_json(include={"findings", "limitations"}, indent=1))

    def mock(rng):
        verdict = rng.choice(["verified", "partially_verified", "unverified"])
        return VerificationOut(
            checks=[ClaimCheck(claim=f.claim, verdict=verdict, note="[mock] not checked", source_url=f.source_url)
                    for f in findings.findings],
            overall=verdict, notes="Mock mode: verification simulated.",
        )

    return llm.structured(VerificationOut, system=system, user=user, model=settings.model_strong,
                          purpose="research_verification", prompt_version=PROMPT_VERSION, agent_id="agent:verifier",
                          run_id=run_id, requirement_id=requirement.id, web_search=True, mock=mock)
