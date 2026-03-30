"""Tests for scene_grounding (MVP)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import pytest

from continuity_state import (
    ConsequenceCategory,
    DetectedConsequence,
    PublicEvent,
    ResolvedOutcome,
)
from scene_grounding import (
    MAX_SCENE_FACTS,
    compute_grounding_markers,
    empty_grounding_dict,
    format_grounding_block_body,
    format_grounding_prompt_prefix,
    grounding_markers_event_summary,
    grounding_state_signals_from_move,
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


def test_compute_grounding_markers_no_sleeping_surface_marker_from_bunk_agreement():
    move = {
        "dialogue": "Fine, you take the top bunk on Marlene's bed.",
        "action": "",
        "motivation": {},
    }
    detected = [_det(ConsequenceCategory.AGREEMENT)]
    m = compute_grounding_markers("Kizzie", move, detected)
    assert not any("sleeping_surface" in x for x in m)


def test_compute_grounding_markers_no_lexical_housing_call_marker():
    move = {
        "dialogue": "Housing call is completed; res life sorted the paperwork.",
        "action": "hung up the phone",
        "motivation": {"goal": "close the housing thread", "risk_level": "low"},
    }
    detected = [
        _det(ConsequenceCategory.COMMITMENT),
        _det(ConsequenceCategory.AGREEMENT),
    ]
    m = compute_grounding_markers("Willow", move, detected)
    assert not any("housing_call" in x for x in m)


def test_compute_grounding_markers_phone():
    move = {
        "dialogue": "My phone is broken.",
        "action": "",
        "motivation": {},
    }
    m = compute_grounding_markers("Willow", move, [])
    assert any("object_state:phone" in x for x in m)


def test_compute_grounding_markers_bandage_and_weapon():
    bandage_move = {
        "dialogue": "The dressing is wrapped now.",
        "action": "",
        "motivation": {},
    }
    assert "bandage_applied" in grounding_state_signals_from_move(bandage_move)
    mb = compute_grounding_markers("Nurse", bandage_move, [])
    assert any("wound_dressing" in x for x in mb)

    weapon_move = {
        "dialogue": "",
        "action": "placed the knife on the table",
        "motivation": {},
    }
    assert "weapon_on_table" in grounding_state_signals_from_move(weapon_move)
    mw = compute_grounding_markers("Guard", weapon_move, [])
    assert any("object_state:weapon" in x and "on_table" in x for x in mw)


def test_grounding_markers_event_summary_joins_facts():
    s = grounding_markers_event_summary(
        ["object_state:phone|status=broken", "medical_status:wound_dressing|status=applied"]
    )
    assert "Phone" in s
    assert "dressing" in s.lower() or "Wound" in s


def test_rebuild_and_supersede():
    class M:
        public_events = []
        resolved_outcomes = []
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


def test_rebuild_projects_active_resolved_outcome():
    class M:
        public_events = []
        turn_counter = 3
        resolved_outcomes = [
            ResolvedOutcome(
                outcome_id="resolved_assignment_sleeping_surface_kizzie_top_bunk_marlene_e3",
                category="assignment",
                key="sleeping_surface",
                subject_id="Kizzie",
                value={
                    "assignee_id": "Kizzie",
                    "surface_id": "top_bunk_marlene",
                },
                source_event_id="e3",
                rule_id="assignment.sleeping_surface.consequence.v1",
                created_turn_index=3,
            )
        ]

    out = rebuild_scene_grounding_from_continuity(M())
    assert len(out["facts"]) == 1
    fact = out["facts"][0]
    assert fact["category"] == "assignment"
    assert fact["key"] == "sleeping_surface"
    assert fact["value"]["assignee"] == "Kizzie"
    assert fact["value"]["surface"] == "top_bunk_marlene"


def test_rebuild_prefers_active_resolved_outcome_over_old_marker_for_same_assignee():
    class M:
        turn_counter = 4

    ts = datetime.now(timezone.utc)
    m = M()
    m.public_events = [
        PublicEvent(
            event_id="e1",
            timestamp=ts,
            event_type="decision",
            participants=["Marlene_Fletcher"],
            summary="Old sleeping assignment",
            turn_index=1,
            grounding_markers=[
                "assignment:sleeping_surface|surface=floor|assignee=Kizzie"
            ],
        )
    ]
    m.resolved_outcomes = [
        ResolvedOutcome(
            outcome_id="resolved_assignment_sleeping_surface_kizzie_couch_e4",
            category="assignment",
            key="sleeping_surface",
            subject_id="Kizzie",
            value={
                "assignee_id": "Kizzie",
                "surface_id": "couch",
            },
            source_event_id="e4",
            rule_id="assignment.sleeping_surface.consequence.v1",
            created_turn_index=4,
        )
    ]

    out = rebuild_scene_grounding_from_continuity(m)
    assert len(out["facts"]) == 1
    fact = out["facts"][0]
    assert fact["value"]["surface"] == "couch"
    assert fact["supersedes"] == "e1:0"


def test_rebuild_projects_active_housing_call_resolved_outcome():
    class M:
        public_events = []
        turn_counter = 3
        resolved_outcomes = [
            ResolvedOutcome(
                outcome_id="resolved_communication_housing_call_scene_completed_e3",
                category="communication_state",
                key="housing_call",
                subject_id="scene",
                value={
                    "status": "completed",
                },
                source_event_id="e3",
                rule_id="communication.housing_call.completed.v1",
                created_turn_index=3,
                aspect_id="communication.housing_call",
                slot_key="communication.housing_call::scene",
            )
        ]

    out = rebuild_scene_grounding_from_continuity(M())
    assert len(out["facts"]) == 1
    fact = out["facts"][0]
    assert fact["category"] == "communication_state"
    assert fact["key"] == "housing_call"
    assert fact["value"]["status"] == "completed"
    assert fact["value_summary"] == "Housing call: completed"


def test_rebuild_projects_active_suppressant_formulation_resolved_outcome():
    class M:
        public_events = []
        turn_counter = 3
        resolved_outcomes = [
            ResolvedOutcome(
                outcome_id="resolved_medical_suppressant_formulation_kizzie_incompatible_e3",
                category="medical",
                key="suppressant_formulation",
                subject_id="Kizzie",
                value={
                    "status": "incompatible",
                },
                source_event_id="e3",
                rule_id="medical.suppressant_formulation.incompatible.v1",
                created_turn_index=3,
                aspect_id="medical.suppressant_formulation",
                slot_key="medical.suppressant_formulation::Kizzie",
            )
        ]

    out = rebuild_scene_grounding_from_continuity(M())
    assert len(out["facts"]) == 1
    fact = out["facts"][0]
    assert fact["category"] == "medical"
    assert fact["key"] == "suppressant_formulation"
    assert fact["value"]["subject"] == "Kizzie"
    assert fact["value"]["status"] == "incompatible"
    assert fact["value_summary"] == "Kizzie: suppressant formulation incompatible"


def test_rebuild_projects_active_location_entry_resolved_outcome():
    class M:
        public_events = []
        turn_counter = 3
        resolved_outcomes = [
            ResolvedOutcome(
                outcome_id="resolved_access_location_entry_kizzie_clinic_room_denied_e3",
                category="access",
                key="location_entry",
                subject_id="Kizzie",
                value={
                    "location_id": "clinic_room",
                    "status": "denied",
                },
                source_event_id="e3",
                rule_id="access.location_entry.denied.v1",
                created_turn_index=3,
                aspect_id="access.location_entry",
                slot_key="access.location_entry::Kizzie::clinic_room",
            )
        ]

    out = rebuild_scene_grounding_from_continuity(M())
    assert len(out["facts"]) == 1
    fact = out["facts"][0]
    assert fact["category"] == "access"
    assert fact["key"] == "location_entry"
    assert fact["value"]["subject"] == "Kizzie"
    assert fact["value"]["location"] == "clinic_room"
    assert fact["value"]["status"] == "denied"
    assert fact["value_summary"] == "Kizzie: clinic room entry denied"


def test_cap_facts(monkeypatch):
    import scene_grounding as sg

    monkeypatch.setattr(sg, "MAX_SCENE_FACTS", 2)
    class M:
        turn_counter = 1
        resolved_outcomes = []

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
