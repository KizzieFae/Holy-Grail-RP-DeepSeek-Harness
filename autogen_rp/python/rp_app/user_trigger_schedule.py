"""Parse and validate optional headless user-trigger schedule JSON (harness-only)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


_ALLOWED_TOP_LEVEL = frozenset({"default_trigger", "by_orchestration_turn"})


class UserTriggerScheduleError(ValueError):
    """Invalid schedule file or contents."""


def load_user_trigger_schedule(
    path: str | Path,
    *,
    max_orchestration_turn: int,
) -> tuple[dict[int, str], str | None]:
    """Load and strictly validate a user-trigger schedule file.

    Returns:
        (by_orchestration_turn, default_trigger_or_none)

    Raises:
        UserTriggerScheduleError: on any validation failure.
    """
    p = Path(path)
    if not p.is_file():
        raise UserTriggerScheduleError(f"user trigger schedule not found: {p}")

    try:
        raw_text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserTriggerScheduleError(f"cannot read schedule file: {p}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise UserTriggerScheduleError(f"invalid JSON in schedule file: {p}") from exc

    if not isinstance(data, dict):
        raise UserTriggerScheduleError("schedule root must be a JSON object")

    extra = set(data.keys()) - _ALLOWED_TOP_LEVEL
    if extra:
        raise UserTriggerScheduleError(
            f"unknown top-level keys in schedule: {sorted(extra)}"
        )

    json_default: str | None = None
    if "default_trigger" in data:
        dt = data["default_trigger"]
        if not isinstance(dt, str) or not str(dt).strip():
            raise UserTriggerScheduleError("default_trigger must be a non-empty string")
        json_default = str(dt).strip()

    raw_map = data.get("by_orchestration_turn", {})
    if raw_map is None:
        raw_map = {}
    if not isinstance(raw_map, dict):
        raise UserTriggerScheduleError("by_orchestration_turn must be a JSON object")

    by_turn: dict[int, str] = {}
    seen_keys: set[int] = set()
    for key_raw, val in raw_map.items():
        if isinstance(key_raw, bool) or not isinstance(key_raw, (int, str)):
            raise UserTriggerScheduleError(
                f"by_orchestration_turn key must be int or string int, got {key_raw!r}"
            )
        try:
            n = int(str(key_raw).strip())
        except (TypeError, ValueError) as exc:
            raise UserTriggerScheduleError(
                f"by_orchestration_turn key must be integer >= 1, got {key_raw!r}"
            ) from exc
        if n < 1:
            raise UserTriggerScheduleError(
                f"by_orchestration_turn keys must be >= 1, got {n}"
            )
        if n > max_orchestration_turn:
            raise UserTriggerScheduleError(
                f"by_orchestration_turn key {n} exceeds max orchestration turn "
                f"{max_orchestration_turn}"
            )
        if n in seen_keys:
            raise UserTriggerScheduleError(
                f"duplicate by_orchestration_turn key: {n}"
            )
        seen_keys.add(n)
        if not isinstance(val, str) or not str(val).strip():
            raise UserTriggerScheduleError(
                f"by_orchestration_turn[{n}] must be a non-empty string"
            )
        by_turn[n] = str(val).strip()

    return by_turn, json_default


def make_resolve_effective_user_trigger(
    by_turn: Mapping[int, str],
    *,
    cli_trigger_provided: bool,
    cli_trigger_value: str,
    json_default: str | None,
    built_in_fallback: str,
) -> Callable[[int], str]:
    """Build resolver following agreed precedence for non-overridden turns."""

    def resolve(orchestration_turn: int) -> str:
        if orchestration_turn in by_turn:
            return by_turn[orchestration_turn]
        if cli_trigger_provided:
            return cli_trigger_value
        if json_default:
            return json_default
        return built_in_fallback

    return resolve
