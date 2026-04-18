"""Issue #68: audit-only interpretation envelope and Phase 1 grounding observability.

Not read by runtime. Not on the #59 runtime use allowlist.
"""

from __future__ import annotations

from typing import Any

from scene_grounding import is_behaviorally_binding_scene_fact

SIGNAL_INTERPRETATION_SCHEMA_VERSION = 1

# v1 partial registry — operator interpretation roles (not #59 applicability classes).
_SIGNAL_ROLES_V1: dict[str, str] = {
    "progression_advisory": "telemetry",
    "anti_regression_advisory": "guardrail",
    "scene_grounding": "telemetry",
}


def build_grounding_phase1_inner(
    *,
    scene_grounding: Any,
    continuity_turn_index: int,
    continuity_event: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Minimal Phase 1 snapshot derived from existing session grounding + continuity refs.

    Returns None when ``scene_grounding`` is not a dict (caller omits ``metadata.scene_grounding``).

    ``grounding_derivation_refs`` lists continuity-native ids (``PublicEvent.event_id`` and/or
    fact ``source.ref``) when present; the key is omitted entirely when no refs are available
    (reduced scope — no invented identifiers).
    """
    if not isinstance(scene_grounding, dict):
        return None
    facts_raw = scene_grounding.get("facts")
    facts_list = facts_raw if isinstance(facts_raw, list) else []
    facts = [f for f in facts_list if isinstance(f, dict)]

    binding = 0
    non_binding = 0
    refs: set[str] = set()
    ce = continuity_event or {}
    eid = str(ce.get("event_id") or "").strip()
    if eid:
        refs.add(eid)

    for f in facts:
        cat = str(f.get("category") or "")
        key = str(f.get("key") or "")
        if is_behaviorally_binding_scene_fact(cat, key):
            binding += 1
        else:
            non_binding += 1
        src = f.get("source")
        if isinstance(src, dict):
            ref = str(src.get("ref") or "").strip()
            if ref:
                refs.add(ref)

    out: dict[str, Any] = {
        "continuity_turn_index": int(continuity_turn_index),
        "fact_count": len(facts),
        "binding_fact_count": binding,
        "non_binding_fact_count": non_binding,
    }
    if refs:
        out["grounding_derivation_refs"] = sorted(refs)
    return out


def grounding_observability_summary_line(scene_grounding: Any) -> str:
    """Compact one-line summary for ``metadata.scene_grounding.summary`` (audit only)."""
    if not isinstance(scene_grounding, dict):
        return ""
    facts_raw = scene_grounding.get("facts")
    if not isinstance(facts_raw, list) or not facts_raw:
        return ""
    n = len([f for f in facts_raw if isinstance(f, dict)])
    if n <= 0:
        return ""
    return f"{n} settled scene facts in projection"


def attach_signal_interpretation_v1(metadata: dict[str, Any]) -> None:
    """Populate ``metadata.signal_interpretation`` when any v1-registered block is present.

    Mutates ``metadata`` in place. Idempotent replace of ``signal_interpretation`` when rebuilt.
    """
    signals: dict[str, dict[str, str]] = {}
    if isinstance(metadata.get("progression_advisory"), dict):
        signals["progression_advisory"] = {
            "role": _SIGNAL_ROLES_V1["progression_advisory"]
        }
    if isinstance(metadata.get("anti_regression_advisory"), dict):
        signals["anti_regression_advisory"] = {
            "role": _SIGNAL_ROLES_V1["anti_regression_advisory"]
        }
    sg = metadata.get("scene_grounding")
    if isinstance(sg, dict) and isinstance(sg.get("phase1"), dict):
        signals["scene_grounding"] = {"role": _SIGNAL_ROLES_V1["scene_grounding"]}
    if not signals:
        return
    metadata["signal_interpretation"] = {
        "schema_version": SIGNAL_INTERPRETATION_SCHEMA_VERSION,
        "signals": signals,
    }


def merge_scene_grounding_audit_family(
    *,
    scene_grounding_state: Any,
    continuity_turn_index: int,
    continuity_event: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build ``metadata.scene_grounding`` object (phase1 + optional summary) or None."""
    phase1 = build_grounding_phase1_inner(
        scene_grounding=scene_grounding_state,
        continuity_turn_index=continuity_turn_index,
        continuity_event=continuity_event,
    )
    if phase1 is None:
        return None
    out: dict[str, Any] = {"phase1": phase1}
    summary = grounding_observability_summary_line(scene_grounding_state)
    if summary:
        out["summary"] = summary
    return out
