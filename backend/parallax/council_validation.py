"""Does the council add signal? Measured, not assumed.

T2 reliability: the same requirements twice -> verdict agreement and budget-rank agreement per persona,
   verdict agreement per department.
T3 discrimination: decoy requirements (absurdly expensive, out of scope) mixed in -> they must get little
   budget, "against/don't care" verdicts, Finance against the expensive one.
T4 evidence alignment: mean customer budget per real requirement vs. real pain counts (weak test: the
   personas read the same feedback).

Nothing is persisted as requirements or responses; only the run, its LLM calls and the result.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from parallax.agents import company_twin
from parallax.agents.grounding import persona_grounding
from parallax.agents.market_twin import DirectEngine, TinyTroupeEngine
from parallax.agents.roster import active_agents
from parallax.agents.validation import spearman
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import session_scope
from parallax.llm.client import get_llm
from parallax.models import Requirement, SimRun
from parallax.policy import active_policy
from parallax.requirements import themes_for

DECOYS = [
    {"id": "DECOY-EXPENSIVE", "title": "Solid gold interior trim and a built-in champagne cellar as standard",
     "description": "Every successor 5 Series gets 24-carat gold interior trim and a refrigerated 12-bottle champagne cellar "
                    "in the trunk as standard equipment.", "expect": "low budget; Finance against"},
    {"id": "DECOY-SCOPE", "title": "Meet the Euro 7 exhaust emission limits",
     "description": "The successor must comply with the Euro 7 regulation's exhaust and brake-particle emission limits.",
     "expect": "out of customer scope; low budget"},
]


def _transient(item: dict) -> Requirement:
    return Requirement(id=item["id"], target_model=get_settings().target_model, market="US", title=item["title"],
                       description=item["description"], customer_problem="", acceptance_criteria=[], assumptions=[],
                       uncertainties=[], status="proposed", created_by="system:validation", version=1)


def _round(run_id, requirements, personas, groundings, departments, engine_name):
    llm = get_llm()
    engine = TinyTroupeEngine() if engine_name == "tinytroupe" else DirectEngine()
    if isinstance(engine, TinyTroupeEngine):
        results = engine.evaluate_many(llm, [(p, groundings[p.id]) for p in personas], requirements, run_id)
    else:
        results = [engine.evaluate(llm, p, groundings[p.id], requirements, run_id) for p in personas]
    owners = {}
    for result in results:
        spent = sum(r.budget_points for r in result.reactions) + result.keep_price_points
        scale = 100.0 / spent if spent else 0.0
        owners[result.agent.id] = {r.requirement_id: {"verdict": r.verdict, "budget": r.budget_points * scale} for r in result.reactions}
    depts = defaultdict(dict)
    for dept in departments:
        for req in requirements:
            memo = company_twin.review(llm, dept, req, {"evidence_summary": "validation round"}, [], run_id)
            depts[dept.id][req.id] = {"verdict": memo.verdict, "cost_view": memo.cost_view}
    return owners, dict(depts)


def execute(run_id: uuid.UUID) -> None:
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.started_at = "running", datetime.now(timezone.utc)
        options, actor = run.config.get("options", {}), run.requested_by
        policy = active_policy(session).document
        personas = active_agents(session, "market_persona")
        departments = [d for d in active_agents(session, "department") if d.market in (None, "US")]
        real = [session.get(Requirement, rid) for rid in options["requirement_ids"]]
        pains = {}
        for req in real:
            theme = next((t for t in themes_for(session, req) if t.market == req.market), None)
            pains[req.id] = theme.pain_review_count if theme else 0
        groundings = {p.id: persona_grounding(session, p, policy, get_settings().grounding_quotes_per_persona) for p in personas}
        session.expunge_all()
    requirements = real + [_transient(d) for d in DECOYS]
    engine_name = options.get("persona_engine", "direct")
    get_llm().set_budget(run_id, 400)
    try:
        rounds = []
        for index in range(2):
            with session_scope() as session:
                session.get(SimRun, run_id).progress = {"stage": f"round_{index + 1}"}
            rounds.append(_round(run_id, requirements, personas, groundings, departments, engine_name))
        (o1, d1), (o2, d2) = rounds
        req_ids = [r.id for r in requirements]
        real_ids = [r.id for r in real]

        # T2 reliability
        verdict_same = [o1[p][r]["verdict"] == o2[p][r]["verdict"] for p in o1 if p in o2 for r in req_ids]
        rank_rhos = [spearman([o1[p][r]["budget"] for r in req_ids], [o2[p][r]["budget"] for r in req_ids]) for p in o1 if p in o2]
        rank_rhos = [x for x in rank_rhos if x is not None]
        dept_same = [d1[d][r]["verdict"] == d2[d][r]["verdict"] for d in d1 if d in d2 for r in req_ids]

        # T3 discrimination
        def mean_budget(ids, owners):
            values = [owners[p][r]["budget"] for p in owners for r in ids]
            return round(sum(values) / len(values), 1) if values else None

        decoy_ids = [d["id"] for d in DECOYS]
        decoy_rejected = [o1[p][r]["verdict"] in ("dont_care", "against") for p in o1 for r in decoy_ids]
        finance = next((d for d in d1 if d.endswith("finance")), None)

        # T4 alignment
        mean_real = {r: (sum(o1[p][r]["budget"] for p in o1) + sum(o2[p][r]["budget"] for p in o2)) / (2 * len(o1)) for r in real_ids}
        alignment = spearman([mean_real[r] for r in real_ids], [pains[r] for r in real_ids]) if len(real_ids) >= 3 else None

        result = {
            "engine": engine_name, "personas": len(o1), "departments": len(d1), "requirements": real_ids, "decoys": DECOYS,
            "T2_reliability": {
                "owner_verdict_agreement": round(sum(verdict_same) / len(verdict_same), 3) if verdict_same else None,
                "owner_budget_rank_rho_mean": round(sum(rank_rhos) / len(rank_rhos), 3) if rank_rhos else None,
                "department_verdict_agreement": round(sum(dept_same) / len(dept_same), 3) if dept_same else None,
                "pass_rule": "owner agreement >= 0.7 and department agreement >= 0.7",
            },
            "T3_discrimination": {
                "mean_budget_real": mean_budget(real_ids, o1), "mean_budget_decoys": mean_budget(decoy_ids, o1),
                "decoy_rejected_share": round(sum(decoy_rejected) / len(decoy_rejected), 3) if decoy_rejected else None,
                "finance_on_expensive_decoy": d1.get(finance, {}).get("DECOY-EXPENSIVE") if finance else None,
                "departments_on_scope_decoy": {d: v.get("DECOY-SCOPE") for d, v in d1.items()},
                "pass_rule": "decoys get clearly less budget, >= 80 % reject them, Finance against the expensive decoy",
            },
            "T4_alignment": {"mean_budget_by_requirement": {r: round(v, 1) for r, v in mean_real.items()},
                             "pain_reviews_by_requirement": pains, "spearman": alignment,
                             "note": "weak test: personas read the same feedback"},
            "round_1": {"owners": o1, "departments": d1}, "round_2": {"owners": o2, "departments": d2},
        }
        status, error = "completed", None
    except Exception as exc:
        result, status, error = {}, "failed", repr(exc)[:2000]
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.error, run.finished_at = status, error, datetime.now(timezone.utc)
        run.progress = {"stage": "done", "result": result}
        record_event(session, category="ai", actor_id=actor, action=f"council_validation.{status}", entity_type="sim_run",
                     entity_id=str(run_id), run_id=run_id,
                     after={k: result.get(k) for k in ("T2_reliability", "T3_discrimination", "T4_alignment")}, rationale=error)


def start(session, actor_id: str, requirement_ids: list[str], persona_engine: str) -> SimRun:
    missing = [rid for rid in requirement_ids if session.get(Requirement, rid) is None]
    if missing:
        raise ValueError(f"unknown requirements: {missing}")
    run = SimRun(kind="council_validation", status="queued", requirement_ids=[], requested_by=actor_id,
                 config={"options": {"requirement_ids": requirement_ids, "persona_engine": persona_engine}},
                 progress={"stage": "queued"})
    session.add(run)
    session.flush()
    return run

