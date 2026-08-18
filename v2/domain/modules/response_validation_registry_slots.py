"""Registry-slot validation for structured ``scene_state_updates`` only.

No narrative interpretation, event summaries, or implicit contradiction checks.
Uses the same parse helpers as ``resolved_outcome_registry`` (closed schema).
"""

from __future__ import annotations

from typing import Any

from resolved_outcome_registry import (
    parse_housing_call_outcome_candidates,
    parse_location_entry_outcome_candidates,
    parse_lodging_sleep_surface_candidates,
    parse_suppressant_formulation_outcome_candidates,
)

_REGISTRY_REJECT_REASONS = frozenset(
    {
        "invalid_surface_id",
        "invalid_status",
        "invalid_location_id",
    }
)


def _updates_nonempty_for_key(updates: dict[str, Any], key: str) -> bool:
    raw = updates.get(key)
    if raw is None:
        return False
    if isinstance(raw, dict):
        return bool(raw)
    if isinstance(raw, list):
        return len(raw) > 0
    return bool(str(raw).strip())


def validate_registry_scene_state_updates(
    move: dict[str, Any] | None,
    *,
    scene_state: dict[str, Any] | None,
    _continuity_manager: Any | None,
) -> tuple[bool, str]:
    """Reject only malformed registry-shaped updates (parse reasons).

    ``_continuity_manager`` is reserved for future slot-active checks; unused to
    avoid implicit contradiction logic beyond parser surface.
    """
    _ = _continuity_manager
    if not isinstance(move, dict):
        return True, ""
    updates = move.get("scene_state_updates")
    if not isinstance(updates, dict) or not updates:
        return True, ""
    ss = scene_state if isinstance(scene_state, dict) else {}

    checks: list[tuple[str, Any]] = [
        ("sleeping_surface_assignment", parse_lodging_sleep_surface_candidates),
        ("housing_call_outcome", parse_housing_call_outcome_candidates),
        ("suppressant_formulation_outcome", parse_suppressant_formulation_outcome_candidates),
        ("location_entry_outcome", parse_location_entry_outcome_candidates),
    ]
    for key, parse_fn in checks:
        if not _updates_nonempty_for_key(updates, key):
            continue
        _cands, reason = parse_fn(move, ss)
        if reason in _REGISTRY_REJECT_REASONS:
            return False, f"[REGISTRY_SLOT] {key}: {reason}"
    return True, ""
