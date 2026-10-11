"""Signals: theme counts classified for a PM (pain / request / strength / mixed) and condensed into
concrete findings ("CarPlay drops during the drive"), so a PM can go into a requirement with substance.

Condensing: the LLM proposes 2-5 findings for one theme and assigns every review to one finding (or
"other"); counts, shares and quotes are computed in code from those assignments. Quotes are verbatim
record text, never generated.
"""

import hashlib
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import session_scope
from parallax.llm.client import LLMClient, get_llm
from parallax.llm.gate import check_records
from parallax.llm.prompts import SAFETY
from parallax.models import Finding, Record, SimRun, Theme
from parallax.themes import latest_snapshot_id

PROMPT_VERSION = "condense-v1"
FIRST_PASS = 120
ASSIGN_CHUNK = 100


def classify(theme: Theme) -> str:
    total = theme.mention_review_count or 0
    if not total:
        return "none"
    pain, praise, requests = theme.pain_review_count / total, theme.praise_review_count / total, theme.request_review_count / total
    if pain >= 0.4:
        return "pain"
    if requests >= 0.3:
        return "request"
    if praise >= 0.6 and pain < 0.15:
        return "strength"
    return "mixed"


def need_share(theme: Theme) -> float:
    """Share of the signal's reviews reporting a problem or a wish (y axis of the signal map)."""
    total = theme.mention_review_count or 0
    if not total:
        return 0.0
    need = theme.need_review_count or 0
    if not need and (theme.pain_review_count or theme.request_review_count):
        need = min(total, theme.pain_review_count + theme.request_review_count)  # snapshot built before the column existed
    return round(need / total, 3)


def smoothed_need_share(theme: Theme, prior: float, strength: float) -> float:
    """Share pulled toward the market average by `strength` pseudo-reviews. A signal with 5 reviews can only
    sit at 0 %, 20 %, 40 % ... and at 100 % with one bad streak; smoothing shows that small signals are uncertain
    instead of lining them up on a few heights. Large signals barely move."""
    total = theme.mention_review_count or 0
    return round((need_share(theme) * total + prior * strength) / (total + strength), 3) if total + strength else prior


def market_prior(themes: list[Theme]) -> float:
    reviews = sum(t.mention_review_count or 0 for t in themes)
    return sum(need_share(t) * (t.mention_review_count or 0) for t in themes) / reviews if reviews else 0.5


def quadrant(theme: Theme, thresholds: dict, prior: float | None = None) -> str:
    frequent = (theme.mention_review_count or 0) >= thresholds["frequent_min_reviews"]
    share = need_share(theme) if prior is None else smoothed_need_share(theme, prior, thresholds.get("smoothing_reviews", 5))
    needy = share >= thresholds["need_share_threshold"]
    return {(True, True): "act", (True, False): "protect", (False, True): "watch", (False, False): "background"}[(frequent, needy)]


def explain_kind(theme: Theme) -> str:
    """The classification rule that fired, with this signal's own numbers."""
    total = theme.mention_review_count or 0
    if not total:
        return "No reviews"
    pain, requests, praise = (round(100 * n / total) for n in
                              (theme.pain_review_count, theme.request_review_count, theme.praise_review_count))
    return {"pain": f"Pain: {pain} % report a problem (from 40 %)",
            "request": f"Wish: {requests} % ask for something (from 30 %)",
            "strength": f"Strength: {praise} % praise, {pain} % problems (from 60 % / under 15 %)",
            "mixed": f"Mixed: {pain} % problems, {requests} % wishes, {praise} % praise, no rule reached"}[classify(theme)]


FINDING_PRIORITY = ("pain", "request", "mixed", "praise")


def finding_order(kind: str | None):
    """Sort key for findings: the signal's own kind first, then problems before wishes before praise, then size.
    A requirement is written against problems and wishes, so a mixed signal leads with those."""
    own = {"pain": "pain", "request": "request", "strength": "praise"}.get(kind or "")

    def key(finding) -> tuple:
        k = finding["kind"] if isinstance(finding, dict) else finding.kind
        n = finding["reviews"] if isinstance(finding, dict) else finding.review_count
        rank = 0 if k == own else 1 + (FINDING_PRIORITY.index(k) if k in FINDING_PRIORITY else len(FINDING_PRIORITY))
        return rank, -n
    return key


CHANNEL_LABELS = {"bmw_feedback": "BMW feedback", "youtube": "YouTube", "google_play": "Google Play", "app_store": "App Store",
                  "other": "Other web", "forum": "Forum", "editorial_review": "Editorial review"}


RANK = {"pain": lambda t: (t.pain_review_count, t.impact_score or 0), "strength": lambda t: (t.praise_review_count,),
        "request": lambda t: (t.request_review_count,), "mixed": lambda t: (t.mention_review_count,),
        "all": lambda t: (t.demand_score, t.pain_review_count, t.mention_review_count)}


def ranked_themes(session: Session, market: str | None, kind: str, limit: int) -> list[tuple[Theme, str]]:
    snapshot = latest_snapshot_id(session, get_settings().target_model)
    if snapshot is None:
        return []
    query = select(Theme).where(Theme.snapshot_id == snapshot, Theme.mention_review_count > 0)
    query = query.where(Theme.market == market) if market else query.where(Theme.market.is_(None))
    themes = [(t, classify(t)) for t in session.scalars(query)]
    if kind != "all":
        themes = [(t, k) for t, k in themes if k == kind]
    themes.sort(key=lambda pair: RANK[kind](pair[0]), reverse=True)
    return themes[:limit]


def latest_findings(session: Session, market: str | None, feature_keys: list[str]) -> dict[str, list[Finding]]:
    if not feature_keys:
        return {}
    query = select(Finding).where(Finding.feature_key.in_(feature_keys), Finding.target_model == get_settings().target_model)
    query = query.where(Finding.market == market) if market else query.where(Finding.market.is_(None))
    out: dict[str, list[Finding]] = defaultdict(list)
    for finding in session.scalars(query.order_by(Finding.review_count.desc())):
        out[finding.feature_key].append(finding)
    return out


# ------------------------------------------------------------------ condensing


class FindingDraft(BaseModel):
    id: str = Field(description="Short id like F1, F2 ...")
    title: str = Field(description="The concrete problem, wish or praise in customer language, max 10 words.")
    description: str = Field(description="One or two sentences: what exactly customers experience.")
    kind: Literal["pain", "request", "praise", "mixed"]


class Assignment(BaseModel):
    record_id: str
    finding_id: str = Field(description="One of the finding ids, or 'other' if none fits.")


class CondenseOut(BaseModel):
    findings: list[FindingDraft] = Field(description="2-5 distinct, concrete findings; do not repeat the theme name.")
    assignments: list[Assignment]


class AssignOut(BaseModel):
    assignments: list[Assignment]


SYSTEM = f"""\
You condense customer feedback about one feature of the BMW 5 Series into concrete findings for a
product manager. A finding is one specific experience many customers share (e.g. "Wireless CarPlay drops
during the drive"), not a restatement of the feature. Keep pains, wishes and praise apart. Then assign
EVERY review id to exactly one finding, or "other" if none fits. Never invent reviews.
{SAFETY}"""


def _norm_id(value: str) -> str:
    value = (value or "").strip().upper()
    if value.isdigit():
        value = f"F{value}"
    return value


def _lines(records: list[Record]) -> str:
    return "\n".join(f"- {r.record_id}: {(r.translation_en or r.text_original or '').replace(chr(10), ' ')[:500]}" for r in records)


def condense_theme(llm: LLMClient, theme: Theme, run_id: uuid.UUID) -> dict:
    settings = get_settings()
    with session_scope() as session:
        allowed = check_records(session, theme.record_ids).allowed
        ordered = sorted(allowed, key=lambda rid: hashlib.sha256(rid.encode()).hexdigest())
        records = {r.record_id: r for r in session.scalars(select(Record).where(Record.record_id.in_(ordered)))}
        session.expunge_all()
    if not records:
        return {"feature_key": theme.feature_key, "skipped": "no records cleared for the model"}
    ids = [rid for rid in ordered if rid in records]
    first, rest = ids[:FIRST_PASS], ids[FIRST_PASS:]
    head = f"Feature: {theme.label} | market: {theme.market or 'all'} | claim mix: {theme.counts_by_claim_type}\nReviews:\n"

    def mock_condense(rng):
        drafts = [FindingDraft(id=f"F{i}", title=f"[mock] {theme.label} issue {i}", description="[mock]",
                               kind=rng.choice(["pain", "request", "praise"])) for i in (1, 2)]
        return CondenseOut(findings=drafts, assignments=[Assignment(record_id=rid, finding_id=rng.choice(["F1", "F2"])) for rid in first])

    out = llm.structured(CondenseOut, system=SYSTEM, user=head + _lines([records[r] for r in first]), model=settings.model_fast,
                         purpose="condense_signal", prompt_version=PROMPT_VERSION, agent_id="agent:condenser", run_id=run_id,
                         input_record_ids=first, mock=mock_condense, reasoning_effort="low")
    drafts = {_norm_id(f.id): f for f in out.findings}
    titles = {f.title.strip().lower(): _norm_id(f.id) for f in out.findings}

    def resolve(value: str) -> str:
        """Models sometimes answer with 'f1', '1' or the finding title instead of 'F1'."""
        key = _norm_id(value)
        if key in drafts:
            return key
        return titles.get(value.strip().lower(), "other")

    assigned = {a.record_id: resolve(a.finding_id) for a in out.assignments if a.record_id in records}
    catalog = "\n".join(f"{_norm_id(f.id)}: {f.title} ({f.kind})" for f in out.findings)
    for start in range(0, len(rest), ASSIGN_CHUNK):
        chunk = rest[start:start + ASSIGN_CHUNK]

        def mock_assign(rng, chunk=chunk):
            return AssignOut(assignments=[Assignment(record_id=rid, finding_id=rng.choice(list(drafts) or ["other"])) for rid in chunk])

        more = llm.structured(AssignOut, system=SYSTEM, user=f"{head}Findings:\n{catalog}\nAssign these reviews:\n"
                              + _lines([records[r] for r in chunk]), model=settings.model_fast, purpose="condense_assign",
                              prompt_version=PROMPT_VERSION, agent_id="agent:condenser", run_id=run_id,
                              input_record_ids=chunk, mock=mock_assign, reasoning_effort="low")
        assigned.update({a.record_id: resolve(a.finding_id) for a in more.assignments if a.record_id in records})

    members: dict[str, list[str]] = defaultdict(list)
    for rid in ids:
        members[assigned.get(rid, "other") if assigned.get(rid) in drafts else "other"].append(rid)
    total = len(ids)
    rows = []
    for finding_id, draft in drafts.items():
        rids = members.get(finding_id, [])
        if not rids:
            continue
        rows.append(Finding(
            target_model=theme.target_model, market=theme.market, feature_key=theme.feature_key, theme_label=theme.label,
            title=draft.title, description=draft.description, kind=draft.kind, record_ids=rids, review_count=len(rids),
            share_of_theme=round(len(rids) / total, 4),
            quotes=[{"record_id": rid, "text": (records[rid].text_original or "")[:240]} for rid in rids[:3]],
            run_id=run_id, model=settings.model_fast,
        ))
    with session_scope() as session:
        session.execute(delete(Finding).where(Finding.feature_key == theme.feature_key, Finding.target_model == theme.target_model,
                                              (Finding.market == theme.market) if theme.market else Finding.market.is_(None)))
        session.add_all(rows)
    return {"feature_key": theme.feature_key, "market": theme.market, "reviews": total, "findings": len(rows),
            "unassigned": len(members.get("other", []))}


def start(session: Session, actor_id: str, options: dict) -> SimRun:
    run = SimRun(kind="condense", status="queued", requirement_ids=[], requested_by=actor_id,
                 config={"options": options, "model": get_settings().model_fast, "prompt_version": PROMPT_VERSION},
                 progress={"stage": "queued"})
    session.add(run)
    session.flush()
    record_event(session, category="ai", actor_id=actor_id, action="condense.start", entity_type="sim_run",
                 entity_id=str(run.id), run_id=run.id, after=options)
    return run


def execute(run_id: uuid.UUID) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    llm = get_llm()
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status, run.started_at = "running", datetime.now(timezone.utc)
        options, actor = run.config.get("options", {}), run.requested_by
        themes = []
        for market in options.get("markets", [None]):
            for kind in options.get("kinds", ["pain", "request", "strength"]):
                themes += [t for t, _ in ranked_themes(session, market, kind, int(options.get("limit", 8)))]
        session.expunge_all()
    llm.set_budget(run_id, 40 + sum(1 + max(0, t.mention_review_count - FIRST_PASS) // ASSIGN_CHUNK + 1 for t in themes))
    results, failures = [], 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(condense_theme, llm, t, run_id): t for t in themes}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as error:
                failures += 1
                results.append({"feature_key": futures[future].feature_key, "error": repr(error)[:300]})
            with session_scope() as session:
                session.get(SimRun, run_id).progress = {"stage": "condensing", "themes_done": done, "themes_total": len(themes)}
    with session_scope() as session:
        run = session.get(SimRun, run_id)
        run.status = "partial" if failures else "completed"
        run.finished_at = datetime.now(timezone.utc)
        run.progress = {"stage": "done", "themes_total": len(themes), "results": results}
        record_event(session, category="ai", actor_id=actor, action=f"condense.{run.status}", entity_type="sim_run",
                     entity_id=str(run_id), run_id=run_id, after={"themes": len(themes), "failures": failures})
