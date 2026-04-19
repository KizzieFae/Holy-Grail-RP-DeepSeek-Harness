"""Test-only helpers for Issue #77 setup seam (no runtime stub)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_setup_seam_v77 import (  # noqa: E402
    ensure_interim_anchor_role_fallback_for_finalize,
    finalize_continuity_setup_seam,
)


def complete_setup_seam_for_test_manager(
    manager: Any, *, cast: list[str] | None = None
) -> None:
    """Complete the continuity setup seam using the real finalize path.

    If role_assignments do not yet yield a valid interim anchor (A1/A2 from
    resolver), assigns deterministic test roles: first cast name ``guest``,
    remaining names ``staff`` (via setdefault, so explicit test roles win).
    """
    if manager.scene_state is None:
        raise RuntimeError("complete_setup_seam_for_test_manager: scene_state is None")
    if cast is None:
        cast = [
            str(x).strip()
            for x in (manager.scene_state.present_characters or [])
            if str(x or "").strip()
        ]
    ensure_interim_anchor_role_fallback_for_finalize(manager, cast=cast)
    finalize_continuity_setup_seam(manager, cast=cast)
