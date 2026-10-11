"""Append-only audit trail: who or what did what, when, and why."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from parallax.models import AuditEvent


def actor_type_of(actor_id: str) -> str:
    """Actor IDs are namespaced: `pm:lisa`, `agent:synthesizer`, `persona:...`, `system:...`."""
    prefix = actor_id.split(":", 1)[0]
    if prefix in {"pm", "user", "human"}:
        return "human"
    if prefix == "system":
        return "system"
    return "agent"


def record_event(
    session: Session,
    *,
    category: str,
    actor_id: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    requirement_id: str | None = None,
    run_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
    rationale: str | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        category=category,
        actor_type=actor_type_of(actor_id),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        requirement_id=requirement_id,
        run_id=run_id,
        before=before,
        after=after,
        rationale=rationale,
        meta=meta or {},
    )
    session.add(event)
    return event


def diff(before: dict, after: dict) -> tuple[dict, dict]:
    """Return only the keys whose values changed."""
    keys = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}
