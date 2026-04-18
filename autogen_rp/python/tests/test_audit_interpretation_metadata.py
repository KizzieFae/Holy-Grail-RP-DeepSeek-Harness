"""Issue #68: audit interpretation envelope and Phase 1 grounding snapshot helpers."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_interpretation_metadata import (
    attach_signal_interpretation_v1,
    build_grounding_phase1_inner,
    merge_scene_grounding_audit_family,
)


def test_build_grounding_phase1_inner_collects_refs() -> None:
    sg = {
        "schema_version": 1,
        "facts": [
            {
                "category": "object_state",
                "key": "phone",
                "source": {"kind": "continuity_event", "ref": "evt-1"},
            }
        ],
        "last_rebuilt_turn": 2,
    }
    ce = {"event_id": "evt-2"}
    p1 = build_grounding_phase1_inner(
        scene_grounding=sg,
        continuity_turn_index=3,
        continuity_event=ce,
    )
    assert p1 is not None
    assert p1["continuity_turn_index"] == 3
    assert p1["fact_count"] == 1
    assert set(p1["grounding_derivation_refs"]) == {"evt-1", "evt-2"}


def test_build_grounding_phase1_inner_omits_refs_when_empty() -> None:
    p1 = build_grounding_phase1_inner(
        scene_grounding={"facts": [], "schema_version": 1},
        continuity_turn_index=0,
        continuity_event={},
    )
    assert p1 is not None
    assert "grounding_derivation_refs" not in p1


def test_attach_signal_interpretation_v1_partial_registry() -> None:
    md: dict = {
        "progression_advisory": {"stall_score": 0.1},
        "scene_grounding": {"phase1": {"continuity_turn_index": 0, "fact_count": 0}},
    }
    attach_signal_interpretation_v1(md)
    si = md["signal_interpretation"]
    assert si["schema_version"] == 1
    assert si["signals"]["progression_advisory"]["role"] == "telemetry"
    assert si["signals"]["scene_grounding"]["role"] == "telemetry"
    assert "anti_regression_advisory" not in si["signals"]


def test_merge_scene_grounding_audit_family_summary_when_facts() -> None:
    fam = merge_scene_grounding_audit_family(
        scene_grounding_state={
            "facts": [{"category": "object_state", "key": "phone"}],
        },
        continuity_turn_index=1,
        continuity_event={},
    )
    assert fam is not None
    assert "phase1" in fam
    assert "summary" in fam
    assert "settled scene facts" in fam["summary"]


def test_no_runtime_import_of_signal_interpretation_in_enforcement() -> None:
    """Guard: progression_enforcement must not reference audit interpretation key."""
    root = Path(__file__).resolve().parent.parent / "rp_app"
    text = (root / "progression_enforcement.py").read_text(encoding="utf-8")
    assert "signal_interpretation" not in text
