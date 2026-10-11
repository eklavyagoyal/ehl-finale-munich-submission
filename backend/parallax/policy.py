"""Decision policy: the research branch's decision-model.json plus Parallax extensions.

Everything here is a proposed demo policy, not BMW policy. Every run stores the policy version
it used, and the PM can publish a new version (audited) through the API.
"""

import copy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from parallax.audit import record_event
from parallax.models import PolicyVersion

# Used when no decision-model.json has been ingested yet. Identical to research/decision-model.json v1.0.
FALLBACK_DECISION_MODEL: dict[str, Any] = {
    "schema_version": "1.0",
    "status": "proposed_demo_policy_not_bmw_approved",
    "planning_horizon": "successor_vehicle_3_to_5_years",
    "decision_unit": ["feature_key", "target_model", "market", "planning_horizon"],
    "scale": {"min": 0, "max": 5},
    "criteria": [
        {"key": "demand", "weight": 0.25, "meaning": "Strength of demand within comparable cohorts; frequency, corroboration, and sampling limitations."},
        {"key": "impact", "weight": 0.20, "meaning": "Severity of the customer problem and benefit of addressing it."},
        {"key": "competitive_gap", "weight": 0.15, "meaning": "Verified gap against matched competitor models, years, markets, and trims."},
        {"key": "vehicle_market_fit", "weight": 0.20, "meaning": "Fit to the target vehicle class and documented needs of the market."},
        {"key": "delivery_fit", "weight": 0.10, "meaning": "Fit of available rough effort/timing estimates to the planning horizon; unknown without support."},
        {"key": "reuse", "weight": 0.10, "meaning": "Supported applicability across customer segments and target vehicles."},
    ],
    "gates": ["customer_facing_scope", "model_market_applicability", "evidence_traceability", "pm_review"],
    "advisory_inputs": ["rough_effort", "timing_constraints"],
    "gate_values": ["pass", "fail", "unknown"],
    "gate_policy": {"fail": "defer_or_reject_with_reason", "unknown": "investigate_before_commitment"},
    "missing_score_policy": "retain_null_and_compute_bounds_using_0_and_5_without_renormalizing_weights",
    "formula": "score_0_to_100 = 20 * sum(weight_i * score_i)",
    "sensitivity": {
        "method": "vary_each_weight_by_20_percent_then_renormalize_all_weights",
        "additional_checks": ["leave_out_each_source_channel", "low_and_high_score_estimates", "market_specific_rankings"],
        "interpretation": "Flag changes in the top shortlist; show overlapping score bounds rather than claiming a definite order.",
    },
}

PARALLAX_EXTENSIONS: dict[str, Any] = {
    "status": "proposed_parallax_extension_not_bmw_approved",
    # Which claim review states feed theme counts. The contract counts accepted claims only.
    "theme_claim_statuses": ["accepted"],
    # Market buckets used for personas and market views. "EU" here means the EU aggregate plus
    # individual European countries; the original country codes stay on every record.
    "market_buckets": {
        "US": ["US"],
        "CN": ["CN"],
        "EU": ["EU", "DE", "FR", "IT", "ES", "GB", "SE", "DK", "FI", "NO", "NL", "BE", "AT", "CH", "PL",
               "PT", "IE", "CZ", "LV", "LT", "EE", "HU", "SK", "SI", "GR", "RO", "BG", "HR", "LU"],
    },
    # Optional sibling derivatives counted as a labeled proxy in a market's themes, e.g. {"CN": ["bmw:G68"]}
    # (5 Series long wheelbase in China). Off by default: the research contract excludes G68 from the G60
    # packet ("sparse coverage is a finding, not a reason to transfer evidence"). Enabling it is a PM policy
    # publish (audited); proxy evidence never counts as direct target-model evidence.
    "market_proxies": {},
    # Within-cohort shares from tiny cohorts (e.g. one editorial article) are meaningless;
    # below this cohort size the share counts as 0 for the demand anchors.
    "min_cohort_size_for_share": 30,
    # Signal map (four fields): x = distinct reviews mentioning the feature, y = share of them reporting a
    # pain or a wish. A signal counts as "frequent" from this many reviews, as "mostly problems" from this share.
    "signal_map": {"frequent_min_reviews": 30, "need_share_threshold": 0.5, "smoothing_reviews": 5},  # weighted reviews
    # Evidence weights: how much one review counts toward a signal. weight = source x author x text.
    # BMW feedback comes from owners through BMW channels and is labelled by BMW, so it counts fully; an online
    # review counts half, scaled by what triage knows about the author; emoji-laden and very short texts a bit less.
    # A PM policy, shown in the UI; raw counts stay visible next to the weighted ones.
    "evidence_weights": {
        "source": {"bmw": 1.0, "social": 0.5, "competitors": 0.5},
        "author": {"owner": 1.0, "unclear": 0.8, "not_owner": 0.6},
        "emoji_factor": 0.95, "short_text": {"max_chars": 40, "factor": 0.9},
    },
    # Triage of online reviews (parallax.triage). Off until the PM has checked the spot-check sample: when on,
    # online reviews marked not relevant or about another vehicle no longer count toward the vehicle's signals.
    "triage_filter": {"enabled": False, "exclude_not_relevant": True,
                      "exclude_vehicles": ["older_generation", "other_bmw", "competitor"]},
    # Observed demand anchors (0-5), first matching rule from the top wins. Shares are
    # within-cohort collected-review shares, never customer prevalence.
    "demand_anchors": [
        {"score": 5, "min_reviews": 25, "min_cohort_share": 0.05, "min_channels": 2},
        {"score": 4, "min_reviews": 10, "min_cohort_share": 0.03, "min_channels": 1},
        {"score": 3, "min_reviews": 5, "min_cohort_share": 0.01, "min_channels": 1},
        {"score": 2, "min_reviews": 3, "min_cohort_share": 0.0, "min_channels": 1},
        {"score": 1, "min_reviews": 1, "min_cohort_share": 0.0, "min_channels": 1},
    ],
    # Observed impact from the claim-type mix of supporting reviews.
    "impact_anchors": {"pain_majority": 4.0, "request_majority": 3.0, "praise_majority": 2.0, "mixed": 2.5,
                       "severity_bonus": 0.5, "severity_markers": ["very serious problem", "serious problem"]},
    # How simulated persona outputs are combined per market. Market weights are a policy
    # assumption based on sales exposure (2030 plan, G60/G68 combined); sales are context, not prevalence.
    "persona_weighting": {
        "market_weights": {"EU": 127000, "US": 80000, "CN": 78000},
        "market_weight_basis": "sales_volumes.xlsx G60_G68 volume_2030 (combined G60/G68; exposure context only)",
        "validation_multipliers": {"validated": 1.0, "weak": 0.5, "not_validated": 0.5,
                                    "unvalidated_assumption": 0.5, "failed": 0.0},
    },
    # Criterion rating precedence when several raters rated the same criterion.
    "rating_precedence": ["observed", "estimated", "simulated", "assumed"],
    # Simulated and assumed ratings never become point scores in the MCDA: they widen the bounds.
    "uncertain_statuses": ["simulated", "assumed"],
    "vote": {"tie_breaker": "investigate", "options": ["approve", "reject", "investigate", "defer"]},
    # Semantic Similarity Rating anchor sets (Likert 1-5) for persona importance.
    "ssr_anchor_sets": [
        [
            "This would make no difference to me at all.",
            "Nice to have, but I would barely notice it.",
            "A moderate improvement that I would appreciate.",
            "This matters a lot to me and would influence which car I buy next.",
            "This is essential for me; without it I would seriously consider another brand.",
        ],
        [
            "I don't care about this.",
            "It is a minor detail for me.",
            "It is somewhat important to me.",
            "It is very important to me.",
            "It is one of the most important things for my next car.",
        ],
    ],
    "persona_validation": {"min_attributes": 8, "validated_min_rho": 0.3, "weak_min_rho": 0.1},
}


def default_policy_document(decision_model: dict | None = None) -> dict:
    return {"decision_model": copy.deepcopy(decision_model or FALLBACK_DECISION_MODEL),
            "parallax": copy.deepcopy(PARALLAX_EXTENSIONS)}


def active_policy(session: Session) -> PolicyVersion:
    policy = session.scalars(
        select(PolicyVersion).where(PolicyVersion.active.is_(True)).order_by(PolicyVersion.id.desc())
    ).first()
    if policy is None:
        policy = publish_policy(session, default_policy_document(), "system:bootstrap", "Initial default policy")
    missing = {k: v for k, v in PARALLAX_EXTENSIONS.items() if k not in policy.document.get("parallax", {})}
    if missing:
        # Keys added by newer code: fill in memory with defaults; stored versions stay immutable.
        set_committed_value(policy, "document", {**policy.document,
                                                 "parallax": {**copy.deepcopy(missing), **policy.document["parallax"]}})
    return policy


def publish_policy(session: Session, document: dict, actor_id: str, rationale: str) -> PolicyVersion:
    validate_policy(document)
    document = {**document, "parallax": {**copy.deepcopy(PARALLAX_EXTENSIONS), **document["parallax"]}}
    previous = session.scalars(select(PolicyVersion).where(PolicyVersion.active.is_(True))).all()
    for row in previous:
        row.active = False
    policy = PolicyVersion(document=document, active=True, created_by=actor_id, rationale=rationale)
    session.add(policy)
    session.flush()
    record_event(
        session, category="change", actor_id=actor_id, action="policy.publish", entity_type="policy",
        entity_id=str(policy.id), before={"active_ids": [p.id for p in previous]}, after={"active_id": policy.id},
        rationale=rationale,
    )
    return policy


def validate_policy(document: dict) -> None:
    model = document.get("decision_model") or {}
    criteria = model.get("criteria") or []
    if not criteria:
        raise ValueError("policy needs decision_model.criteria")
    total = sum(float(c["weight"]) for c in criteria)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"criterion weights must sum to 1.0 (got {total:.4f})")
    if "parallax" not in document:
        raise ValueError("policy needs a parallax extension block")


def criteria_weights(policy_document: dict) -> dict[str, float]:
    return {c["key"]: float(c["weight"]) for c in policy_document["decision_model"]["criteria"]}


def market_bucket(policy_document: dict, country_or_region: str) -> str:
    for bucket, members in policy_document["parallax"]["market_buckets"].items():
        if country_or_region in members:
            return bucket
    return "RoW"
