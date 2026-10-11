"""Grounding: real evidence handed to agents. This is where evidence text leaves the database,
so every helper here filters through the permission gate first."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.llm.gate import check_records
from parallax.models import Agent, Record, Source, Theme
from parallax.policy import market_bucket

APP_CHANNELS = {"app_store", "google_play"}


@dataclass
class Grounding:
    quotes: list[dict] = field(default_factory=list)  # {record_id, text, channel, market}
    study: list[dict] = field(default_factory=list)  # {record_id, attribute, value, statistic, scale}
    gate: dict = field(default_factory=dict)

    @property
    def record_ids(self) -> list[str]:
        return [q["record_id"] for q in self.quotes] + [s["record_id"] for s in self.study]


def _stable_order(key: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()


def _engine_label(record: Record) -> str | None:
    for label in (record.source_fields or {}).get("original_labels") or []:
        if label.get("name") == "Engine Type":
            return label.get("value")
    return None


def _text(record: Record) -> str:
    text = record.translation_en or record.text_original or ""
    return text.strip()


def persona_grounding(session: Session, agent: Agent, policy: dict, limit: int, include_examples: bool = False) -> Grounding:
    spec_filter = agent.spec.get("grounding", {}).get("record_filter", {})
    bucket = spec_filter.get("market_bucket", agent.market)
    subjects = set(spec_filter.get("subject_ids_any", []))
    channels = set(spec_filter.get("channels", []))
    powertrains = set(spec_filter.get("powertrain_label_values", []))

    rows = session.execute(
        select(Record, Source).join(Source, Source.source_id == Record.source_id)
        .where(Record.record_kind == "feedback", Record.superseded_by.is_(None), Record.text_original.is_not(None))
    ).all()
    candidates: dict[str, list[tuple[Record, Source]]] = defaultdict(list)
    for record, source in rows:
        if source.is_example and not include_examples:
            continue
        if channels and source.channel not in channels:
            continue
        record_subjects = set(record.subject_ids or [])
        if subjects and not (record_subjects & subjects) and not (not record_subjects and source.channel in APP_CHANNELS):
            continue
        if bucket and not any(market_bucket(policy, m) == bucket for m in (record.markets or [])):
            continue
        engine = _engine_label(record)
        if powertrains and engine and engine not in powertrains:
            continue
        candidates[source.channel].append((record, source))

    gate = check_records(session, [r.record_id for group in candidates.values() for r, _ in group])
    allowed = set(gate.allowed)
    # Round-robin over channels so one large channel does not drown the others.
    pools = {
        channel: sorted((pair for pair in group if pair[0].record_id in allowed),
                        key=lambda pair: _stable_order(pair[0].record_id, agent.id))
        for channel, group in candidates.items()
    }
    quotes: list[dict] = []
    while len(quotes) < limit and any(pools.values()):
        for channel in sorted(pools):
            if pools[channel] and len(quotes) < limit:
                record, _ = pools[channel].pop(0)
                quotes.append({"record_id": record.record_id, "text": _text(record)[:600], "channel": channel,
                               "markets": record.markets})

    study: list[dict] = []
    cohort = agent.spec.get("grounding", {}).get("study_cohort")
    if cohort:
        metric_rows = session.execute(
            select(Record, Source).join(Source, Source.source_id == Record.source_id)
            .where(Record.record_kind == "metric", Source.channel == "bmw_customer_study", Record.superseded_by.is_(None))
        ).all()
        metric_ids = [r.record_id for r, s in metric_rows
                      if cohort["subject_id"] in (r.subject_ids or []) and set(cohort["markets"]) & set(r.markets or [])
                      and (include_examples or not s.is_example)]
        metric_gate = check_records(session, metric_ids)
        by_id = {r.record_id: r for r, _ in metric_rows}
        for record_id in metric_gate.allowed:
            metric = by_id[record_id].metric or {}
            study.append({"record_id": record_id, "attribute": metric.get("name"), "value": metric.get("value"),
                          "statistic": metric.get("statistic"), "scale": metric.get("scale")})
        gate.excluded.update(metric_gate.excluded)
    return Grounding(quotes=quotes, study=study, gate=gate.as_meta())


def requirement_evidence_quotes(session: Session, theme: Theme | None, record_ids: list[str], limit: int = 12) -> tuple[list[dict], dict]:
    """Gate-cleared quotes for a requirement, spread over channels."""
    ids = sorted(dict.fromkeys(record_ids), key=lambda rid: _stable_order(rid, "requirement"))[:400]
    gate = check_records(session, ids)
    allowed = set(gate.allowed)
    rows = session.execute(
        select(Record, Source).join(Source, Source.source_id == Record.source_id).where(Record.record_id.in_(list(allowed)))
    ).all() if allowed else []
    by_channel: dict[str, list] = defaultdict(list)
    for record, source in rows:
        by_channel[source.channel].append((record, source))
    quotes: list[dict] = []
    while len(quotes) < limit and any(by_channel.values()):
        for channel in sorted(by_channel):
            if by_channel[channel] and len(quotes) < limit:
                record, _ = by_channel[channel].pop(0)
                quotes.append({"record_id": record.record_id, "channel": channel, "markets": record.markets,
                               "text": _text(record)[:500]})
    return quotes, gate.as_meta()
