"""Shared datetime parsing for continuity_state serialization paths."""

from __future__ import annotations

from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: object | None) -> datetime:
    if value is None or not str(value).strip():
        return _utc_now()
    parsed = datetime.fromisoformat(str(value))
    return (
        parsed.astimezone(timezone.utc)
        if parsed.tzinfo is not None
        else parsed.replace(tzinfo=timezone.utc)
    )
