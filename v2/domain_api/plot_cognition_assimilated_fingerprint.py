"""Resolve assimilated authority fingerprint from Plot Cognition overlay state (#166)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus
from .session_state import LiveSession


def resolve_assimilated_authority_source_fingerprint(
    fixture: LiveSession,
    overlay: Any | None,
    *,
    policy: BoundednessPolicy | None = None,
) -> str | None:
    """Return the assimilated authority_source_fingerprint for the fixture scope, if provable."""
    if overlay is None:
        return None
    scope_id = str(fixture.plot_cognition_scope_id or "").strip()
    if not scope_id:
        return None
    resolved_policy = policy or BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=resolved_policy)
    if loaded.status != LoadStatus.READY or loaded.store is None:
        return None
    authority = loaded.store.assimilated_authority
    if authority is None or not authority.sessions:
        return None
    if len(authority.sessions) == 1:
        return str(authority.sessions[0].authority_source_fingerprint or "").strip() or None
    for session in authority.sessions:
        if session.hg_scene_id == fixture.hg_scene_id:
            return str(session.authority_source_fingerprint or "").strip() or None
    return str(authority.sessions[0].authority_source_fingerprint or "").strip() or None
