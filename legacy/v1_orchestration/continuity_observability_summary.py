"""Issue #79 Slice 4 — ``continuity_observability_summary_v1`` for ``_audit_summary.json``.

Summary-only rollup; observational (#59). No CTAR / full continuity dumps.
"""

from __future__ import annotations

from typing import Any

from continuity_audit_origin import (
    continuity_audit_origin_is_bypass_kind,
    flush_continuity_audit_origin_export_payload,
)
from continuity_state import ExcursionStatus

CONTINUITY_OBSERVABILITY_SUMMARY_V1_SCHEMA_VERSION = 1

# Explicit marker when ``_audit_summary.json`` is written without a ``ContinuityManager``
# (Issue #79 follow-up — does not synthesize continuity-backed rollup data).
# Closed enum for ``continuity_observability_status_v1.reason`` — single source of truth.
CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED = (
    "continuity_manager_not_provided"
)

CONTINUITY_OBSERVABILITY_STATUS_REASONS: frozenset[str] = frozenset(
    {CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED}
)

_ALLOWED_TOP_KEYS: frozenset[str] = frozenset(
    {
        "beats_with_mutation_resolution",
        "continuity_turn_count_observed",
        "excursion_active_count",
        "excursion_closed_count",
        "excursion_record_count",
        "schema_version",
        "session_audit_origin",
    }
)


def _canonical_bypass_beats(raw: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return rows
    for e in raw:
        if not isinstance(e, dict):
            continue
        kind = str(e.get("kind", "") or "")
        if not continuity_audit_origin_is_bypass_kind(kind):
            continue
        try:
            idx = int(e.get("continuity_turn_index", 0))
        except (TypeError, ValueError):
            continue
        rows.append({"continuity_turn_index": idx, "kind": kind})
    rows.sort(key=lambda r: (r["continuity_turn_index"], r["kind"]))
    return rows


def _beats_with_mutation_resolution_indices(manager: Any) -> list[int]:
    meta = getattr(manager, "turn_metadata_by_index", None)
    if not isinstance(meta, dict):
        return []
    out: list[int] = []
    for k, bucket in meta.items():
        if not isinstance(bucket, dict):
            continue
        cmr = bucket.get("continuity_mutation_resolution")
        if not isinstance(cmr, dict) or not cmr:
            continue
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue
        out.append(idx)
    return sorted(set(out))


def _excursion_counts(manager: Any) -> tuple[int, int, int]:
    ex = getattr(manager, "excursions", None)
    if not isinstance(ex, dict):
        return 0, 0, 0
    n = len(ex)
    active = 0
    closed = 0
    for rec in ex.values():
        st = getattr(rec, "status", None)
        if st == ExcursionStatus.ACTIVE:
            active += 1
        elif st == ExcursionStatus.CLOSED:
            closed += 1
    return n, active, closed


def build_continuity_observability_summary_v1(continuity_manager: Any) -> dict[str, Any]:
    """Build the only allowed shape for ``continuity_observability_summary_v1``.

    Calls ``flush_continuity_audit_origin_export_payload`` (Slice 3) for ``session_audit_origin``.
    """
    beats = _beats_with_mutation_resolution_indices(continuity_manager)
    turn_obs = int(getattr(continuity_manager, "turn_counter", 0) or 0)
    rec_n, active_n, closed_n = _excursion_counts(continuity_manager)

    flushed = flush_continuity_audit_origin_export_payload(continuity_manager)
    bypass_beats = _canonical_bypass_beats(flushed.get("bypass_beats"))
    has_bypass = bool(flushed.get("has_bypass"))

    # Canonical nested session_audit_origin keys: bypass_beats, has_bypass
    session_origin = {
        "bypass_beats": bypass_beats,
        "has_bypass": has_bypass,
    }

    out: dict[str, Any] = {
        "beats_with_mutation_resolution": beats,
        "continuity_turn_count_observed": turn_obs,
        "excursion_active_count": active_n,
        "excursion_closed_count": closed_n,
        "excursion_record_count": rec_n,
        "schema_version": CONTINUITY_OBSERVABILITY_SUMMARY_V1_SCHEMA_VERSION,
        "session_audit_origin": session_origin,
    }
    assert set(out.keys()) == _ALLOWED_TOP_KEYS
    return out


def build_continuity_observability_status_v1_unavailable(*, reason: str) -> dict[str, Any]:
    """Build the only allowed shape for ``continuity_observability_status_v1``.

    Used when the audit summary writer has no ``ContinuityManager``; callers must not
    emit a fabricated ``continuity_observability_summary_v1``.
    """
    if reason not in CONTINUITY_OBSERVABILITY_STATUS_REASONS:
        allowed = ", ".join(sorted(CONTINUITY_OBSERVABILITY_STATUS_REASONS))
        raise ValueError(
            "continuity_observability_status_v1: reason must be one of "
            f"CONTINUITY_OBSERVABILITY_STATUS_REASONS {{{allowed}}}; got {reason!r}"
        )
    # Canonical key order for JSON serialization (status, then reason).
    out: dict[str, Any] = {"status": "unavailable", "reason": reason}
    assert list(out.keys()) == ["status", "reason"]
    return out
