"""Test-only helpers for Issue #77 setup seam (no runtime stub)."""

from __future__ import annotations

from typing import Any

from continuity_setup_seam_v77 import (
    ensure_interim_anchor_role_fallback_for_finalize,
    finalize_continuity_setup_seam,
)


def complete_setup_seam_for_test_manager(
    manager: Any, *, cast: list[str] | None = None
) -> None:
    """Complete the continuity setup seam using the real finalize path.

    Template-driven scenes (``scene_template_id``) must already have
    ``anchor_role_name`` and ``role_assignments`` suitable for Issue #80.

    Non-template tests: if interim anchor resolution fails, patch guest/staff
    via ``ensure_interim_anchor_role_fallback_for_finalize`` (legacy).
    """
    if manager.scene_state is None:
        raise RuntimeError("complete_setup_seam_for_test_manager: scene_state is None")
    if cast is None:
        cast = [
            str(x).strip()
            for x in (manager.scene_state.present_characters or [])
            if str(x or "").strip()
        ]
    if str(getattr(manager.scene_state, "scene_template_id", None) or "").strip():
        finalize_continuity_setup_seam(manager, cast=cast)
    else:
        ensure_interim_anchor_role_fallback_for_finalize(manager, cast=cast)
        finalize_continuity_setup_seam(manager, cast=cast)
