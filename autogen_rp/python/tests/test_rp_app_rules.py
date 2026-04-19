import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_continuity import restore_or_initialize_continuity_manager
from app_state_scene import build_initial_scene_issues
from app import (
    get_player_control_mode,
    has_player_character_conflict,
    resolve_bot_reply_limit,
)
from character_state import CharacterState
from continuity_state import CanonAnchor
from prompt_builders import build_character_turn_prompt
from response_validation import (
    build_attempted_post_details,
    eligible_agent_keys_for_present_characters,
    get_available_actors,
    is_duplicate_content,
    is_duplicate_dialogue,
    parse_director_decision,
    validate_bot_response,
)
from response_validation_presence import detect_scene_presence_violation
from scene_exit_detection import detect_exit_from_scene
from semantic_validation import (
    _extract_json_object_text,
    reconcile_turn_selection_issues,
    should_override_presence_rejection,
    should_use_narrator_fallback,
)
from session_manager import SESSION_INDEX_FILE_NAME, SessionManager


def test_build_character_turn_prompt_includes_witness_passivity_guidance() -> None:
    prompt_source = inspect.getsource(build_character_turn_prompt)

    assert "default to staying occupied with your own business" in prompt_source
    assert (
        "fear, hierarchy, and institutional pressure often suppress speech"
        in prompt_source
    )
    assert "do not address them like a casual peer" in prompt_source
    assert "Dialogue may be empty" in prompt_source


def test_build_initial_scene_issues_seeds_recovery_watch_pressures() -> None:
    issues = build_initial_scene_issues(
        {
            "template_id": "celina_apartment_recovery_watch",
            "premise": "Celina's apartment is functioning as a secluded safehouse immediately after a dangerous rescue, with the protector trying to stabilize a vulnerable Demi-human while outside criminal pressure remains offscreen.",
            "role_assignments": {
                "Celina": "protector",
                "Kizzie": "recovering_demi_human",
            },
        }
    )

    descriptions = [issue.description for issue in issues]
    assert any(
        "Assess and stabilize Kizzie's injuries" in description
        for description in descriptions
    )
    assert any(
        "Establish whether Kizzie led immediate danger directly to this refuge"
        in description
        for description in descriptions
    )
    assert any(
        "Determine whether outside danger can reach Kizzie here" in description
        for description in descriptions
    )
    route_issue = next(
        issue
        for issue in issues
        if "led immediate danger directly to this refuge" in issue.description
    )
    assert "didn't lead anyone here" in route_issue.resolution_signals


def test_restore_or_initialize_continuity_manager_passes_seeded_initial_issues() -> (
    None
):
    class FakeManager:
        def __init__(self) -> None:
            self.scene_state = None
            self.captured_initial_issues = None

        def initialize_scene(
            self, location, opening_description, present_characters, initial_issues=None
        ) -> None:
            self.captured_initial_issues = list(initial_issues or [])
            self.scene_state = SimpleNamespace(
                present_characters=list(present_characters),
                opening_description=opening_description,
            )

        def bootstrap_present_characters_from_cast(
            self, character_names: list[str]
        ) -> None:
            if self.scene_state is None:
                return
            cur = getattr(self.scene_state, "present_characters", None) or []
            if not cur and character_names:
                self.scene_state.present_characters = list(character_names)

    fake_st = SimpleNamespace(session_state={})
    manager = restore_or_initialize_continuity_manager(
        st_module=fake_st,
        continuity_state=None,
        character_names=["Celina", "Kizzie"],
        opening_description="Opening line.",
        scene_setup={
            "template_id": "celina_apartment_recovery_watch",
            "premise": "Celina's apartment is functioning as a secluded safehouse immediately after a dangerous rescue, with the protector trying to stabilize a vulnerable Demi-human while outside criminal pressure remains offscreen.",
            "role_assignments": {
                "Celina": "protector",
                "Kizzie": "recovering_demi_human",
            },
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Kizzie": "must_remain",
            },
            "character_authority_labels": {"Celina": "high", "Kizzie": "low"},
        },
        continuity_manager_cls=FakeManager,
        build_initial_scene_issues_fn=build_initial_scene_issues,
        apply_scene_setup_to_scene_state_fn=lambda *_args, **_kwargs: None,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert manager.captured_initial_issues is not None
    assert len(manager.captured_initial_issues) == 3
    descriptions = [issue.description for issue in manager.captured_initial_issues]
    assert any(
        "Assess and stabilize Kizzie's injuries" in description
        for description in descriptions
    )
    assert any(
        "Establish whether Kizzie led immediate danger directly to this refuge"
        in description
        for description in descriptions
    )
    assert any(
        "Determine whether outside danger can reach Kizzie here" in description
        for description in descriptions
    )


def test_get_available_actors_excludes_used_actors() -> None:
    assert get_available_actors(["Ayame", "Celina", "Mira"], ["Ayame"]) == [
        "Celina",
        "Mira",
    ]


def test_get_available_actors_respects_authoritative_eligible_participants() -> None:
    assert get_available_actors(
        ["Ayame", "Celina", "Mira"],
        ["Ayame"],
        ["Celina"],
    ) == ["Celina"]


def test_get_available_actors_excludes_offstage_characters() -> None:
    assert get_available_actors(
        ["Ayame", "Celina", "Mira"],
        [],
        ["Ayame", "Celina", "Mira"],
        ["Celina"],
    ) == ["Ayame", "Mira"]


def test_resolve_bot_reply_limit_defaults_to_active_bot_count() -> None:
    assert resolve_bot_reply_limit(3, None) == 3


def test_resolve_bot_reply_limit_clamps_to_available_bots() -> None:
    assert resolve_bot_reply_limit(3, 5) == 3


def test_parse_director_decision_accepts_available_actor() -> None:
    decision, error = parse_director_decision(
        json.dumps(
            {
                "next_actor": "Ayame",
                "environment_event": "",
                "tension_shift": "steady",
                "reason": "Ayame was directly addressed.",
            }
        ),
        ["Ayame", "Celina", "Mira"],
        ["Ayame", "Mira"],
    )

    assert error == ""
    assert decision is not None
    assert decision["next_actor"] == "Ayame"


def test_parse_director_decision_rejects_actor_outside_available_list() -> None:
    decision, error = parse_director_decision(
        json.dumps(
            {
                "next_actor": "Celina",
                "environment_event": "",
                "tension_shift": "steady",
                "reason": "Celina should not be chosen.",
            }
        ),
        ["Ayame", "Celina", "Mira"],
        ["Ayame", "Mira"],
    )

    assert decision is None
    assert "Invalid next_actor" in error


def test_eligible_agent_keys_maps_display_names_to_agent_keys() -> None:
    def display_name_for_key(agent_key: str) -> str:
        if agent_key == "Hannah_Lovelace":
            return "Hannah Lovelace"
        return agent_key

    assert eligible_agent_keys_for_present_characters(
        ["Ayame", "Hannah Lovelace", "Celina"],
        ["Ayame", "Celina", "Hannah_Lovelace"],
        display_name_for_key=display_name_for_key,
    ) == ["Ayame", "Hannah_Lovelace", "Celina"]


def test_parse_director_decision_normalizes_display_name_when_allowed() -> None:
    decision, error = parse_director_decision(
        json.dumps(
            {
                "next_actor": "Hannah Lovelace",
                "environment_event": "",
                "tension_shift": "steady",
                "reason": "Hannah was addressed.",
            }
        ),
        ["Ayame", "Celina", "Hannah_Lovelace"],
        ["Ayame", "Hannah_Lovelace"],
    )
    assert error == ""
    assert decision is not None
    assert decision["next_actor"] == "Hannah_Lovelace"


def test_parse_director_decision_allows_end_round_without_next_actor() -> None:
    decision, error = parse_director_decision(
        json.dumps(
            {
                "end_round": True,
                "environment_event": "",
                "tension_shift": "steady",
                "reason": "Enough reactions for this beat.",
            }
        ),
        ["Ayame", "Celina", "Mira"],
        ["Ayame", "Mira"],
    )

    assert error == ""
    assert decision is not None
    assert decision["end_round"] is True
    assert decision["next_actor"] == ""


def test_build_attempted_post_details_includes_human_readable_attempted_message() -> (
    None
):
    details = build_attempted_post_details(
        raw_response='{"action": "steps forward", "dialogue": "You answer to me.", "motivation": {"goal": "dominate", "tactic": "threaten", "emotional_driver": "cruel amusement", "risk_level": "high"}}',
        parsed_output={
            "action": "steps forward",
            "dialogue": "You answer to me.",
            "motivation": {
                "goal": "dominate",
                "tactic": "threaten",
                "emotional_driver": "cruel amusement",
                "risk_level": "high",
            },
        },
    )

    assert details["action"] == "steps forward"
    assert details["dialogue"] == "You answer to me."
    assert "Action: steps forward" in details["attempted_message"]
    assert 'Dialogue: "You answer to me."' in details["attempted_message"]
    assert "goal=dominate" in details["attempted_message"]
    assert details["raw_response"].startswith('{"action": "steps forward"')


def test_get_player_control_mode_for_predefined_character() -> None:
    assert get_player_control_mode("ayame") == "human_controlled_character"


def test_get_player_control_mode_for_custom_persona() -> None:
    assert get_player_control_mode(None) == "human_controlled_custom_persona"


def test_has_player_character_conflict_detects_duplicate_identity() -> None:
    assert has_player_character_conflict(["ayame", "celina"], "ayame") is True


def test_has_player_character_conflict_allows_distinct_player_and_bots() -> None:
    assert has_player_character_conflict(["ayame", "celina"], "mira") is False


def test_finalize_incomplete_sessions_marks_active_sessions_closed(
    tmp_path: Path,
) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="active_scene",
        team_state={"scene": "state"},
        characters=["Ayame", "Celina"],
        metadata={"scene_status": "active"},
        chat_history=[{"role": "user", "content": "Hello"}],
    )

    recovered = manager.finalize_incomplete_sessions()
    recovered_session = manager.load_session("active_scene")

    assert recovered == ["active_scene"]
    assert recovered_session["metadata"]["scene_status"] == "closed"
    assert recovered_session["metadata"]["scene_closed_reason"] == "startup_recovery"
    assert recovered_session["metadata"]["recovered_on_startup"] is True


def test_finalize_incomplete_sessions_leaves_closed_sessions_unchanged(
    tmp_path: Path,
) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="closed_scene",
        team_state={"scene": "state"},
        characters=["Ayame"],
        metadata={"scene_status": "closed", "scene_closed_reason": "user_ended"},
        chat_history=[{"role": "user", "content": "Bye"}],
    )

    recovered = manager.finalize_incomplete_sessions()
    session_data = manager.load_session("closed_scene")

    assert recovered == []
    assert session_data["metadata"]["scene_status"] == "closed"
    assert session_data["metadata"]["scene_closed_reason"] == "user_ended"


def test_save_session_preserves_player_control_mode_metadata(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="player_scene",
        team_state={"scene": "state"},
        characters=["Ayame", "Celina"],
        metadata={
            "player_control_mode": "human_controlled_character",
            "scene_status": "closed",
        },
        player_character="ayame",
        chat_history=[{"role": "user", "content": "Hello"}],
    )

    session_data = manager.load_session("player_scene")

    assert (
        session_data["metadata"]["player_control_mode"] == "human_controlled_character"
    )
    assert session_data["player_character"] == "ayame"


def test_save_session_uses_timezone_aware_utc_saved_at(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="utc_scene",
        team_state={"scene": "state"},
        characters=["Ayame"],
        metadata={"scene_status": "closed"},
        chat_history=[],
    )

    session_data = manager.load_session("utc_scene")
    saved_at = datetime.fromisoformat(session_data["saved_at"])

    assert saved_at.tzinfo is not None
    assert saved_at.utcoffset() is not None
    assert saved_at.utcoffset().total_seconds() == 0


def test_canon_anchor_from_dict_normalizes_legacy_naive_timestamp_to_utc() -> None:
    anchor = CanonAnchor.from_dict(
        {
            "anchor_id": "canon_ayame_voice",
            "category": "character_voice",
            "subject": "Ayame",
            "statement": "Ayame speaks carefully.",
            "source": "legacy_fixture",
            "established_at": "2026-03-17T12:34:56",
            "protected": True,
        }
    )

    assert anchor.established_at.tzinfo is not None
    assert anchor.established_at.utcoffset() is not None
    assert anchor.established_at.utcoffset().total_seconds() == 0


def test_get_cross_session_memories_aggregates_memory_buckets_and_user_relationships(
    tmp_path: Path,
) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="session_one",
        team_state={"scene": "state"},
        characters=["Ayame", "Celina"],
        metadata={
            "summary": "Session one summary",
            "memory_buckets": {
                "session_summary": "Ayame and Celina argued in the workshop.",
                "persistent_world_facts": [
                    "The workshop forge is central to the conflict."
                ],
                "user_preferences": ["Call me Alex."],
            },
            "character_states": {
                "Ayame": {
                    "name": "Ayame",
                    "relationships": {
                        "Alex": {
                            "entity_type": "user",
                            "history": ["Alex said or signaled: Call me Alex."],
                            "trust": 6,
                            "interaction_count": 1,
                            "last_summary": "Alex said or signaled: Call me Alex.",
                        }
                    },
                }
            },
        },
        chat_history=[],
    )
    manager.save_session(
        session_id="session_two",
        team_state={"scene": "state"},
        characters=["Ayame"],
        metadata={
            "summary": "Session two summary",
            "memory_buckets": {
                "session_summary": "Ayame met Alex again near the forge.",
                "persistent_world_facts": ["Smoke still hangs over the workshop."],
                "user_preferences": ["I prefer direct answers."],
            },
            "character_states": {
                "Ayame": {
                    "name": "Ayame",
                    "relationships": {
                        "Alex": {
                            "entity_type": "user",
                            "history": [
                                "Alex said or signaled: I prefer direct answers."
                            ],
                            "trust": 7,
                            "interaction_count": 2,
                            "last_summary": "Alex said or signaled: I prefer direct answers.",
                        }
                    },
                }
            },
        },
        chat_history=[],
    )

    memories = manager.get_cross_session_memories(
        character_names=["Ayame", "Celina"],
        user_name="Alex",
    )

    assert memories["session_summaries"]
    assert "Ayame met Alex again near the forge." in memories["session_summaries"]
    assert (
        "The workshop forge is central to the conflict."
        in memories["persistent_world_facts"]
    )
    assert "Call me Alex." in memories["user_preferences"]
    assert memories["character_user_memories"]["Ayame"]
    assert memories["cross_session_relationships"]["Ayame"]["entity_type"] == "user"
    assert memories["indexed_session_count"] == 2
    assert memories["relationship_trends"]["Ayame"]["trend"] == "improving"
    assert (tmp_path / SESSION_INDEX_FILE_NAME).exists()


def test_validate_bot_response_allows_must_remain_offstage_exit_move() -> None:
    is_valid, reason = validate_bot_response(
        content="turns toward the door",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        move={
            "action": "turns to leave the room",
            "dialogue": "",
            "motivation": {
                "goal": "withdraw",
                "tactic": "exit",
                "emotional_driver": "annoyance",
                "risk_level": "low",
            },
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "role_assignments": {"Celina": "guard", "Ayame": "host"},
        },
    )

    assert is_valid is True
    assert reason == ""


def test_detect_exit_from_scene_recognizes_descriptive_boundary_crossing() -> None:
    assert (
        detect_exit_from_scene(
            {
                "action": "let the door swing shut behind her and stood motionless in the hallway outside the room",
                "dialogue": "",
                "motivation": {
                    "goal": "withdraw from the confrontation",
                    "tactic": "put the hallway and a closed door between herself and the room",
                },
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room with a narrow hallway outside the door.",
            },
        )
        is True
    )


def test_detect_exit_from_scene_does_not_false_positive_on_left_hand_empty_phrase() -> (
    None
):
    assert (
        detect_exit_from_scene(
            {
                "action": "let the suitcase handle go with a sharp, sudden release that left her hand empty",
                "dialogue": "",
                "motivation": {
                    "goal": "release the suitcase",
                    "tactic": "drop it",
                },
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room.",
            },
        )
        is False
    )


def test_detect_exit_from_scene_does_not_false_positive_on_goddamn_substring() -> None:
    assert (
        detect_exit_from_scene(
            {
                "action": "snatched the suitcase handle out of Marlene's grip with a sharp jerk",
                "dialogue": "Nobody touches her shit without permission. You sleep on the floor or in the goddamn hallway.",
                "motivation": {
                    "goal": "reassert control",
                    "tactic": "issue ultimatum",
                },
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room.",
            },
        )
        is False
    )


def test_detect_exit_from_scene_does_not_false_positive_on_head_snapping_toward_hallway() -> (
    None
):
    assert (
        detect_exit_from_scene(
            {
                "action": "froze halfway to the bedroom door, her head snapping toward the hallway as the scent hit her like a physical blow",
                "dialogue": "Fuck.",
                "motivation": {
                    "goal": "assess the threat",
                    "tactic": "freeze and listen",
                },
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room.",
            },
        )
        is False
    )


def test_detect_exit_from_scene_does_not_false_positive_on_dont_leave_me_hanging_idiom() -> (
    None
):
    assert (
        detect_exit_from_scene(
            {
                "action": "spun on her heel with a wide grin",
                "dialogue": "C'mon, puppy, don't leave a girl hangin'!",
                "motivation": {
                    "goal": "provoke a reaction",
                    "tactic": "taunt",
                },
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room.",
            },
        )
        is False
    )


def test_detect_exit_from_scene_recognizes_headed_out_exit_statement() -> None:
    assert (
        detect_exit_from_scene(
            {
                "action": "grabbed her jacket and headed out the door",
                "dialogue": "",
                "motivation": {"goal": "leave", "tactic": "depart"},
            },
            {
                "location": "Dorm 303",
                "environment_description": "A cramped dorm room.",
            },
        )
        is True
    )


def test_validate_bot_response_allows_must_remain_ultimatum_walk_out() -> None:
    is_valid, reason = validate_bot_response(
        content='Willow plants herself in the doorway. "Walk out, or I carry you."',
        speaker="Willow",
        user_name="Marlene",
        chat_history=[],
        move={
            "action": "plants herself in the doorway",
            "dialogue": "Walk out, or I carry you.",
            "motivation": {
                "goal": "force a choice",
                "tactic": "ultimatum",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
        },
        scene_state={
            "character_presence_constraints": {
                "Willow": "must_remain",
                "Marlene": "must_remain",
            },
            "role_assignments": {"Willow": "ra", "Marlene": "resident"},
        },
    )
    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_allows_must_remain_hallway_offstage() -> None:
    is_valid, reason = validate_bot_response(
        content="let the door swing shut behind her and stood motionless in the hallway outside the room",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        move={
            "action": "let the door swing shut behind her and stood motionless in the hallway outside the room",
            "dialogue": "",
            "motivation": {
                "goal": "withdraw from the confrontation",
                "tactic": "put the hallway and a closed door between herself and the room",
                "emotional_driver": "anger",
                "risk_level": "medium",
            },
        },
        scene_state={
            "location": "Dorm 303",
            "environment_description": "A cramped dorm room with a narrow hallway outside the door.",
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "role_assignments": {"Celina": "guard", "Ayame": "host"},
        },
    )

    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_rejects_absence_claim_for_must_remain_character() -> (
    None
):
    is_valid, reason = validate_bot_response(
        content="Ayame isn't here anymore.",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        move={
            "action": "glances around the empty hall",
            "dialogue": "Ayame isn't here anymore.",
            "motivation": {
                "goal": "misdirect",
                "tactic": "false claim",
                "emotional_driver": "guarded focus",
                "risk_level": "medium",
            },
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "role_assignments": {"Celina": "guard", "Ayame": "host"},
        },
    )

    assert is_valid is False
    assert "Ayame" in reason


def test_validate_bot_response_allows_absence_claim_when_target_is_offstage() -> None:
    is_valid, reason = validate_bot_response(
        content="Ayame isn't here anymore.",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        move={
            "action": "glances toward the hallway",
            "dialogue": "Ayame isn't here anymore.",
            "motivation": {
                "goal": "report status",
                "tactic": "plain statement",
                "emotional_driver": "neutral",
                "risk_level": "low",
            },
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "role_assignments": {"Celina": "guard", "Ayame": "host"},
            "offstage_characters": ["Ayame"],
            "present_characters": ["Celina", "Ayame"],
        },
    )

    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_allows_absence_claim_when_target_temporary_offstage() -> (
    None
):
    is_valid, reason = validate_bot_response(
        content="Ayame isn't here in the dorm right now.",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        move={
            "action": "checks the doorway",
            "dialogue": "Ayame isn't here in the dorm right now.",
            "motivation": {},
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "present_characters": ["Celina", "Ayame"],
            "character_presence_status": {"Ayame": "temporary_offstage"},
        },
    )

    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_rejects_private_prior_dialogue_reuse() -> None:
    private_line = (
        "The emergency phrase is sapphire nine seven tango full stop for the room."
    )
    assert len(private_line) >= 30
    chat_history = [
        {
            "role": "assistant",
            "actor": "Celina",
            "speaker": "Celina",
            "content": "Narrator render omitted.",
            "move": {
                "action": "leans in close",
                "dialogue": private_line,
                "audibility": "private",
                "audience": [],
            },
        }
    ]
    move_text = f'repeats aloud, "{private_line}"'
    is_valid, reason = validate_bot_response(
        content=move_text,
        speaker="Marlene",
        user_name="Alex",
        chat_history=chat_history,
        move={
            "action": 'repeats aloud verbatim what she could not have heard',
            "dialogue": private_line,
            "motivation": {},
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Marlene": "must_remain",
                "Ayame": "must_remain",
            },
            "present_characters": ["Celina", "Marlene", "Ayame"],
        },
    )

    assert is_valid is False
    assert reason.startswith("[PERCEPTION]")


def test_validate_bot_response_allows_public_prior_dialogue_reuse() -> None:
    public_line = (
        "The emergency phrase is sapphire nine seven tango full stop for the room."
    )
    chat_history = [
        {
            "role": "assistant",
            "actor": "Celina",
            "speaker": "Celina",
            "content": "Narrator render omitted.",
            "move": {
                "action": "speaks clearly to the room",
                "dialogue": public_line,
                "audibility": "public",
                "audience": [],
            },
        }
    ]
    move_text = f"echoes back: {public_line}"
    is_valid, reason = validate_bot_response(
        content=move_text,
        speaker="Marlene",
        user_name="Alex",
        chat_history=chat_history,
        move={
            "action": "nods and repeats the phrase for emphasis",
            "dialogue": public_line,
            "motivation": {},
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Marlene": "must_remain",
                "Ayame": "must_remain",
            },
            "present_characters": ["Celina", "Marlene", "Ayame"],
        },
    )

    assert is_valid is True
    assert reason == ""


def test_detect_scene_presence_violation_skips_perception_when_chat_history_none() -> (
    None
):
    private_line = (
        "The emergency phrase is sapphire nine seven tango full stop for the room."
    )
    scene_state = {
        "character_presence_constraints": {
            "Celina": "must_remain",
            "Marlene": "must_remain",
        },
        "present_characters": ["Celina", "Marlene"],
    }
    move_text = private_line
    has_v, r = detect_scene_presence_violation(
        move_text,
        "Marlene",
        move={"action": "", "dialogue": private_line},
        scene_state=scene_state,
        chat_history=None,
    )
    assert has_v is False
    assert r == ""


def test_is_duplicate_dialogue_allows_shared_long_prefix_with_short_remainders() -> None:
    """Phase 4: same 60-char opening but tails under REMAINDER_MIN — not fuzzy duplicate."""
    common = "w" * 60
    tail_a = "x" * 10
    tail_b = "y" * 10
    d1 = common + tail_a
    d2 = common + tail_b
    assert len(d1) > 60 and len(d2) > 60
    chat = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "move": {"dialogue": d1},
        }
    ]
    is_dup, _reason = is_duplicate_dialogue(
        speaker="Marlene", dialogue=d2, chat_history=chat
    )
    assert is_dup is False


def test_is_duplicate_dialogue_rejects_fuzzy_prefix_when_remainders_substantial() -> None:
    common = "z" * 60
    tail = "t" * 30
    d1 = common + tail
    d2 = common + tail.replace("t", "u")  # same lengths, different tail
    assert d1[:60] == d2[:60]
    assert min(len(d1) - 60, len(d2) - 60) >= 25
    chat = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "move": {"dialogue": d1},
        }
    ]
    is_dup, reason = is_duplicate_dialogue(
        speaker="Marlene", dialogue=d2, chat_history=chat
    )
    assert is_dup is True
    assert "overlap" in reason.lower()


def test_is_duplicate_dialogue_allows_short_substring_inside_long_line() -> None:
    """Embedded phrase too small a fraction of longer line — not duplicate."""
    short = "b" * 40
    long_line = ("a" * 50) + short + ("c" * 80)
    assert len(short) >= 40
    assert short in long_line
    assert len(short) / len(long_line) < 0.65
    chat = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "move": {"dialogue": long_line},
        }
    ]
    is_dup, _reason = is_duplicate_dialogue(
        speaker="Marlene", dialogue=short, chat_history=chat
    )
    assert is_dup is False


def test_is_duplicate_dialogue_rejects_near_full_substring_reuse() -> None:
    # Fuzzy substring runs only when both sides exceed the long-text threshold (>60).
    short = "c" * 65
    long_line = short + " tail"
    assert len(short) >= 40
    assert len(short) / len(long_line) >= 0.65
    assert len(short) > 60 and len(long_line) > 60
    chat = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "move": {"dialogue": long_line},
        }
    ]
    is_dup, reason = is_duplicate_dialogue(
        speaker="Marlene", dialogue=short, chat_history=chat
    )
    assert is_dup is True
    assert "structure" in reason.lower()


def test_is_duplicate_content_allows_shared_prefix_with_short_remainders() -> None:
    common = "p" * 50
    c1 = common + "q" * 10
    c2 = common + "r" * 10
    chat = [{"role": "assistant", "content": c1}]
    is_dup, _reason = is_duplicate_content(c2, chat)
    assert is_dup is False


def test_validate_bot_response_rejects_duplicate_dialogue_even_if_action_differs() -> (
    None
):
    prior_dialogue = (
        "Oh, honey, you don't get to turn this into a prison cafeteria just 'cause you're scared "
        "of a little happy scent. You cook, fine. But 'stay out of your way' ain't the deal. "
        "The deal is we figure this out together, 'cause she's ours now. And if you think I'm "
        "lettin' you treat her like a mistake you can just ignore, you're about as wrong as a wolf "
        "in a cat show."
    )

    chat_history = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "content": "Some rendered text.",
            "move": {"action": "did something", "dialogue": prior_dialogue},
        }
    ]

    is_valid, reason = validate_bot_response(
        content="Different action lead-in. " + prior_dialogue,
        speaker="Marlene",
        user_name="Kizzie",
        chat_history=chat_history,
        move={
            "action": "different action",
            "dialogue": prior_dialogue,
            "motivation": {},
        },
        scene_state={},
    )

    assert is_valid is False
    assert reason.startswith("[DUPLICATE]")


def test_validate_bot_response_pipeline_order_duplicate_before_character_drift() -> None:
    """Quality/repetition runs before identity/drift; duplicate dialogue wins first."""
    prior_dialogue = (
        "This is duplicate dialogue text that is long enough for the duplicate check "
        "to run and match exactly between turns without being skipped."
    )
    chat_history = [
        {
            "role": "assistant",
            "speaker": "Marlene",
            "content": "Rendered.",
            "move": {"action": "prior beat", "dialogue": prior_dialogue},
        }
    ]
    is_valid, reason = validate_bot_response(
        content="Marlene's eyes narrowed with contempt while she spoke.",
        speaker="Marlene",
        user_name="Kizzie",
        chat_history=chat_history,
        move={
            "action": "stares down the room",
            "dialogue": prior_dialogue,
            "motivation": {},
        },
        scene_state={},
    )
    assert is_valid is False
    assert reason.startswith("[DUPLICATE]")
    assert "[CHARACTER_DRIFT]" not in reason


def test_validate_bot_response_pipeline_order_duplicate_before_scene_presence() -> None:
    """Quality/repetition runs before scene-truth; duplicate dialogue wins first."""
    prior_dialogue = (
        "Repeated line for duplicate detection that is long enough to qualify "
        "and must match the new move dialogue byte-for-byte after normalization."
    )
    chat_history = [
        {
            "role": "assistant",
            "speaker": "Celina",
            "content": "Earlier render.",
            "move": {"action": "prior", "dialogue": prior_dialogue},
        }
    ]
    is_valid, reason = validate_bot_response(
        content="Celina studies the door.",
        speaker="Celina",
        user_name="Alex",
        chat_history=chat_history,
        move={
            "action": "mutters that Ayame isn't here anymore",
            "dialogue": prior_dialogue,
            "motivation": {
                "goal": "misdirect",
                "tactic": "false claim",
                "emotional_driver": "guarded focus",
                "risk_level": "medium",
            },
        },
        scene_state={
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Ayame": "must_remain",
            },
            "role_assignments": {"Celina": "guard", "Ayame": "host"},
        },
    )
    assert is_valid is False
    assert reason.startswith("[DUPLICATE]")
    assert "[SCENE_PRESENCE]" not in reason


def test_validate_bot_response_drifts_measured_voice_with_high_intensity_dialogue() -> None:
    dialogue = (
        "I need you to listen very carefully because none of this is optional any more "
        "and I will not repeat myself again under any circumstances here!!!"
    )
    is_valid, reason = validate_bot_response(
        content=dialogue,
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        state=CharacterState(
            name="Celina",
            voice_profile={"tone": "measured", "delivery": "calm and controlled"},
        ),
        move={
            "action": "steps forward with rigid posture",
            "dialogue": dialogue,
            "motivation": {"goal": "assert control", "tactic": "command"},
        },
        scene_state={},
    )
    assert is_valid is False
    assert reason.startswith("[CHARACTER_DRIFT]")
    assert "voice profile" in reason.lower()


def test_validate_bot_response_allows_intense_short_dialogue_without_voice_marker_family() -> None:
    """No recognized voice/speech marker family → voice drift check does not run."""
    dialogue = "LEAVE NOW!!!"
    is_valid, reason = validate_bot_response(
        content=dialogue,
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        state=CharacterState(
            name="Celina",
            voice_profile={},
            speech_fingerprint={},
        ),
        move={
            "action": "shouts",
            "dialogue": dialogue,
            "motivation": {"goal": "clear the room", "tactic": "shout"},
        },
        scene_state={},
    )
    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_drifts_guarded_reaction_with_rant_tactic() -> None:
    is_valid, reason = validate_bot_response(
        content="She lets the rant spill out in one breath.",
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        state=CharacterState(
            name="Celina",
            reaction_profile={"under_pressure": "guarded, controlled, narrows focus"},
        ),
        move={
            "action": "paces and vents loudly",
            "dialogue": "Fine. You want the truth spelled out in every ugly detail.",
            "motivation": {
                "goal": "vent frustration",
                "tactic": "rant at length without filtering",
                "emotional_driver": "bitter anger",
                "risk_level": "medium",
            },
        },
        scene_state={},
    )
    assert is_valid is False
    assert reason.startswith("[CHARACTER_DRIFT]")
    assert "reaction profile" in reason.lower()


def test_validate_bot_response_allows_soft_reaction_style_variation() -> None:
    is_valid, reason = validate_bot_response(
        content=(
            "turned away to give some privacy, but kept her posture alert and her gaze occasionally "
            "flicking back to monitor the progress, arms crossed over her chest."
        ),
        speaker="Celina",
        user_name="Alex",
        chat_history=[],
        state=CharacterState(
            name="Celina",
            reaction_profile={"under_pressure": "guarded, controlled, narrows focus"},
        ),
        move={
            "action": (
                "turned away to give some privacy, but kept her posture alert and her gaze occasionally "
                "flicking back to monitor the progress, arms crossed over her chest"
            ),
            "dialogue": "Good. Keep moving. The faster you're dry, the less likely I'll have to haul your ass to a doctor.",
            "motivation": {
                "goal": "ensure the clothing change is completed efficiently to prevent illness while maintaining a facade of irritation",
                "tactic": "offer gruff encouragement masked as a practical threat, using the turned posture to allow a sliver of privacy without dropping vigilance",
                "emotional_driver": "protective urgency channeled into controlled, efficient oversight",
                "risk_level": "low",
            },
        },
    )

    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_allows_in_scene_second_person_callback() -> None:
    is_valid, reason = validate_bot_response(
        content=(
            "held the pressure against the cut for another moment. It's shallow, like you said. "
            "But it's still oozing. You stay here. I'll get water and something clean to bind it."
        ),
        speaker="Celina",
        user_name="Traveler",
        chat_history=[],
        state=CharacterState(
            name="Celina",
            reaction_profile={"under_pressure": "guarded, controlled, narrows focus"},
        ),
        move={
            "action": "held the pressure against the cut for another moment and checked whether the bleeding had slowed",
            "dialogue": "It's shallow, like you said. But it's still oozing. You stay here. I'll get water and something clean to bind it.",
            "motivation": {
                "goal": "stabilize the immediate medical risk while reasserting control over the next steps of care",
                "tactic": "acknowledge the wound's condition and move to gather supplies",
                "emotional_driver": "protective urgency channeled into practical action",
                "risk_level": "low",
            },
        },
    )

    assert is_valid is True
    assert reason == ""


def test_validate_bot_response_rejects_direct_second_person_user_attribution() -> None:
    is_valid, reason = validate_bot_response(
        content='You said: "I never asked for this."',
        speaker="Celina",
        user_name="Traveler",
        chat_history=[],
    )

    assert is_valid is False
    assert reason.startswith("[USER_SPEECH]")


def test_validate_bot_response_allows_temporary_medical_cooperation_goal() -> None:
    is_valid, reason = validate_bot_response(
        content="It... burns. But I'm... breathing out. I'm still here.",
        speaker="Kizzie",
        user_name="Traveler",
        chat_history=[],
        state=CharacterState(
            name="Kizzie",
            core_goals=[
                "Find a true pack and an alpha she can trust without surrendering the freedom that defines her. "
                "Understand what it means to be kitsune, uncover the roots of her lost or fragmented past, and "
                "learn how her shifting and magic truly work. Preserve the ability to run, hunt, and live close "
                "to instinct rather than being caged, controlled, or turned into something tame."
            ],
        ),
        move={
            "action": (
                "jerked sharply as the antiseptic burned, then forced herself to exhale in a shaky, controlled "
                "stream without pulling away"
            ),
            "dialogue": "It... burns. But I'm... breathing out. I'm still here.",
            "motivation": {
                "goal": "endure the antiseptic burn without flinching or resisting, to maintain Celina's cooperation and prove her resilience",
                "tactic": "visibly control the pain response while verbally confirming compliance and presence",
                "emotional_driver": "instinctive pain and dread tempered by growing trust in Celina's protective efficiency",
                "risk_level": "low",
            },
        },
    )

    assert is_valid is True
    assert reason == ""


def test_reconcile_turn_selection_issues_removes_false_positive_direct_address_issue() -> (
    None
):
    issues = [
        "Selected actor ignored direct address preference for Celina",
        "Selected actor repeats the most recent spotlight when alternatives exist",
    ]

    reconciled = reconcile_turn_selection_issues(
        issues,
        {
            "should_flag_direct_address_miss": False,
            "direct_address_target": "Celina",
        },
        selected_actor="Ayame",
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )

    assert reconciled == [
        "Selected actor repeats the most recent spotlight when alternatives exist"
    ]


def test_reconcile_turn_selection_issues_adds_semantic_repeat_and_selection_support_issues() -> (
    None
):
    reconciled = reconcile_turn_selection_issues(
        [],
        {
            "supports_selected_actor": False,
            "should_flag_direct_address_miss": False,
            "should_flag_repeat_spotlight": True,
        },
        selected_actor="Ayame",
        participant_names=["Ayame", "Celina"],
    )

    assert (
        "Selected actor repeats the most recent spotlight when alternatives exist"
        in reconciled
    )
    assert (
        "Semantic turn_selection review did not support selected actor for current beat"
        in reconciled
    )


def test_reconcile_turn_selection_issues_no_addressee_mismatch_when_pick_matches_target() -> (
    None
):
    reconciled = reconcile_turn_selection_issues(
        [],
        {
            "supports_selected_actor": False,
            "should_flag_direct_address_miss": True,
            "direct_address_target": "Ayame",
            "should_flag_repeat_spotlight": False,
        },
        selected_actor="Ayame",
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )

    assert not any(
        "Addressee advisory mismatch (semantic):" in x for x in reconciled
    )
    assert reconciled == []


def test_reconcile_turn_selection_issues_adds_addressee_mismatch_when_pick_differs() -> None:
    reconciled = reconcile_turn_selection_issues(
        [],
        {
            "supports_selected_actor": False,
            "should_flag_direct_address_miss": True,
            "direct_address_target": "Celina",
            "should_flag_repeat_spotlight": False,
        },
        selected_actor="Ayame",
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )

    assert any(
        x.startswith("Addressee advisory mismatch (semantic):")
        and "Celina" in x
        and "Ayame" in x
        for x in reconciled
    )


def test_should_override_presence_rejection_uses_semantic_acceptance() -> None:
    assert (
        should_override_presence_rejection(
            "[SCENE_PRESENCE] Move contradicts must_remain presence for Celina",
            {"is_valid": True},
        )
        is True
    )
    assert (
        should_override_presence_rejection(
            "[CHARACTER_DRIFT] unrelated",
            {"is_valid": True},
        )
        is False
    )


def test_should_use_narrator_fallback_uses_semantic_recommendation() -> None:
    assert should_use_narrator_fallback({"should_use_fallback": True}) is True
    assert should_use_narrator_fallback({"should_use_fallback": False}) is False


def test_extract_json_object_text_handles_fenced_json_response() -> None:
    raw_response = '```json\n{\n  "is_valid": true,\n  "confidence": "high"\n}\n```'

    extracted = _extract_json_object_text(raw_response)

    assert json.loads(extracted) == {
        "is_valid": True,
        "confidence": "high",
    }
