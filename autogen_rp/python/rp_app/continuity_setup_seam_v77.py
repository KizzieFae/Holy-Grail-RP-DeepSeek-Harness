"""Issue #77 — setup seam: interim anchor resolution and completion boundary (pre-#80).

See GitHub #77 invalid-state rows A1, A2, D3.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class ContinuitySetupSeamError(ValueError):
    """Setup seam cannot complete (A1 / A2 / validation)."""


class ContinuitySetupSeamIncompleteError(RuntimeError):
    """Turn blocked: setup seam not finalized (D3)."""


def _role_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_scene_protagonist_role(role_name: str) -> bool:
    """Match ``scene_lifecycle_start`` protagonist heuristic (interim pre-#80 rule)."""
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protagonist",
            "recovering",
            "patient",
            "guest",
            "subject",
            "captive",
            "ward",
            "charge",
            "outsider",
            "newcomer",
            "supplicant",
            "target",
            "applicant",
            "visitor",
            "arrival",
            "student",
            "child",
            "omega",
        )
    )


def resolve_interim_anchor_character_id(
    cast: list[str],
    role_assignments: Mapping[str, Any],
) -> str:
    """Deterministic interim anchor (pre-#80). Raises ``ContinuitySetupSeamError`` on A1/A2."""
    names = [str(c).strip() for c in cast if str(c or "").strip()]
    if not names:
        raise ContinuitySetupSeamError(
            "A1: empty cast; cannot resolve anchor character"
        )
    protagonists = [
        n
        for n in names
        if _is_scene_protagonist_role(role_assignments.get(n, ""))
    ]
    if len(protagonists) == 1:
        return protagonists[0]
    if len(protagonists) == 0:
        if len(names) == 1:
            return names[0]
        raise ContinuitySetupSeamError(
            "A1: no unique anchor — multiple characters but no protagonist-class role "
            "in role_assignments (interim rule pre-#80)"
        )
    raise ContinuitySetupSeamError(
        "A2: ambiguous anchor — multiple protagonist-class roles: "
        + ", ".join(sorted(protagonists))
    )


def ensure_interim_anchor_role_fallback_for_finalize(
    manager: Any, *, cast: list[str]
) -> None:
    """Mutate ``role_assignments`` only when needed so interim anchor resolution can succeed (pre-#80).

    If ``resolve_interim_anchor_character_id`` raises (A1/A2), applies deterministic fallback:
    first name in ``cast`` gets ``guest``, remaining names get ``staff``, via ``setdefault`` so
    explicit roles are preserved.

    Does not mark the setup seam complete; call ``finalize_continuity_setup_seam`` afterward.
    """
    if manager.scene_state is None:
        return
    ra = manager.scene_state.role_assignments or {}
    if not isinstance(ra, dict):
        ra = {}
    try:
        resolve_interim_anchor_character_id(cast, ra)
    except ContinuitySetupSeamError:
        patched = dict(ra)
        for i, name in enumerate(cast):
            patched.setdefault(name, "guest" if i == 0 else "staff")
        manager.scene_state.role_assignments = patched


def validate_completed_setup_seam(manager: Any) -> None:
    """Validate persisted seam: anchor present and in focal presence list."""
    if not getattr(manager, "setup_seam_complete", False):
        return
    aid = getattr(manager, "anchor_character_id", None)
    if aid is None or not str(aid).strip():
        raise ContinuitySetupSeamError(
            "Invalid saved continuity: setup_seam_complete but anchor_character_id missing"
        )
    anchor = str(aid).strip()
    if manager.scene_state is None:
        raise ContinuitySetupSeamError(
            "Invalid saved continuity: setup_seam_complete but scene_state missing"
        )
    present = [
        str(x).strip()
        for x in (manager.scene_state.present_characters or [])
        if str(x or "").strip()
    ]
    if anchor not in present:
        raise ContinuitySetupSeamError(
            f"Invalid saved continuity: anchor {anchor!r} not in present_characters"
        )


def finalize_continuity_setup_seam(manager: Any, *, cast: list[str]) -> None:
    """Resolve interim anchor, require anchor ∈ present_characters, mark seam complete."""
    if manager.scene_state is None:
        raise ContinuitySetupSeamError("Cannot finalize setup seam: scene_state is None")
    if getattr(manager, "setup_seam_complete", False):
        validate_completed_setup_seam(manager)
        return
    role_assignments = manager.scene_state.role_assignments or {}
    if not isinstance(role_assignments, dict):
        role_assignments = {}
    anchor = resolve_interim_anchor_character_id(cast, role_assignments)
    present = [
        str(x).strip()
        for x in (manager.scene_state.present_characters or [])
        if str(x or "").strip()
    ]
    if anchor not in present:
        raise ContinuitySetupSeamError(
            f"A1: resolved anchor {anchor!r} is not in present_characters {present!r}"
        )
    manager.anchor_character_id = anchor
    manager.setup_seam_complete = True
