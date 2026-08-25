"""Per-character epistemic envelope helpers (#38)."""

from __future__ import annotations

import hashlib
from typing import Any

from .session_state import LiveSession


def compute_known_by_snapshot_id(fixture: LiveSession, character_id: str) -> str:
    """Stable fingerprint of which public events the character currently knows."""
    mgr = fixture.manager
    event_ids: list[str] = []
    for event in getattr(mgr, "public_events", []) or []:
        known_by = list(getattr(event, "known_by", []) or [])
        if character_id in known_by:
            event_ids.append(str(getattr(event, "event_id", "") or ""))
    payload = ",".join(sorted(item for item in event_ids if item))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"known_by:{character_id}:{digest}"


def character_may_know_candidate(
    *,
    character_id: str,
    provenance: dict[str, Any] | None,
    host_internal_metadata: dict[str, Any] | None,
) -> bool:
    """Reject retrieval candidates tagged with known_by lists the character is not on."""
    for source in (provenance or {}, host_internal_metadata or {}):
        known_by = source.get("known_by")
        if known_by is None:
            continue
        if isinstance(known_by, list):
            if character_id not in {str(item) for item in known_by}:
                return False
        elif isinstance(known_by, str) and known_by.strip():
            if character_id != known_by.strip():
                return False
    required_knower = (provenance or {}).get("required_knower")
    if required_knower and str(required_knower).strip() not in {"", character_id}:
        return False
    return True


def build_character_visibility_envelope(
    fixture: LiveSession,
    *,
    character_id: str,
    hg_round_id: str,
) -> dict[str, Any]:
    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    return {
        "viewer_role": "character",
        "authority_ceiling_enforced": "derived",
        "viewer_character_id": character_id,
        "subject_character_id": character_id,
        "session_template_id": template_id,
        "perception_gates_ref": f"perception:{character_id}:{hg_round_id}",
        "known_by_snapshot_id": compute_known_by_snapshot_id(fixture, character_id),
    }
