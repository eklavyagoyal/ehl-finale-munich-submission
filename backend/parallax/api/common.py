"""Shared API helpers: actor identity, serialization, errors."""

import re
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import Header, HTTPException
from sqlalchemy import inspect

ACTOR_PATTERN = re.compile(r"^(pm|user|system|agent):[A-Za-z0-9_.@-]{1,100}$")


def actor(x_actor: str | None = Header(default=None, description="Who is acting, e.g. `pm:lisa`. Defaults to `pm:anonymous`.")) -> str:
    value = x_actor or "pm:anonymous"
    if not ACTOR_PATTERN.match(value):
        raise HTTPException(400, "X-Actor must look like 'pm:<name>'")
    return value


def human_actor(value: str) -> str:
    if not value.startswith(("pm:", "user:")):
        raise HTTPException(403, "this action is reserved for a human PM (X-Actor: pm:<name>)")
    return value


def plain(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


def row(obj, exclude: set[str] | None = None) -> dict:
    """ORM instance -> JSON-safe dict of its columns."""
    exclude = exclude or set()
    mapper = inspect(obj).mapper
    return {attr.key: plain(getattr(obj, attr.key)) for attr in mapper.column_attrs if attr.key not in exclude}


def not_found(what: str, key: Any) -> HTTPException:
    return HTTPException(404, f"{what} {key} not found")
