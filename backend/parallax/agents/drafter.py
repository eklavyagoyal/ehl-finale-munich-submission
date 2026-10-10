"""Drafter: turns the strongest theme signals into candidate requirements with the brief's eight fields.

Only gate-cleared quotes are shown to the model. If no record of a theme is cleared, the drafter
works from labels and counts alone (no customer text leaves the database) and says so.
Every cited record must come from the supplied list and every quote must match its record exactly;
anything else is dropped and reported.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax import requirements as reqs
from parallax.agents.grounding import requirement_evidence_quotes
from parallax.config import get_settings
from parallax.llm.client import LLMClient, to_json
from parallax.llm.prompts import SAFETY, SCOPE, UNITS
from parallax.models import Record, Requirement, Theme

PROMPT_VERSION = "drafter-v1"


class CitedQuote(BaseModel):
    record_id: str
    quote: str = Field(description="Exact substring of that record's text.")


class DraftOut(BaseModel):
    in_scope: bool = Field(description="False if this is regulatory, engineering-spec, pricing or not customer-facing.")
    scope_reason: str
    title: str = Field(description="Short customer-facing requirement title.")
    description: str = Field(description="Clear, actionable customer requirement for the successor vehicle.")
    customer_problem: str
    acceptance_criteria: list[str] = Field(description="Customer-facing; targets only where evidence justifies them.")
    supporting_quotes: list[CitedQuote]
    contradicting_quotes: list[CitedQuote]
    future_assumptions: list[str]
    uncertainties: list[str]
    kano_class: Literal["must_be", "performance", "attractive", "indifferent", "reverse", "unclear"] = Field(
        description="Proposed Kano class: defects/complaints about basics -> must_be; more-is-better -> performance; "
                    "unexpected delighters / new requests -> attractive. 'unclear' if evidence does not support a call.")
    kano_rationale: str = Field(description="Why this class, citing the claim mix (defects, requests, praise).")
    benchmark_target: str | None = Field(description="Proposed customer-facing target relative to named competitors, only if "
                                                     "evidence mentions them; otherwise null. The PM sets the final target.")
    suggested_next_action: Literal["pm_review", "investigate", "defer"]


SYSTEM = f"""\
You draft customer requirements for the successor of the BMW 5 Series (target model given below),
3-5 years ahead, from deterministic theme counts and real owner quotes. One requirement per theme.
If condensed findings are given, build the requirement around the largest concrete findings (name them),
not around the generic feature name.
Cite only the record IDs provided, with exact quotes. Separate evidence from assumptions.
{SCOPE}
{UNITS}
{SAFETY}"""


def _theme_payload(theme: Theme, quotes: list[dict], findings: list | None = None) -> dict:
    return {
        "condensed_findings": [{"title": f.title, "description": f.description, "kind": f.kind, "reviews": f.review_count,
                                "share_of_feature_reviews": f.share_of_theme} for f in findings or []]
        or "NONE (signal not condensed yet)",
        "feature_key": theme.feature_key, "feature_label": theme.label, "area": theme.area,
        "market": theme.market or "all markets pooled", "distinct_reviews": theme.mention_review_count,
        "direct_target_model_reviews": theme.direct_review_count, "claim_types": theme.counts_by_claim_type,
        "channels": theme.channels, "max_within_cohort_share": round(theme.max_cohort_share, 4),
        "competitor_reviews_same_feature": theme.competitor_review_count,
        "quotes": quotes or "NONE (no evidence cleared for external model use; work from counts and labels only)",
    }


def draft_requirements(session: Session, llm: LLMClient, *, target_model: str, snapshot_id: uuid.UUID,
                       market: str | None, limit: int, actor_id: str, feature_keys: list[str] | None = None,
                       run_id: uuid.UUID | None = None) -> dict:
    settings = get_settings()
    query = select(Theme).where(Theme.snapshot_id == snapshot_id, Theme.mention_review_count > 0)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    if feature_keys:
        query = query.where(Theme.feature_key.in_(feature_keys))
    themes = session.scalars(query.order_by(Theme.demand_score.desc(), Theme.mention_review_count.desc())).all()
    existing = {(r.feature_key, r.market) for r in session.scalars(select(Requirement)).all()}
    themes = [t for t in themes if (t.feature_key, market) not in existing][:limit]

    created, skipped, dropped_citations = [], [], 0
    for theme in themes:
        from parallax.signals import latest_findings

        findings = latest_findings(session, theme.market, [theme.feature_key]).get(theme.feature_key, [])
        focus = [rid for f in findings[:2] for rid in f.record_ids] if findings else []
        quotes, gate_meta = requirement_evidence_quotes(session, theme, focus + theme.record_ids)
        quote_ids = [q["record_id"] for q in quotes]

        def mock(rng, quotes=quotes, theme=theme):
            cited = [CitedQuote(record_id=q["record_id"], quote=q["text"][:80]) for q in quotes[:3]]
            return DraftOut(
                in_scope=True, scope_reason="[mock] customer-facing feature",
                title=f"{theme.label}: meet customer expectations",
                description=f"The successor offers an improved '{theme.label}' experience that addresses the most frequent owner complaints and requests.",
                customer_problem=f"Owners report issues or wishes around {theme.label} ({theme.mention_review_count} reviews).",
                acceptance_criteria=[f"Owner complaints about {theme.label} decrease in post-launch feedback."],
                supporting_quotes=cited, contradicting_quotes=[],
                future_assumptions=["Customer expectations in this area keep rising through 2030."],
                uncertainties=["Effort and competitor parity not yet assessed."],
                kano_class="must_be" if theme.pain_review_count else "performance",
                kano_rationale=f"[mock] claim mix {theme.counts_by_claim_type}",
                benchmark_target=None,
                suggested_next_action="pm_review",
            )

        draft = llm.structured(
            DraftOut, system=SYSTEM + f"\nTarget model: {target_model}. Market: {market or 'all focus markets'}.",
            user="Theme:\n" + to_json(_theme_payload(theme, quotes, findings)), model=settings.model_strong,
            purpose="draft_requirement", prompt_version=PROMPT_VERSION, agent_id="agent:drafter", run_id=run_id,
            input_record_ids=quote_ids, mock=mock,
        )
        level, explanation = reqs.evidence_level(theme, has_simulation=False)
        requirement = reqs.create(session, {
            "target_model": target_model, "market": market, "feature_key": theme.feature_key, "theme_id": theme.id,
            "title": draft.title, "description": draft.description, "customer_problem": draft.customer_problem,
            "acceptance_criteria": draft.acceptance_criteria, "assumptions": draft.future_assumptions,
            "uncertainties": draft.uncertainties + ([] if quotes else ["Drafted from counts and labels only; no customer text was cleared for the model."]),
            "evidence_level": level, "evidence_level_explanation": explanation,
            "suggested_next_action": draft.suggested_next_action,
            "kano_class": draft.kano_class, "kano_rationale": draft.kano_rationale,
            "benchmark_target": draft.benchmark_target,
            "status": "proposed" if draft.in_scope else "draft",
        }, actor_id="agent:drafter", reason=f"Drafted from theme {theme.feature_key} (snapshot {snapshot_id})", run_id=run_id)

        allowed = set(quote_ids)
        texts = {r.record_id: (r.text_original or "", r.translation_en or "")
                 for r in session.scalars(select(Record).where(Record.record_id.in_(list(allowed)))).all()} if allowed else {}
        cited_ids = set()
        for relation, items in (("supporting", draft.supporting_quotes), ("contradicting", draft.contradicting_quotes)):
            for item in items:
                original = texts.get(item.record_id)
                if item.record_id not in allowed or original is None or not (item.quote in original[0] or item.quote in original[1]):
                    dropped_citations += 1
                    continue
                reqs.link_evidence(session, requirement, item.record_id, relation, "agent:drafter", quote=item.quote,
                                   rationale="cited by drafter", run_id=run_id)
                cited_ids.add(item.record_id)
        # Theme records stay linked as context so the PM can browse all underlying evidence.
        for record_id in [rid for rid in theme.record_ids if rid not in cited_ids][:50]:
            reqs.link_evidence(session, requirement, record_id, "context", "system:drafter-theme", run_id=run_id)
        reqs.add_observed_ratings(session, requirement, run_id=run_id)
        reqs.set_gate(session, requirement, "customer_facing_scope", "pass" if draft.in_scope else "fail", "agent:drafter",
                      draft.scope_reason, run_id=run_id)
        reqs.refresh_code_gates(session, requirement, run_id=run_id)
        created.append({"id": requirement.id, "feature_key": theme.feature_key, "quotes_shown": len(quotes), "gate": gate_meta})
    for theme in session.scalars(query).all():
        if (theme.feature_key, market) in existing:
            skipped.append(theme.feature_key)
    session.flush()
    return {"created": created, "skipped_existing": skipped, "dropped_invalid_citations": dropped_citations}
