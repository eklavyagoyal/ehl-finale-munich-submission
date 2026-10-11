"""Pure unit tests: scoring, vote tally, SSR, rank correlation, label-derived claims."""

from parallax.agents.validation import spearman
from parallax.agents.vote import VoteOut, tally
from parallax.ingest import derive_claims_from_labels
from parallax.llm.ssr import distribution_from_similarities
from parallax.models import CriterionRating
from parallax.policy import default_policy_document
from parallax.scoring import compute, sensitivity

POLICY = default_policy_document()


def rating(criterion, status, score=None, low=None, high=None, rater="r"):
    return CriterionRating(criterion=criterion, status=status, score=score, low=low, high=high, rater_id=rater, rater_type="code")


def test_all_unknown_gives_full_bounds():
    result = compute(POLICY, [])
    assert result["score_low"] == 0 and result["score_high"] == 100
    assert set(result["unknown_criteria"]) == {"demand", "impact", "competitive_gap", "vehicle_market_fit", "delivery_fit", "reuse"}


def test_observed_scores_are_points_without_renormalization():
    result = compute(POLICY, [rating("demand", "observed", 5), rating("impact", "observed", 4)])
    # 20 * (0.25*5 + 0.20*4) = 41 known; unknown rest contributes 0..(0.55*5*20 = 55)
    assert result["score_low"] == 41.0
    assert result["score_high"] == 96.0


def test_observed_beats_simulated_and_uncertain_pool_into_range():
    result = compute(POLICY, [
        rating("impact", "observed", 3),
        rating("impact", "simulated", 4.5, 4, 5),
        rating("vehicle_market_fit", "simulated", 4, 3, 5),
        rating("vehicle_market_fit", "assumed", None, 1, 3, rater="dept:sales"),
    ])
    assert result["criteria"]["impact"]["score"] == 3 and result["criteria"]["impact"]["status"] == "observed"
    fit = result["criteria"]["vehicle_market_fit"]
    assert fit["score"] is None and fit["low"] == 2.0 and fit["high"] == 4.0
    assert fit["status"] == "simulated+assumed"
    assert "vehicle_market_fit" in result["uncertain_criteria"]


def test_sensitivity_reports_rank_ranges():
    a = compute(POLICY, [rating("demand", "observed", 5), rating("delivery_fit", "observed", 1)])
    b = compute(POLICY, [rating("demand", "observed", 1), rating("delivery_fit", "observed", 5)])
    ranks = sensitivity(POLICY, {"A": a, "B": b})
    assert ranks["A"]["best_rank"] == 1


def test_vote_tally_majority_tie_and_gate_cap():
    approve = VoteOut(vote="approve", rationale="", key_points=[], drivers=[], what_would_change_it="")
    reject = VoteOut(vote="reject", rationale="", key_points=[], drivers=[], what_would_change_it="")
    assert tally([("j1", approve), ("j2", approve), ("j3", reject)], {})["recommendation"] == "approve"
    assert tally([("j1", approve), ("j2", reject)], {})["recommendation"] == "investigate"
    capped = tally([("j1", approve), ("j2", approve)], {"model_market_applicability": "unknown", "pm_review": "unknown"})
    assert capped["recommendation"] == "investigate" and capped["gate_cap"]
    failed = tally([("j1", approve)], {"evidence_traceability": "fail"})
    assert failed["recommendation"] == "defer"


def test_ssr_distribution_sums_to_one_and_prefers_closest_anchor():
    dist = distribution_from_similarities([0.1, 0.2, 0.3, 0.4, 0.9])
    assert abs(sum(dist) - 1) < 1e-9
    assert max(range(5), key=lambda i: dist[i]) == 4


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0
    assert spearman([1, 2], [1, 2]) is None


def test_derived_claims_pair_labels_and_map_catalog():
    features = [{"feature_key": "apple_carplay", "label": "Apple CarPlay"}, {"feature_key": "seats", "label": "Seats"}]
    records = {"r1": {"record_id": "r1", "record_kind": "feedback", "text_original": "CarPlay drops; seats great",
                      "source_fields": {"original_labels": [
                          {"name": "Feedback Type", "value": "Defect"}, {"name": "Vfc level2 Name", "value": "Apple CarPlay"},
                          {"name": "Vfc level3 Name", "value": "Connection fault"},
                          {"name": "Feedback Type", "value": "Likes"}, {"name": "Vfc level2 Name", "value": "Seats"},
                      ]}}}
    claims = derive_claims_from_labels(records, set(), features)
    by_feature = {c["feature_key"]: c for c in claims}
    assert by_feature["apple_carplay"]["claim_type"] == "defect"
    assert by_feature["seats"]["claim_type"] == "praise"
    assert all(c["quotes"][0] in records["r1"]["text_original"] for c in claims)
    assert derive_claims_from_labels(records, {"r1"}, features) == []


def test_finding_id_normalization():
    from parallax.signals import _norm_id

    assert _norm_id("f1") == "F1" and _norm_id(" 2 ") == "F2" and _norm_id("F3") == "F3"
