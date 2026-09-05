"""Commit-time entitlement authority for player perceptual projection (#125 / G-125-01)."""

from __future__ import annotations

from typing import Any

ENTITLEMENT_AUTHORITY_SNAPSHOT_KEY = "entitlement_authority_snapshot"
ENTITLEMENT_AUTHORITY_SNAPSHOT_SCHEMA_VERSION = 1


def build_entitlement_authority_snapshot(
    *,
    session_cast: list[str],
    role_assignments: dict[str, str],
) -> dict[str, Any]:
    """Build the versioned snapshot persisted on committed player history entries."""
    normalized_roles: dict[str, str] = {}
    for character_name, role_name in (role_assignments or {}).items():
        character_key = str(character_name or "").strip()
        role_key = str(role_name or "").strip()
        if character_key and role_key:
            normalized_roles[character_key] = role_key
    cast = [str(name).strip() for name in session_cast if str(name or "").strip()]
    return {
        "schema_version": ENTITLEMENT_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
        "role_assignments": normalized_roles,
        "session_cast": cast,
    }


def build_entitlement_authority_snapshot_from_fixture(fixture: Any) -> dict[str, Any]:
    mgr = fixture.manager
    assert mgr.scene_state is not None
    return build_entitlement_authority_snapshot(
        session_cast=list(fixture.cast),
        role_assignments=dict(mgr.scene_state.role_assignments or {}),
    )


def extract_entitlement_authority_snapshot(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get(ENTITLEMENT_AUTHORITY_SNAPSHOT_KEY)
    if not isinstance(raw, dict):
        return None
    if int(raw.get("schema_version", 0) or 0) != ENTITLEMENT_AUTHORITY_SNAPSHOT_SCHEMA_VERSION:
        return None
    role_assignments = raw.get("role_assignments")
    session_cast = raw.get("session_cast")
    if not isinstance(role_assignments, dict) or not isinstance(session_cast, list):
        return None
    return {
        "schema_version": ENTITLEMENT_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
        "role_assignments": {
            str(character).strip(): str(role).strip()
            for character, role in role_assignments.items()
            if str(character or "").strip() and str(role or "").strip()
        },
        "session_cast": [str(name).strip() for name in session_cast if str(name or "").strip()],
    }


def merge_entitlement_snapshot_into_metadata(
    metadata: dict[str, Any],
    *,
    session_cast: list[str],
    role_assignments: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Attach the required player entitlement snapshot to history entry metadata."""
    merged = dict(metadata)
    merged[ENTITLEMENT_AUTHORITY_SNAPSHOT_KEY] = build_entitlement_authority_snapshot(
        session_cast=session_cast,
        role_assignments=role_assignments or {},
    )
    return merged
