"""Issue #77 — setup seam, interim anchor, D3."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from continuity_setup_seam_v77 import (
    ContinuitySetupSeamError,
    ContinuitySetupSeamIncompleteError,
    finalize_continuity_setup_seam,
    resolve_interim_anchor_character_id,
)


def test_resolve_single_protagonist_role() -> None:
    aid = resolve_interim_anchor_character_id(
        ["Alice", "Bob"],
        {"Alice": "staff", "Bob": "guest"},
    )
    assert aid == "Bob"


def test_resolve_singleton_cast_without_roles() -> None:
    assert resolve_interim_anchor_character_id(["Zoe"], {}) == "Zoe"


def test_a2_multiple_protagonists() -> None:
    with pytest.raises(ContinuitySetupSeamError, match="A2"):
        resolve_interim_anchor_character_id(
            ["A", "B"],
            {"A": "patient", "B": "guest"},
        )


def test_a1_multi_cast_no_protagonist_marker() -> None:
    with pytest.raises(ContinuitySetupSeamError, match="A1"):
        resolve_interim_anchor_character_id(
            ["A", "B"],
            {"A": "staff", "B": "staff"},
        )


def test_finalize_requires_anchor_in_present() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["P1", "P2"],
    )
    assert m.scene_state is not None
    m.scene_state.role_assignments = {"P1": "guest", "P2": "staff"}
    m.scene_state.present_characters = ["P2"]
    with pytest.raises(ContinuitySetupSeamError, match="not in present_characters"):
        finalize_continuity_setup_seam(m, cast=["P1", "P2"])


def test_d3_process_turn_blocked_before_finalize() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B"],
    )
    assert m.scene_state is not None
    m.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    m.setup_seam_complete = False
    m.anchor_character_id = None
    with pytest.raises(ContinuitySetupSeamIncompleteError, match="D3"):
        m.process_turn(
            acting_character="A",
            move={"action": "x", "dialogue": "y", "motivation": {}},
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )


def test_finalize_marks_complete_and_allows_process_turn() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B"],
    )
    assert m.scene_state is not None
    m.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    m.setup_seam_complete = False
    m.anchor_character_id = None
    finalize_continuity_setup_seam(m, cast=["A", "B"])
    assert m.setup_seam_complete
    assert m.anchor_character_id == "A"
    m.process_turn(
        acting_character="A",
        move={"action": "x", "dialogue": "y", "motivation": {}},
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
