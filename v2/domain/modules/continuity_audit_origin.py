"""Issue #79 Slice 3 — continuity audit origin (pipeline vs bypass classification).

Observational only; not on the #59 runtime use allowlist. Does not influence validation.
"""

from __future__ import annotations

from typing import Any, Optional

# Closed enum (Issue #79): pipeline path vs continuity-affecting bypass kinds.
CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN = "pipeline_turn"
CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API = "bypass_direct_excursion_api"
CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION = "bypass_raw_location"
CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION = "bypass_oor_reintegration"

CONTINUITY_AUDIT_BYPASS_KINDS: frozenset[str] = frozenset(
    {
        CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
        CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION,
        CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION,
    }
)


def continuity_audit_origin_is_bypass_kind(kind: str) -> bool:
    return str(kind or "") in CONTINUITY_AUDIT_BYPASS_KINDS


def flush_continuity_audit_origin_export_payload(
    continuity_manager: Any,
) -> dict[str, Any]:
    """Prepare ``session_audit_origin`` for ``continuity_observability_summary_v1`` (Issue #79).

    Returns ``{"has_bypass": bool, "bypass_beats": [...]}`` (bypass kinds only), then **clears**
    the full session log. Typically invoked from ``build_continuity_observability_summary_v1``
    when writing ``_audit_summary.json``.
    """
    log = _get_origin_log(continuity_manager)
    bypass_only = [e for e in log if continuity_audit_origin_is_bypass_kind(e.get("kind", ""))]
    has_bypass = bool(bypass_only)
    log.clear()
    return {
        "has_bypass": has_bypass,
        "bypass_beats": list(bypass_only),
    }


def build_continuity_audit_origin_row_metadata(
    continuity_manager: Any,
) -> dict[str, Any] | None:
    """Per-turn ``metadata.continuity_audit_origin`` when the row reflects a pipeline commit.

    Returns ``None`` when the pending pipeline marker does not match the current
    ``turn_counter`` (avoids false positives on failure / non-commit audit paths).
    """
    if continuity_manager is None:
        return None
    if getattr(continuity_manager, "scene_state", None) is None:
        return None
    pending = getattr(continuity_manager, "_pending_pipeline_audit_origin_index", None)
    idx = int(getattr(continuity_manager, "turn_counter", 0) or 0)
    if pending is None or int(pending) != idx:
        return None
    return {
        "kind": CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN,
        "continuity_turn_index": idx,
    }


def _get_origin_log(continuity_manager: Any) -> list[dict[str, Any]]:
    if continuity_manager is None:
        return []
    raw = getattr(continuity_manager, "continuity_audit_origin_log", None)
    if not isinstance(raw, list):
        raw = []
        setattr(continuity_manager, "continuity_audit_origin_log", raw)
    return raw


def manager_suppress_direct_excursion_bypass_audit(continuity_manager: Any) -> bool:
    """True while pipeline turn or reintegration apply is active (Slice 3 bypass gating)."""
    return bool(
        getattr(continuity_manager, "_continuity_pipeline_turn_active", False)
        or getattr(continuity_manager, "_continuity_in_reintegration_apply", False)
    )


def manager_record_continuity_audit_event(
    continuity_manager: Any, kind: str, continuity_turn_index: int
) -> None:
    log = _get_origin_log(continuity_manager)
    log.append(
        {"continuity_turn_index": int(continuity_turn_index), "kind": str(kind)}
    )


def manager_notify_raw_location_bypass_for_audit(
    continuity_manager: Any, *, continuity_turn_index: Optional[int] = None
) -> None:
    """Call after assigning ``scene_state.location`` outside ``process_turn`` (Slice 3)."""
    idx = (
        int(continuity_turn_index)
        if continuity_turn_index is not None
        else int(getattr(continuity_manager, "turn_counter", 0) or 0)
    )
    manager_record_continuity_audit_event(
        continuity_manager, CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION, idx
    )
