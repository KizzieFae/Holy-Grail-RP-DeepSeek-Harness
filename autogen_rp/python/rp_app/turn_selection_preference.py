"""Deterministic routing preference snapshot for Director selection diagnostics.

Bridges responder_obligation / action_responsibility hints with semantic validation
and human-facing logs. Single source of truth for advisory preference fields.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def resolve_participant_key(
    ref: str,
    participant_names: list[str],
    *,
    display_name_for_key: Callable[[str], str] | None = None,
) -> str | None:
    """Map a free-form label (agent key or card display name) to a canonical agent key."""
    raw = str(ref or "").strip()
    if not raw:
        return None
    keys = [str(k or "").strip() for k in participant_names if str(k or "").strip()]
    if raw in keys:
        return raw
    if display_name_for_key is not None:
        for k in keys:
            disp = str(display_name_for_key(k) or "").strip()
            if disp and disp == raw:
                return k
    lower = raw.lower()
    for k in keys:
        if k.lower() == lower:
            return k
    return None


def build_routing_preference_snapshot(
    *,
    responder_obligation: dict[str, Any] | None,
    action_responsibility: dict[str, Any] | None,
    available_actors: list[str],
) -> dict[str, Any]:
    """Advisory preference from orchestration hints (Director path only; hard routes exit earlier)."""
    avail = {str(a or "").strip() for a in available_actors if str(a or "").strip()}
    ro = responder_obligation if isinstance(responder_obligation, dict) else {}
    ar = action_responsibility if isinstance(action_responsibility, dict) else {}

    preference_candidate: str | None = None
    preference_source = "none"
    preference_class = "none"

    if ro.get("active") and str(ro.get("confidence") or "") == "high":
        primary = str(ro.get("primary_actor") or "").strip()
        if primary in avail:
            preference_candidate = primary
            preference_source = "responder_obligation"
            preference_class = "advisory"
    elif ar.get("active") and str(ar.get("confidence") or "") == "high":
        primary = str(ar.get("primary_actor") or "").strip()
        if primary in avail:
            preference_candidate = primary
            preference_source = "action_responsibility"
            preference_class = "advisory"

    return {
        "preference_candidate": preference_candidate,
        "preference_source": preference_source,
        "preference_class": preference_class,
        "responder_obligation_active": bool(ro.get("active")),
        "action_responsibility_active": bool(ar.get("active")),
    }


def sanitize_semantic_turn_selection_assessment(
    semantic_assessment: dict[str, Any] | None,
    *,
    selected_actor: str,
    participant_names: list[str],
    display_name_for_key: Callable[[str], str] | None = None,
) -> dict[str, Any] | None:
    """Align semantic flags with the actual pick so logs never contradict (e.g. ignored preference for pick).

    - Clears direct-address miss when the model's target resolves to the selected actor.
    - Clears an unresolvable direct_address_target miss (avoids nonsense labels).
    - When pick matches resolved semantic target, sets supports_selected_actor True.
    """
    if not isinstance(semantic_assessment, dict):
        return None
    if semantic_assessment.get("parse_error"):
        return dict(semantic_assessment)

    out = dict(semantic_assessment)
    pick = str(selected_actor or "").strip()
    target_raw = str(out.get("direct_address_target") or "").strip()
    resolved_target = resolve_participant_key(
        target_raw,
        participant_names,
        display_name_for_key=display_name_for_key,
    )

    if out.get("should_flag_direct_address_miss"):
        if not target_raw or resolved_target is None:
            out["should_flag_direct_address_miss"] = False
        elif pick and resolved_target == pick:
            out["should_flag_direct_address_miss"] = False
            out["supports_selected_actor"] = True
            out["direct_address_target"] = resolved_target

    if resolved_target is not None:
        out["direct_address_target"] = resolved_target

    return out


def build_turn_selection_diagnostics_for_audit(
    *,
    actual_pick: str,
    routing_snapshot: dict[str, Any],
    semantic_effective: dict[str, Any] | None,
    reconciled_issues: list[str],
    final_pick: str | None = None,
) -> dict[str, Any]:
    """Structured diagnostics for audit metadata (compact semantic slice)."""
    out: dict[str, Any] = {
        "validated_pick": actual_pick,
        **dict(routing_snapshot),
        "reconciled_issues": list(reconciled_issues),
    }
    if final_pick is not None:
        out["final_pick"] = final_pick
    if isinstance(semantic_effective, dict):
        out["semantic_effective"] = {
            "supports_selected_actor": semantic_effective.get("supports_selected_actor"),
            "direct_address_target": semantic_effective.get("direct_address_target"),
            "should_flag_direct_address_miss": semantic_effective.get(
                "should_flag_direct_address_miss"
            ),
            "should_flag_repeat_spotlight": semantic_effective.get(
                "should_flag_repeat_spotlight"
            ),
            "confidence": semantic_effective.get("confidence"),
        }
    return out


def format_turn_selection_diagnostic_block(
    *,
    validated_pick: str,
    final_pick: str,
    routing_snapshot: dict[str, Any],
    reconciled_issues: list[str],
) -> str:
    """Single-line diagnostic derived from structured fields (before display-name substitution).

    ``validated_pick`` is the actor semantic validation used (Director parse output).
    ``final_pick`` is ``next_actor`` after progression override and participation fairness.
    """
    pref = routing_snapshot.get("preference_candidate")
    src = str(routing_snapshot.get("preference_source") or "none")
    klass = str(routing_snapshot.get("preference_class") or "none")
    parts = [
        f"validated_pick={validated_pick}",
        f"final_pick={final_pick}",
    ]
    if str(validated_pick).strip() != str(final_pick).strip():
        parts.append("routing_note=pick_changed_after_validation")
    parts.append(
        (
            f"advisory_preference={pref} (source={src}, class={klass})"
            if pref
            else f"advisory_preference=none (source={src})"
        )
    )
    if pref and str(pref).strip() == str(validated_pick).strip():
        parts.append("preference_aligned_vs_validated=yes")
    elif pref:
        parts.append("preference_aligned_vs_validated=no")
    else:
        parts.append("preference_aligned_vs_validated=n/a")
    if reconciled_issues:
        parts.append(f"notes={' | '.join(reconciled_issues)}")
    return "Selection diagnostics: " + "; ".join(parts)
