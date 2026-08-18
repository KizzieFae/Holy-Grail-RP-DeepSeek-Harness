"""Issue #79 Slice 2 — runtime mirrors and excursion digest for per-turn audits.

Observational only; not on the #59 runtime use allowlist. No derived presence / E_active.
"""

from __future__ import annotations

from typing import Any


def scene_state_after_runtime_mirror(scene_state: Any) -> dict[str, Any]:
    """Direct mirror of ``SceneState`` for ``context_snapshot.scene_state_after``.

    Single source: ``SceneState.to_dict()`` — no recomputation of presence or location.
    """
    if scene_state is None or not hasattr(scene_state, "to_dict"):
        return {}
    return scene_state.to_dict()


def build_excursion_audit_digest_v1(continuity_manager: Any) -> list[dict[str, str]] | None:
    """Compact excursion pointer for per-turn ``metadata`` (Issue #79 Slice 2).

    Returns ``None`` when continuity is unavailable, excursions are missing/empty,
    or no valid excursion ids were found. Otherwise a **sorted** list of
    ``{"excursion_id": ..., "status": ...}`` entries — **no** participant payloads,
    reintegration fields, or full ``ExcursionRecord`` dumps. Full records stay in
    session / continuity snapshot only.
    """
    if continuity_manager is None:
        return None
    raw = getattr(continuity_manager, "excursions", None)
    if not isinstance(raw, dict):
        return None
    if not raw:
        return None
    rows: list[dict[str, str]] = []
    for eid, rec in raw.items():
        eid_s = str(eid or "").strip()
        if not eid_s:
            continue
        st = getattr(rec, "status", None)
        status_val = (
            st.value if hasattr(st, "value") else (str(st) if st is not None else "")
        )
        rows.append(
            {
                "excursion_id": eid_s,
                "status": str(status_val).strip(),
            }
        )
    rows.sort(key=lambda r: r.get("excursion_id", ""))
    return rows if rows else None
