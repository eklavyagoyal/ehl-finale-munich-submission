"""Semantic Similarity Rating (SSR).

Personas answer in free text; the answer is embedded and compared with Likert anchor statements.
Similarities become a probability distribution over the 1-5 scale, averaged across anchor sets.
This avoids the mid-scale collapse of asking an LLM for a number directly.
(Method: PyMC Labs / Colgate-Palmolive 2025; tested on personal-care purchase intent, not cars.)
"""

import math
import threading

from parallax.llm.client import LLMClient

_anchor_cache: dict[tuple[str, tuple[str, ...]], list[list[float]]] = {}
_lock = threading.Lock()


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _anchors(llm: LLMClient, anchor_set: list[str]) -> list[list[float]]:
    key = (llm.settings.embedding_model + llm.mode, tuple(anchor_set))
    with _lock:
        cached = _anchor_cache.get(key)
    if cached is None:
        cached = llm.embed(anchor_set, purpose="ssr_anchors")
        with _lock:
            _anchor_cache[key] = cached
    return cached


def distribution_from_similarities(similarities: list[float], epsilon: float = 0.01) -> list[float]:
    low = min(similarities)
    shifted = [s - low + epsilon for s in similarities]
    total = sum(shifted)
    return [s / total for s in shifted]


def rate(llm: LLMClient, texts: list[str], anchor_sets: list[list[str]], *, run_id=None, agent_id=None) -> list[dict]:
    """Return per text: distribution (5 floats), mean on 1-5, importance on 0-5."""
    if not texts:
        return []
    vectors = llm.embed(texts, purpose="ssr_responses", run_id=run_id, agent_id=agent_id)
    anchor_vectors = [_anchors(llm, anchor_set) for anchor_set in anchor_sets]
    results = []
    for vector in vectors:
        per_set = [distribution_from_similarities([_cos(vector, a) for a in anchors]) for anchors in anchor_vectors]
        distribution = [sum(d[i] for d in per_set) / len(per_set) for i in range(5)]
        mean = sum((i + 1) * p for i, p in enumerate(distribution))
        results.append({"distribution": [round(p, 4) for p in distribution], "mean": round(mean, 3),
                        "importance_0_5": round((mean - 1) * 5 / 4, 3)})
    return results
