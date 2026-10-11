"""Multi-criteria scoring exactly as research/decision-model.json defines it.

score_0_100 = 20 * sum(weight_i * score_i); unknown criteria give bounds with 0 and 5 (no
renormalization); simulated/assumed ratings never become point scores, they set the low/high
range. The headline `score` is the midpoint of the bounds and is labeled as such.
"""

from collections import defaultdict
from dataclasses import dataclass

from parallax.models import CriterionRating
from parallax.policy import criteria_weights


@dataclass
class CriterionResult:
    criterion: str
    weight: float
    score: float | None
    low: float
    high: float
    status: str  # observed | estimated | simulated | assumed | simulated+assumed | unknown
    raters: list[str]
    rating_ids: list[int]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def combine_criterion(criterion: str, weight: float, ratings: list[CriterionRating], precedence: list[str],
                      uncertain: set[str]) -> CriterionResult:
    by_status: dict[str, list[CriterionRating]] = defaultdict(list)
    for rating in ratings:
        by_status[rating.status].append(rating)
    for status in precedence:
        group = by_status.get(status)
        if not group:
            continue
        raters = [r.rater_id for r in group]
        ids = [r.id for r in group if r.id is not None]
        if status in uncertain:
            # No observed/estimated input: pool every simulated and assumed rater into a consensus range
            # (mean of lows, mean of highs). It widens the bounds; it never becomes a point score.
            pooled = [r for s in precedence if s in uncertain for r in by_status.get(s, [])]
            lows = [r.low if r.low is not None else r.score for r in pooled]
            highs = [r.high if r.high is not None else r.score for r in pooled]
            pairs = [(lo, hi) for lo, hi in zip(lows, highs) if lo is not None and hi is not None]
            if not pairs:
                continue
            low = sum(lo for lo, _ in pairs) / len(pairs)
            high = sum(hi for _, hi in pairs) / len(pairs)
            statuses = "+".join(s for s in precedence if s in uncertain and by_status.get(s))
            return CriterionResult(criterion, weight, None, round(low, 3), round(high, 3), statuses,
                                   [r.rater_id for r in pooled], [r.id for r in pooled if r.id is not None])
        points = [r.score for r in group if r.score is not None]
        if not points:
            continue
        mean = sum(points) / len(points)
        lows = [r.low if r.low is not None else r.score for r in group]
        highs = [r.high if r.high is not None else r.score for r in group]
        return CriterionResult(criterion, weight, round(mean, 3), min(lows), max(highs), status, raters, ids)
    return CriterionResult(criterion, weight, None, 0.0, 5.0, "unknown", [], [])


def compute(policy_document: dict, ratings: list[CriterionRating]) -> dict:
    weights = criteria_weights(policy_document)
    ext = policy_document["parallax"]
    precedence = ext["rating_precedence"]
    uncertain = set(ext["uncertain_statuses"])
    grouped: dict[str, list[CriterionRating]] = defaultdict(list)
    for rating in ratings:
        grouped[rating.criterion].append(rating)
    results = {key: combine_criterion(key, weight, grouped.get(key, []), precedence, uncertain)
               for key, weight in weights.items()}
    low = 20 * sum(r.weight * (r.score if r.score is not None else r.low) for r in results.values())
    high = 20 * sum(r.weight * (r.score if r.score is not None else r.high) for r in results.values())
    return {
        "criteria": {k: v.as_dict() for k, v in results.items()},
        "score_low": round(low, 2),
        "score_high": round(high, 2),
        "score_midpoint": round((low + high) / 2, 2),
        "unknown_criteria": [k for k, v in results.items() if v.status == "unknown"],
        "uncertain_criteria": [k for k, v in results.items() if set(v.status.split("+")) & uncertain],
        "formula": policy_document["decision_model"].get("formula"),
        "note": "score_midpoint is the midpoint of the policy bounds, not a point estimate.",
    }


def sensitivity(policy_document: dict, results: dict[str, dict]) -> dict[str, dict]:
    """Vary each weight by +/-20 % and renormalize; report each requirement's best and worst rank."""
    weights = criteria_weights(policy_document)
    scenarios = [weights]
    for key in weights:
        for factor in (0.8, 1.2):
            varied = {k: (w * factor if k == key else w) for k, w in weights.items()}
            total = sum(varied.values())
            scenarios.append({k: w / total for k, w in varied.items()})
    ranks: dict[str, list[int]] = defaultdict(list)
    for scenario in scenarios:
        mids = {}
        for requirement_id, result in results.items():
            low = high = 0.0
            for key, criterion in result["criteria"].items():
                w = scenario.get(key, 0)
                low += w * (criterion["score"] if criterion["score"] is not None else criterion["low"])
                high += w * (criterion["score"] if criterion["score"] is not None else criterion["high"])
            mids[requirement_id] = 10 * (low + high)
        for rank, requirement_id in enumerate(sorted(mids, key=lambda r: -mids[r]), 1):
            ranks[requirement_id].append(rank)
    return {rid: {"best_rank": min(r), "worst_rank": max(r), "rank_sensitive": max(r) != min(r)} for rid, r in ranks.items()}


def overlapping(results: dict[str, dict]) -> dict[str, list[str]]:
    """Requirements whose score bounds overlap cannot be ordered with confidence."""
    out: dict[str, list[str]] = {}
    items = list(results.items())
    for rid, res in items:
        out[rid] = [other for other, o in items if other != rid
                    and not (res["score_high"] < o["score_low"] or o["score_high"] < res["score_low"])]
    return out
