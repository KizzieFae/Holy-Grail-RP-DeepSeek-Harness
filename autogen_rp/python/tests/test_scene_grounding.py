"""Tests for scene_grounding (MVP)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import pytest

from continuity_state import ConsequenceCategory, DetectedConsequence, PublicEvent
from scene_grounding import (
    MAX_SCENE_FACTS,
    compute_grounding_markers,
    empty_grounding_dict,
    format_grounding_block_body,
    format_grounding_prompt_prefix,
    rebuild_scene_grounding_from_continuity,
)


def _det(cat: ConsequenceCategory) -> DetectedConsequence:
    return DetectedConsequence(
        category=cat,
        confidence="strong",
        source_fields=["dialogue"],
        excerpt="x",
    )


def test_compute_grounding_markers_suppressants_revelation():
    move = {
        "dialogue": "Those suppressants are wrong for my physiology—I'm not a wolf.",
        "action": "",
        "motivation": {"goal": "explain", "risk_level": "low"},
    }
    detected = [_det(ConsequenceCategory.REVELATION)]
    m = compute_grounding_markers("Kizzie", move, detected)
    assert any("omega_suppressants" in x for x in m)
    assert any("wrong_for_physiology" in x for x in m)


def test_compute_grounding_markers_bunk_agreement():
    move = {
        "dialogue": "Fine, you take the top bunk on Marlene's bed.",
        "action": "",
        "motivation": {},
    }
    detected = [_det(ConsequenceCategory.AGREEMENT)]
    m = compute_grounding_markers("Kizzie", move, detected)
    assert any("sleeping_surface" in x and "top_of_bunk_marlene" in x for x in m)


def test_compute_grounding_markers_phone():
    move = {
        "dialogue": "My phone is broken.",
        "action": "",
        "motivation": {},
    }
    m = compute_grounding_markers("Willow", move, [])
    assert any("object_state:phone" in x for x in m)


def test_rebuild_and_supersede():
    class M:
        public_events = []
        turn_counter = 2

    m = M()
    ts = datetime.now(timezone.utc)
    m.public_events = [
        PublicEvent(
            event_id="e1",
            timestamp=ts,
            event_type="decision",
            participants=["A"],
            summary="s",
            turn_index=1,
            grounding_markers=[
                "assignment:sleeping_surface|surface=floor|assignee=Kizzie"
            ],
        ),
        PublicEvent(
            event_id="e2",
            timestamp=ts,
            event_type="decision",
            participants=["B"],
            summary="s2",
            turn_index=2,
            grounding_markers=[
                "assignment:sleeping_surface|surface=top_of_bunk_marlene|assignee=Kizzie"
            ],
        ),
    ]
    out = rebuild_scene_grounding_from_continuity(m)
    facts = out["facts"]
    assert len(facts) == 1
    assert facts[0]["key"] == "sleeping_surface"
    assert "top_of_bunk_marlene" in facts[0]["value"].get("surface", "")


def test_cap_facts(monkeypatch):
    import scene_grounding as sg

    monkeypatch.setattr(sg, "MAX_SCENE_FACTS", 2)
    class M:
        turn_counter = 1

    m = M()
    ts = datetime.now(timezone.utc)
    m.public_events = [
        PublicEvent(
            event_id="e_all",
            timestamp=ts,
            event_type="decision",
            participants=["X"],
            summary="s",
            turn_index=1,
            grounding_markers=[
                "medical_status:omega_suppressants|formulation=wrong_for_physiology|subject=A",
                "assignment:sleeping_surface|surface=floor|assignee=A",
                "object_state:phone|status=broken",
                "communication_state:housing_call|status=completed",
            ],
        )
    ]
    out = sg.rebuild_scene_grounding_from_continuity(m)
    assert len(out["facts"]) == 2
    cats = {f["category"] for f in out["facts"]}
    assert "medical_status" in cats
    assert "assignment" in cats


def test_format_prompt_prefix_empty():
    assert format_grounding_prompt_prefix(None) == ""
    assert format_grounding_prompt_prefix({}) == ""


def test_format_prompt_prefix_nonempty():
    d = {
        "schema_version": 1,
        "facts": [
            {
                "category": "medical_status",
                "key": "omega_suppressants",
                "value_summary": "Kizzie: suppressants wrong for physiology",
            }
        ],
    }
    p = format_grounding_prompt_prefix(d)
    assert "SETTLED SCENE FACTS" in p
    assert "wrong for physiology" in p


def test_empty_grounding_dict_shape():
    e = empty_grounding_dict()
    assert e["schema_version"] == 1
    assert e["facts"] == []


def test_format_grounding_block_body():
    body = format_grounding_block_body(
        {
            "facts": [
                {"category": "object_state", "value_summary": "Phone: broken"},
            ]
        }
    )
    assert "[object_state]" in body
    assert "Phone: broken" in body
