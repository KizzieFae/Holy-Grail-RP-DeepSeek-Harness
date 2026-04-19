import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from continuity_state import SceneState
from offstage_prompt_filter import (
    filter_dialogue_for_offstage_character,
    filter_structured_moves_for_offstage_character,
)
from prompt_builders import build_character_turn_prompt
from response_validation_selection import get_available_actors
from scene_exit_detection import has_scene_reentry_evidence
from user_presence_signals import (
    apply_user_trigger_to_offstage,
    release_pending_forced_speaker_from_offstage,
)


def _display(name: str) -> str:
    return name.replace("_", " ")


def test_apply_user_trigger_marks_offstage_when_traveler_says_character_left() -> None:
    scene = SceneState(
        present_characters=["Willow_Reeves", "Marlene_Fletcher"],
        offstage_characters=[],
    )
    apply_user_trigger_to_offstage(
        scene_state=scene,
        trigger_text="Willow left the dorm again and headed to the garage.",
        participant_names=["Willow_Reeves", "Marlene_Fletcher"],
        get_character_display_name_fn=_display,
    )
    assert "Willow_Reeves" in scene.offstage_characters
    assert "Marlene_Fletcher" not in scene.offstage_characters


def test_apply_user_trigger_clears_offstage_on_reentry_phrase() -> None:
    scene = SceneState(
        present_characters=["Willow_Reeves", "Marlene_Fletcher"],
        offstage_characters=["Willow_Reeves"],
    )
    apply_user_trigger_to_offstage(
        scene_state=scene,
        trigger_text="Willow came back into the room.",
        participant_names=["Willow_Reeves", "Marlene_Fletcher"],
        get_character_display_name_fn=_display,
    )
    assert scene.offstage_characters == []


def test_filter_dialogue_keeps_user_and_self_only() -> None:
    recent = [
        {"role": "user", "speaker": "Traveler", "content": "I look at the door."},
        {"role": "assistant", "speaker": "Willow Reeves", "content": "My line."},
        {"role": "assistant", "speaker": "Marlene Fletcher", "content": "Not yours."},
    ]
    out = filter_dialogue_for_offstage_character(
        recent,
        char_name="Willow_Reeves",
        get_character_display_name_fn=_display,
    )
    assert len(out) == 2
    assert out[0]["role"] == "user"
    assert out[1]["speaker"] == "Willow Reeves"


def test_filter_moves_keeps_only_speaker() -> None:
    moves = [
        {"speaker": "Willow_Reeves", "action": "a"},
        {"speaker": "Marlene_Fletcher", "action": "b"},
    ]
    assert filter_structured_moves_for_offstage_character(moves, "Willow_Reeves") == [
        moves[0]
    ]


def test_has_scene_reentry_evidence_positive() -> None:
    assert has_scene_reentry_evidence(
        {"action": "She walked back into the dorm room.", "dialogue": "", "motivation": {}}
    )


def test_has_scene_reentry_evidence_requires_authored_action_or_dialogue() -> None:
    assert not has_scene_reentry_evidence(
        {
            "action": "",
            "dialogue": "",
            "motivation": {"goal": "return to the room", "tactic": ""},
        }
    )


# --- Replay-style integration slice (routing + continuity + prompt header) ---


def test_replay_slice_traveler_exit_then_available_actors_omits_offstage() -> None:
    """Mirrors: user message applies offstage before selection; Director pool excludes them."""
    scene = SceneState(
        present_characters=["Willow_Reeves", "Marlene_Fletcher", "Harley_Quinn"],
        offstage_characters=[],
    )
    # Exit regex applies to the whole trigger; name only the exiting character so
    # co-present cast are not marked offstage by the same line.
    apply_user_trigger_to_offstage(
        scene_state=scene,
        trigger_text="Willow left the room.",
        participant_names=["Willow_Reeves", "Marlene_Fletcher", "Harley_Quinn"],
        get_character_display_name_fn=_display,
    )
    eligible = [n for n in scene.present_characters]
    available = get_available_actors(
        participant_names=["Willow_Reeves", "Marlene_Fletcher", "Harley_Quinn"],
        used_actors=[],
        eligible_participants=eligible,
        offstage_characters=scene.offstage_characters,
    )
    assert "Willow_Reeves" not in available
    assert "Marlene_Fletcher" in available
    assert "Harley_Quinn" in available


def test_replay_slice_must_remain_hard_exit_keeps_present_no_offstage() -> None:
    """Departure move + must_remain: stays in present_characters; no offstage mutation."""
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm suite",
        opening_description="Roommates in the common area.",
        present_characters=["Alpha_Cast", "Beta_Cast"],
    )
    assert manager.scene_state is not None
    manager.scene_state.character_presence_constraints["Alpha_Cast"] = "must_remain"

    complete_setup_seam_for_test_manager(manager)
    manager.process_turn(
        acting_character="Alpha_Cast",
        move={
            "action": "turned on her heel and left the room",
            "dialogue": "",
            "motivation": {
                "goal": "",
                "tactic": "",
                "emotional_driver": "anger",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Beta_Cast",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Alpha exits the immediate space.",
        },
        other_characters=["Beta_Cast"],
        timestamp=datetime.fromisoformat("2026-03-27T12:00:00+00:00"),
    )

    assert "Alpha_Cast" in manager.scene_state.present_characters
    assert "Alpha_Cast" not in manager.scene_state.offstage_characters


def test_replay_slice_embodied_reentry_clears_offstage() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm suite",
        opening_description="Common area.",
        present_characters=["Alpha_Cast", "Beta_Cast"],
    )
    assert manager.scene_state is not None
    manager.scene_state.offstage_characters = ["Alpha_Cast"]

    complete_setup_seam_for_test_manager(manager)
    manager.process_turn(
        acting_character="Alpha_Cast",
        move={
            "action": "She walked back into the dorm room and shut the door.",
            "dialogue": "",
            "motivation": {
                "goal": "rejoin the confrontation",
                "tactic": "controlled return",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Beta_Cast",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Alpha returns on-stage.",
        },
        other_characters=["Beta_Cast"],
        timestamp=datetime.fromisoformat("2026-03-27T12:01:00+00:00"),
    )

    assert "Alpha_Cast" not in manager.scene_state.offstage_characters


def test_replay_slice_release_pending_forced_speaker_clears_offstage() -> None:
    scene = SceneState(
        present_characters=["Willow_Reeves", "Marlene_Fletcher"],
        offstage_characters=["Willow_Reeves"],
    )
    release_pending_forced_speaker_from_offstage(
        scene_state=scene,
        pending_forced_speaker="Willow_Reeves",
        participant_names=["Willow_Reeves", "Marlene_Fletcher"],
    )
    assert scene.offstage_characters == []


def test_replay_slice_character_prompt_includes_offstage_scope_header() -> None:
    prompt = build_character_turn_prompt(
        char_name="Ayame",
        user_name="Alex",
        trigger_text="The door stays open to the hall.",
        director_decision={"next_actor": "Ayame", "reason": "Offstage beat."},
        scene_state={
            "location": "workshop",
            "present_characters": ["Ayame", "Celina"],
            "offstage_characters": ["Ayame"],
            "absent_but_relevant": [],
        },
        scene_template_context={"template_id": "t1", "premise": "Test."},
        my_scene_role={
            "character": "Ayame",
            "role": "host",
            "presence_constraint": "must_remain",
            "authority": "high",
        },
        scene_roles=[
            {
                "character": "Ayame",
                "role": "host",
                "presence_constraint": "must_remain",
                "authority": "high",
            },
            {
                "character": "Celina",
                "role": "guest",
                "presence_constraint": "",
                "authority": "",
            },
        ],
        recent_moves=[{"speaker": "Celina", "action": "waits"}],
        recent_dialogue=[
            {"role": "assistant", "speaker": "Celina", "content": "Still here."}
        ],
        active_issues=[],
        priority_ladder=[],
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        state_context="",
        cast=["Celina"],
    )
    assert "OFFSTAGE / PERCEPTUAL SCOPE" in prompt
    assert "PERCEPTUAL SCOPE (CRITICAL)" in prompt
