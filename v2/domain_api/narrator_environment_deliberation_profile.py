"""Structural deliberation profile selection for narrator environmental cognition (#194)."""

from __future__ import annotations

from typing import Any

DELIBERATION_PROFILE_DEEP = "deep"
DELIBERATION_PROFILE_CONSTRAINED = "constrained"

DEEP_CATEGORIES = frozenset({"C", "cannot_safely_resolve"})


def classify_environment_cognition_deliberation_profile(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Select constrained vs deep profile from prepare-time envelope structure only."""
    view = context.get("environmental_current_view") or {}
    packet = context.get("environmental_packet") or {}
    signals: list[str] = []

    if view.get("conflicts"):
        signals.append("environmental_conflicts")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    if packet.get("recent_environmental_changes"):
        signals.append("recent_environmental_changes")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    if packet.get("carryover_b2_refs"):
        signals.append("carryover_b2_refs")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    location_refs = list(packet.get("location_refs") or [])
    if len(location_refs) != 1:
        signals.append("location_ref_count_ne_1")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    continuity_turn_index = context.get("continuity_turn_index")
    if continuity_turn_index is not None and int(continuity_turn_index) > 1:
        signals.append("continuity_turn_index_gt_1")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    stable_sub_referents = list(packet.get("stable_sub_referents") or [])
    if len(stable_sub_referents) > 0:
        signals.append("stable_sub_referents_present")
        return {"profile": DELIBERATION_PROFILE_DEEP, "signals": signals}

    signals.append("narrow_opening_envelope")
    return {"profile": DELIBERATION_PROFILE_CONSTRAINED, "signals": signals}


def classify_cognition_result_deliberation_profile(
    cognition_result: dict[str, Any] | None,
) -> str:
    """Post-inference structural guard: complex cognition envelopes require deep profile."""
    if not isinstance(cognition_result, dict):
        return DELIBERATION_PROFILE_DEEP
    needs = list(cognition_result.get("information_needs") or [])
    resolutions = list(cognition_result.get("resolutions") or [])
    if len(needs) > 1:
        return DELIBERATION_PROFILE_DEEP
    categories = {
        str(item.get("category", "") or "").strip()
        for item in resolutions
        if isinstance(item, dict)
    }
    if categories & DEEP_CATEGORIES:
        return DELIBERATION_PROFILE_DEEP
    if any(
        isinstance(item, dict) and item.get("mediation_outcome") not in (None, "", "no_match")
        for item in resolutions
    ):
        return DELIBERATION_PROFILE_DEEP
    if len(needs) == 1 and categories and categories <= {"B2"}:
        return DELIBERATION_PROFILE_CONSTRAINED
    return DELIBERATION_PROFILE_DEEP
