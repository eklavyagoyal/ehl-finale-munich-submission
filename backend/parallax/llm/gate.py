"""The single permission gate between stored evidence and any external LLM.

Record text may reach an external model only if its source is accepted and has
export_permissions.external_llm == true (research contract). Exclusions are logged, never silent.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from parallax.config import get_settings
from parallax.models import Record, Source


class EvidencePermissionError(RuntimeError):
    pass


@dataclass
class GateResult:
    allowed: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)  # record_id -> reason

    def as_meta(self) -> dict:
        reasons: dict[str, int] = {}
        for reason in self.excluded.values():
            reasons[reason] = reasons.get(reason, 0) + 1
        return {"allowed": len(self.allowed), "excluded": len(self.excluded), "excluded_by_reason": reasons}


def check_records(session: Session, record_ids: list[str] | set[str], allow_unreviewed: bool | None = None) -> GateResult:
    if allow_unreviewed is None:
        allow_unreviewed = get_settings().allow_unreviewed_evidence_for_llm
    ids = list(dict.fromkeys(record_ids))
    result = GateResult()
    if not ids:
        return result
    rows = session.execute(
        select(Record.record_id, Source.review_status, Source.external_llm, Source.is_example)
        .join(Source, Source.source_id == Record.source_id)
        .where(Record.record_id.in_(ids))
    ).all()
    found = {row[0]: row for row in rows}
    for record_id in ids:
        row = found.get(record_id)
        if row is None:
            result.excluded[record_id] = "unknown_record"
            continue
        _, status, external_llm, _ = row
        if status == "rejected":
            result.excluded[record_id] = "source_rejected"
        elif external_llm is False:
            result.excluded[record_id] = "external_llm_disallowed"
        elif allow_unreviewed:
            result.allowed.append(record_id)
        elif status != "accepted":
            result.excluded[record_id] = "source_not_accepted"
        elif external_llm is not True:
            result.excluded[record_id] = "external_llm_permission_not_confirmed"
        else:
            result.allowed.append(record_id)
    return result


def assert_allowed(session: Session, record_ids: list[str]) -> GateResult:
    result = check_records(session, record_ids)
    if result.excluded:
        raise EvidencePermissionError(
            f"{len(result.excluded)} record(s) are not cleared for external LLM use: {result.as_meta()['excluded_by_reason']}"
        )
    return result
