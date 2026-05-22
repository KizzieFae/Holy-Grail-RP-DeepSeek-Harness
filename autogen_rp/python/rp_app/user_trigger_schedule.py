"""Parse and validate optional headless user-trigger schedule JSON (harness-only)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_ALLOWED_TOP_LEVEL = frozenset(
    {"default_trigger", "by_orchestration_turn", "by_actor_targeted_turn"}
)
_ISSUE240_ACTOR_TARGETED_MODE = "actor_targeted_overlay"


class UserTriggerScheduleError(ValueError):
    """Invalid schedule file or contents."""


@dataclass(frozen=True)
class ActorTargetedOverlayEntry:
    target_actor: str
    trigger: str


@dataclass(frozen=True)
class UserTriggerSchedule:
    by_orchestration_turn: dict[int, str]
    by_actor_targeted_turn: dict[int, ActorTargetedOverlayEntry]
    default_trigger: str | None


def _norm_actor(name: str) -> str:
    return str(name or "").replace("_", " ").casefold().strip()


def actor_names_match(left: str, right: str) -> bool:
    ln = _norm_actor(left)
    rn = _norm_actor(right)
    if not ln or not rn:
        return False
    return ln == rn or ln in rn or rn in ln


def load_user_trigger_schedule(
    path: str | Path,
    *,
    max_orchestration_turn: int,
) -> UserTriggerSchedule:
    """Load and strictly validate a user-trigger schedule file."""
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

    by_turn = _parse_by_orchestration_turn(
        data.get("by_orchestration_turn", {}),
        max_orchestration_turn=max_orchestration_turn,
    )
    by_actor = _parse_by_actor_targeted_turn(
        data.get("by_actor_targeted_turn", {}),
        max_orchestration_turn=max_orchestration_turn,
    )

    overlap = set(by_turn) & set(by_actor)
    if overlap:
        raise UserTriggerScheduleError(
            "by_orchestration_turn and by_actor_targeted_turn cannot share turns: "
            f"{sorted(overlap)}"
        )

    return UserTriggerSchedule(
        by_orchestration_turn=by_turn,
        by_actor_targeted_turn=by_actor,
        default_trigger=json_default,
    )


def _parse_turn_key(key_raw: Any, *, max_orchestration_turn: int) -> int:
    if isinstance(key_raw, bool) or not isinstance(key_raw, (int, str)):
        raise UserTriggerScheduleError(
            f"orchestration turn key must be int or string int, got {key_raw!r}"
        )
    try:
        n = int(str(key_raw).strip())
    except (TypeError, ValueError) as exc:
        raise UserTriggerScheduleError(
            f"orchestration turn key must be integer >= 1, got {key_raw!r}"
        ) from exc
    if n < 1:
        raise UserTriggerScheduleError(
            f"orchestration turn keys must be >= 1, got {n}"
        )
    if n > max_orchestration_turn:
        raise UserTriggerScheduleError(
            f"orchestration turn key {n} exceeds max orchestration turn "
            f"{max_orchestration_turn}"
        )
    return n


def _parse_by_orchestration_turn(
    raw_map: Any,
    *,
    max_orchestration_turn: int,
) -> dict[int, str]:
    if raw_map is None:
        raw_map = {}
    if not isinstance(raw_map, dict):
        raise UserTriggerScheduleError("by_orchestration_turn must be a JSON object")

    by_turn: dict[int, str] = {}
    seen_keys: set[int] = set()
    for key_raw, val in raw_map.items():
        n = _parse_turn_key(key_raw, max_orchestration_turn=max_orchestration_turn)
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
    return by_turn


def _parse_by_actor_targeted_turn(
    raw_map: Any,
    *,
    max_orchestration_turn: int,
) -> dict[int, ActorTargetedOverlayEntry]:
    if raw_map is None:
        raw_map = {}
    if not isinstance(raw_map, dict):
        raise UserTriggerScheduleError("by_actor_targeted_turn must be a JSON object")

    by_turn: dict[int, ActorTargetedOverlayEntry] = {}
    seen_keys: set[int] = set()
    for key_raw, val in raw_map.items():
        n = _parse_turn_key(key_raw, max_orchestration_turn=max_orchestration_turn)
        if n in seen_keys:
            raise UserTriggerScheduleError(
                f"duplicate by_actor_targeted_turn key: {n}"
            )
        seen_keys.add(n)
        if not isinstance(val, dict):
            raise UserTriggerScheduleError(
                f"by_actor_targeted_turn[{n}] must be a JSON object"
            )
        actor = str(val.get("target_actor") or "").strip()
        trigger = str(val.get("trigger") or "").strip()
        if not actor:
            raise UserTriggerScheduleError(
                f"by_actor_targeted_turn[{n}].target_actor must be non-empty"
            )
        if not trigger:
            raise UserTriggerScheduleError(
                f"by_actor_targeted_turn[{n}].trigger must be non-empty"
            )
        by_turn[n] = ActorTargetedOverlayEntry(target_actor=actor, trigger=trigger)
    return by_turn


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


def make_resolve_effective_user_trigger_from_schedule(
    schedule: UserTriggerSchedule,
    *,
    cli_trigger_provided: bool,
    cli_trigger_value: str,
    built_in_fallback: str,
) -> Callable[[int], str]:
    return make_resolve_effective_user_trigger(
        schedule.by_orchestration_turn,
        cli_trigger_provided=cli_trigger_provided,
        cli_trigger_value=cli_trigger_value,
        json_default=schedule.default_trigger,
        built_in_fallback=built_in_fallback,
    )


def make_actor_targeted_character_turn_resolver(
    schedule: UserTriggerSchedule,
    *,
    base_resolve: Callable[[int], str],
) -> Callable[[int, str], tuple[str, dict[str, Any]]]:
    """Resolve per-character trigger; inject overlay only when actor matches."""

    actor_map = schedule.by_actor_targeted_turn

    def resolve(orchestration_turn: int, acting_character: str) -> tuple[str, dict[str, Any]]:
        if not actor_map:
            return base_resolve(orchestration_turn), {}
        entry = actor_map.get(orchestration_turn)
        if entry is None:
            return base_resolve(orchestration_turn), {
                "overlay_schedule_mode": _ISSUE240_ACTOR_TARGETED_MODE,
                "overlay_target_actor": None,
                "overlay_applied": False,
                "overlay_skipped_reason": None,
            }
        meta = {
            "overlay_schedule_mode": _ISSUE240_ACTOR_TARGETED_MODE,
            "overlay_target_actor": entry.target_actor,
            "overlay_applied": False,
            "overlay_skipped_reason": "target_actor_did_not_act",
        }
        if actor_names_match(acting_character, entry.target_actor):
            meta["overlay_applied"] = True
            meta["overlay_skipped_reason"] = None
            return entry.trigger, meta
        return base_resolve(orchestration_turn), meta

    return resolve
