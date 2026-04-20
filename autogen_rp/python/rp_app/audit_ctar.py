"""Issue #79 Slice 1 — CTAR (continuity turn-level audit record) projection for per-turn audits.

Read-only observability; not on the #59 runtime use allowlist.
"""

from __future__ import annotations

from typing import Any


def _canonicalize_json_mapping(obj: Any) -> Any:
    """Recursively sort JSON object keys lexicographically; lists preserve order."""
    if isinstance(obj, dict):
        return {k: _canonicalize_json_mapping(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonicalize_json_mapping(x) for x in obj]
    return obj


def canonicalize_continuity_mutation_resolution_for_audit(
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Write-time canonical ordering for ``continuity_mutation_resolution`` (Issue #79 / #81).

    Outer keys: resolution slot ids (e.g. ``location``, ``excursion_lifecycle:...``).
    Inner keys per slot: ``mutation_type``, ``payload``, ``source`` — sorted lexicographically;
    ``payload`` is recursively key-sorted when it is a dict.
    """
    if not isinstance(raw, dict) or not raw:
        return {}
    out: dict[str, Any] = {}
    for slot_key in sorted(raw.keys()):
        entry = raw[slot_key]
        if not isinstance(entry, dict):
            continue
        inner: dict[str, Any] = {}
        for ik in sorted(entry.keys()):
            val = entry[ik]
            if ik == "payload" and isinstance(val, dict):
                inner[ik] = _canonicalize_json_mapping(val)
            elif isinstance(val, dict):
                inner[ik] = _canonicalize_json_mapping(val)
            else:
                inner[ik] = val
        out[slot_key] = inner
    return out


def _canonicalize_consequences_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out = [str(x) for x in raw]
    return sorted(out)


def build_ctar_projection_for_audit(continuity_manager: Any) -> dict[str, Any] | None:
    """Build CTAR slice for ``metadata.ctar`` on character/narrator full audit rows.

    Includes only: ``continuity_turn_index``, optional ``consequences``, optional
    ``continuity_mutation_resolution`` (canonicalized when present).

    Returns ``None`` when continuity or scene state is unavailable (no CTAR attachment).
    """
    if continuity_manager is None:
        return None
    if getattr(continuity_manager, "scene_state", None) is None:
        return None

    idx = int(getattr(continuity_manager, "turn_counter", 0) or 0)
    meta = getattr(continuity_manager, "turn_metadata_by_index", None)
    if not isinstance(meta, dict):
        meta = {}
    bucket = meta.get(idx)
    if not isinstance(bucket, dict):
        bucket = {}

    piece: dict[str, Any] = {"continuity_turn_index": idx}

    if "consequences" in bucket:
        piece["consequences"] = _canonicalize_consequences_list(bucket.get("consequences"))

    if "continuity_mutation_resolution" in bucket:
        cmr = bucket.get("continuity_mutation_resolution")
        if isinstance(cmr, dict) and cmr:
            piece["continuity_mutation_resolution"] = (
                canonicalize_continuity_mutation_resolution_for_audit(cmr)
            )

    return _canonicalize_json_mapping(piece)
