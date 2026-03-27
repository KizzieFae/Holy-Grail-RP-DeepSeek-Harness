import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from orchestration_helpers import ensure_orchestration_state, resolve_continuation_override_actor


def test_descriptive_exit_updates_authoritative_presence_state() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm 303",
        opening_description="The argument spills across the threshold.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    manager.process_turn(
        acting_character="Mira",
        move={
            "action": "let the door swing shut behind her and stalked down the hallway toward the stairwell without looking back",
            "dialogue": "",
            "motivation": {
                "goal": "remove herself from the confrontation entirely",
                "tactic": "put the hallway and stairwell between herself and the room",
                "emotional_driver": "anger",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Ayame",
            "environment_event": "The door shudders in Mira's wake.",
            "tension_shift": "steady",
            "reason": "Mira leaves the room rather than continuing the exchange.",
        },
        other_characters=["Ayame", "Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:02:30"),
    )

    assert "Mira" not in manager.scene_state.present_characters
    assert "Mira" in manager.scene_state.absent_but_relevant
    assert manager.public_events[0].state_changes == ["Mira left the immediate scene."]


def test_resolve_continuation_override_actor_allows_one_step_owned_continuation() -> None:
    orchestration_state = ensure_orchestration_state(None)
    orchestration_state["recent_structured_moves"] = [
        {
            "speaker": "Ayame",
            "action": "steps into Celina's path",
            "dialogue": "No.",
            "motivation": {
                "goal": "hold the doorway and force Celina to stop",
                "tactic": "maintain the physical block until Celina yields",
            },
        }
    ]
    orchestration_state["spotlight_history"] = ["Ayame"]
    continuity_manager = SimpleNamespace(
        turn_counter=1,
        turn_metadata_by_index={1: {"tags": ["authority_asserted"]}},
    )

    assert (
        resolve_continuation_override_actor(
            orchestration_state=orchestration_state,
            continuity_manager=continuity_manager,
            eligible_participants=["Ayame", "Celina"],
            actors_used_this_round=["Ayame"],
        )
        == "Ayame"
    )


def test_resolve_continuation_override_actor_rejects_superseded_line() -> None:
    orchestration_state = ensure_orchestration_state(None)
    orchestration_state["recent_structured_moves"] = [
        {
            "speaker": "Ayame",
            "action": "steps into Celina's path",
            "dialogue": "No.",
            "motivation": {
                "goal": "hold the doorway and force Celina to stop",
                "tactic": "maintain the physical block until Celina yields",
            },
        }
    ]
    orchestration_state["spotlight_history"] = ["Ayame"]
    continuity_manager = SimpleNamespace(
        turn_counter=1,
        turn_metadata_by_index={1: {"tags": ["refusal"]}},
    )

    assert (
        resolve_continuation_override_actor(
            orchestration_state=orchestration_state,
            continuity_manager=continuity_manager,
            eligible_participants=["Ayame", "Celina"],
            actors_used_this_round=["Ayame"],
        )
        is None
    )
