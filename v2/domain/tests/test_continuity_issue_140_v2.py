"""Issue #140: v2 continuity — public-event extraction, eligibility, classifier canonical text."""

import sys
from datetime import datetime
from pathlib import Path


from continuity_consequence_classifier import ConsequenceClassifier
from continuity_knowledge_helpers import perceivable_dialogue_excerpt_for_interpretation
from continuity_manager import ContinuityManager
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from continuity_state import ConsequenceCategory
from perception_audibility import (
    normalize_move_audibility,
    public_event_extraction,
    public_safe_event_summary,
)


def _decision() -> dict:
    return {
        "next_actor": "Celina",
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "test",
    }


def test_public_event_extraction_alias_matches_public_safe() -> None:
    move = {"action": "x", "dialogue": "y", "motivation": {}}
    a = public_safe_event_summary(
        acting_character="A", move=move, provisional_summary="A did"
    )
    b = public_event_extraction(
        acting_character="A", move=move, provisional_summary="A did"
    )
    assert a == b


def test_public_event_extraction_v2_no_verbatim_private_in_summary() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "leans in close."},
            {
                "type": "speech",
                "dialogue": "You must never tell anyone this secret.",
                "audibility": "private",
                "audience": ["Celina"],
            },
        ],
        "motivation": {
            "goal": "pressure",
            "tactic": "whisper",
            "emotional_driver": "fear",
            "risk_level": "high",
        },
    }
    raw = 'Ayame said: "You must never tell anyone this secret."'
    safe = public_event_extraction(
        acting_character="Ayame",
        move=move,
        provisional_summary=raw,
    )
    assert "secret" not in safe.lower()
    assert "You must never" not in safe


def test_classifier_v2_repositioning_parity_with_flat_v1_semantics() -> None:
    """Same authored action+dialogue as flat v1 via beats → same key category signal."""
    clf = ConsequenceClassifier()
    v1 = {
        "action": (
            "pushed off the table and walked around the chair to stand behind it, "
            "resting her hands on its backrest"
        ),
        "dialogue": "My legs are fine. Your terms are bullshit.",
        "motivation": {
            "goal": "break the stalemate",
            "tactic": "physically disengage from the table",
            "emotional_driver": "defiance",
            "risk_level": "high",
        },
    }
    v2 = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": v1["action"]},
            {"type": "speech", "dialogue": v1["dialogue"]},
        ],
        "motivation": v1["motivation"],
    }
    c1 = {d.category for d in clf.classify_turn("Celina", v1, _decision(), None)}
    c2 = {d.category for d in clf.classify_turn("Celina", v2, _decision(), None)}
    assert ConsequenceCategory.REPOSITIONING in c1
    assert ConsequenceCategory.REPOSITIONING in c2


def test_perceivable_dialogue_excerpt_directed_not_visible_to_non_audience() -> None:
    raw = {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "speech",
                "dialogue": "For your ears only.",
                "audibility": "directed",
                "audience": ["Celina"],
            },
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "low",
        },
    }
    norm = normalize_move_audibility(raw, "Ayame", ["Ayame", "Celina", "Mira"])
    ex_m = perceivable_dialogue_excerpt_for_interpretation(
        norm_move=norm,
        acting_character="Ayame",
        observer_character="Mira",
        max_chars=80,
    )
    assert ex_m == ""
    ex_c = perceivable_dialogue_excerpt_for_interpretation(
        norm_move=norm,
        acting_character="Ayame",
        observer_character="Celina",
        max_chars=80,
    )
    assert "For your ears only." in ex_c


def test_process_turn_v2_directed_speech_not_in_public_event_summary() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="A tense confrontation in the forge.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    complete_setup_seam_for_test_manager(manager)
    manager.process_turn(
        acting_character="Ayame",
        move={
            "move_schema_version": 2,
            "beats": [
                {"type": "action", "action": "points at Celina"},
                {
                    "type": "speech",
                    "dialogue": "Why did you sabotage the forge?",
                    "audibility": "directed",
                    "audience": ["Celina"],
                },
            ],
            "motivation": {
                "goal": "expose Celina",
                "tactic": "direct accusation",
                "emotional_driver": "anger",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "The forge fire spits sparks.",
            "tension_shift": "escalate",
            "reason": "Celina was directly accused.",
        },
        other_characters=["Celina", "Mira"],
        timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
    )
    assert len(manager.public_events) >= 1
    summary = manager.public_events[-1].summary
    assert "sabotage" not in summary.lower()
    assert "Why did you" not in summary
