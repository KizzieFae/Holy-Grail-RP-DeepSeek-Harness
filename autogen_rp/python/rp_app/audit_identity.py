"""Issue #106 / #109 — Streamlit audit label from opaque ``session_id``.

``audit_session_owner`` for UI-triggered audited runs is a deterministic slug of the
persisted ``session_id`` only (Issue #109: UUID-based, no embedded semantics). It must
never be copied from ``scene_owner`` or cast names. Headless audit labels are **not**
constructed here; they follow scenario/harness parameters unchanged (Issue #109).
"""

from __future__ import annotations

import re


def streamlit_audit_owner_label_from_session_id(session_id: str) -> str:
    """Deterministic slug for audit filenames / manifest ``session_owner`` (Streamlit only).

    Applies to the opaque ``session_id`` string (Issue #109). Does not add semantic tokens.
    Headless simulations keep their existing ``audit_session_owner`` / scenario slug rules.
    """
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(session_id or "").strip()).strip("_").lower()
    return s or "streamlit_session"
