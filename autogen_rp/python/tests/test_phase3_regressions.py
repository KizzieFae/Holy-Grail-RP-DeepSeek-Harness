import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app import (
    PROMPT_DIALOGUE_HISTORY_LIMIT,
    build_memory_fact_summary,
    build_recent_dialogue_history,
)
from audit_logger import AuditLogger
from character_state import CharacterState
from continuity_manager import ContinuityManager
from response_validation import detect_character_drift, validate_turn_selection_decision
from session_manager import SessionManager


def _build_move(idx: int, goal: str = "protect the forge") -> dict:
    return {
        "action": f"holds position {idx}",
        "dialogue": f"Turn {idx} holds the line.",
        "motivation": {
            "goal": goal,
            "tactic": "hold steady",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }


def _build_decision(next_actor: str, tension_shift: str = "steady") -> dict:
    return {
        "next_actor": next_actor,
        "environment_event": "",
        "tension_shift": tension_shift,
        "reason": "Deterministic test decision.",
    }


def test_phase3_character_drift_detection_rejects_conflicting_goal() -> None:
    state = CharacterState(
        name="Ayame",
        long_term_goal="Protect the forge",
        medium_term_goal="Expose the saboteur",
        core_goals=["Protect the forge", "Expose the saboteur"],
        voice_profile={"tone": "cool", "cadence": "measured"},
    )

    has_drift, reason = detect_character_drift(
        content="I burn the forge to ash.",
        speaker="Ayame",
        state=state,
        move={
            "dialogue": "I burn the forge to ash.",
            "motivation": {
                "goal": "destroy the forge",
                "tactic": "lash out",
                "emotional_driver": "rage",
                "risk_level": "high",
            },
        },
    )

    assert has_drift is True
    assert "stable goal anchor" in reason


def test_phase3_character_drift_skips_offsite_anchor_when_scene_context_differs() -> None:
    state = CharacterState(
        name="Harley",
        core_goals=["Protect the Arkham ward and keep the newcomers unstable"],
    )
    has_drift, reason = detect_character_drift(
        content="leans in with a grin",
        speaker="Harley",
        state=state,
        move={
            "action": "leans in with a grin",
            "dialogue": "",
            "motivation": {
                "goal": "abandon the Arkham ward entirely and burn the intake desk",
                "tactic": "provoke chaos",
                "emotional_driver": "glee",
                "risk_level": "high",
            },
        },
        scene_state={
            "location": "SCUC Dorm 303",
            "environment_description": "A standard double dorm room on campus.",
        },
    )
    assert has_drift is False
    assert reason == ""


def test_phase3_character_drift_still_binds_when_scene_echoes_offsite_marker() -> None:
    state = CharacterState(
        name="Harley",
        core_goals=["Protect the Arkham ward at all costs"],
    )
    has_drift, reason = detect_character_drift(
        content="smirks",
        speaker="Harley",
        state=state,
        move={
            "action": "smirks",
            "dialogue": "",
            "motivation": {
                "goal": "destroy the Arkham ward",
                "tactic": "lash out",
                "emotional_driver": "rage",
                "risk_level": "high",
            },
        },
        scene_state={
            "location": "SCUC Dorm 303",
            "environment_description": "Arkham transfer paperwork stacked on the desk.",
        },
    )
    assert has_drift is True
    assert "stable goal anchor" in reason


def test_phase3_character_drift_detection_allows_temporary_stabilization_goal() -> None:
    state = CharacterState(
        name="Kizzie",
        core_goals=[
            "Find a true pack and an alpha she can trust without surrendering the freedom that defines her. "
            "Understand what it means to be kitsune, uncover the roots of her lost or fragmented past, and "
            "learn how her shifting and magic truly work. Preserve the ability to run, hunt, and live close "
            "to instinct rather than being caged, controlled, or turned into something tame."
        ],
    )

    has_drift, reason = detect_character_drift(
        content="It... burns. But I'm... breathing out. I'm still here.",
        speaker="Kizzie",
        state=state,
        move={
            "dialogue": "It... burns. But I'm... breathing out. I'm still here.",
            "motivation": {
                "goal": "endure the antiseptic burn without flinching or resisting, to maintain Celina's cooperation and prove her resilience",
                "tactic": "visibly control the pain response while verbally confirming compliance and presence",
                "emotional_driver": "instinctive pain tempered by growing trust in Celina's protective efficiency",
                "risk_level": "low",
            },
        },
    )

    assert has_drift is False
    assert reason == ""


def test_phase3_character_drift_detection_allows_voice_intensity_variation_as_soft_signal() -> (
    None
):
    state = CharacterState(
        name="Celina",
        long_term_goal="Keep the room calm",
        voice_profile={"tone": "cool", "cadence": "measured"},
    )

    has_drift, reason = detect_character_drift(
        content='"LEAVE NOW!!!"',
        speaker="Celina",
        state=state,
        move={
            "dialogue": "LEAVE NOW!!!",
            "motivation": {
                "goal": "keep control",
                "tactic": "shout",
                "emotional_driver": "anger",
                "risk_level": "high",
            },
        },
    )

    assert has_drift is False
    assert reason == ""


def test_phase3_character_drift_detects_formal_speech_fingerprint_diction_conflict() -> None:
    state = CharacterState(
        name="Mira",
        speech_fingerprint={"register": "formal", "signature": "spare, clipped"},
    )

    has_drift, reason = detect_character_drift(
        content='"yeah, gonna lay everything out because honestly I wanna talk this through for a while"',
        speaker="Mira",
        state=state,
        move={
            "dialogue": "yeah, gonna lay everything out because honestly I wanna talk this through for a while",
            "motivation": {
                "goal": "explain the situation",
                "tactic": "ramble at length",
                "emotional_driver": "anxiety",
                "risk_level": "medium",
            },
        },
    )

    assert has_drift is True
    assert "speech fingerprint" in reason.lower()


def test_phase3_character_drift_detects_reaction_profile_tactic_conflict() -> None:
    state = CharacterState(
        name="Ayame",
        reaction_profile={"under_pressure": "guarded, controlled, narrows focus"},
    )

    has_drift, reason = detect_character_drift(
        content="I blurt everything out at once.",
        speaker="Ayame",
        state=state,
        move={
            "dialogue": "I blurt everything out at once.",
            "motivation": {
                "goal": "end the silence",
                "tactic": "blurt everything",
                "emotional_driver": "panic",
                "risk_level": "high",
            },
        },
    )

    assert has_drift is True
    assert "reaction profile" in reason.lower()


def test_phase3_turn_selection_validation_only_checks_structural_membership() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Outsider",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Testing invalid participant failure.",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Celina", "Mira"],
        trigger_text="Ayame turns to Celina and asks why she came back.",
        spotlight_history=["Ayame", "Mira"],
    )

    assert issues == ["Selected actor is not a participant: Outsider"]


def test_phase3_turn_selection_validation_rejects_unavailable_actor() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Testing unavailable actor failure.",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Mira"],
        trigger_text="The room goes still.",
        spotlight_history=["Ayame", "Celina"],
    )

    assert issues == ["Selected actor is not in available_next_actors: Celina"]


def test_phase5_turn_selection_end_round_empty_actor_valid() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "",
            "end_round": True,
            "environment_event": "",
            "tension_shift": "",
            "reason": "Scene beat complete.",
        },
        participant_names=["Ayame", "Celina"],
        available_actors=["Ayame"],
        trigger_text="",
        spotlight_history=[],
    )
    assert issues == []


def test_phase5_turn_selection_flags_offstage_actor() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "test",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Ayame", "Celina", "Mira"],
        trigger_text="",
        spotlight_history=[],
        offstage_characters=["Celina"],
    )
    assert issues == ["Selected actor is marked offstage: Celina"]


def test_phase5_turn_selection_preemption_forced_speaker_mismatch() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Mira",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Ayame", "Celina", "Mira"],
        trigger_text="",
        spotlight_history=[],
        pending_forced_speaker="Ayame",
        forced_speaker_consumed=False,
    )
    assert issues == [
        "next_actor should match pending forced speaker (Ayame), got Mira",
    ]


def test_phase5_turn_selection_preemption_continuation_mismatch() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Mira",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Ayame", "Celina", "Mira"],
        trigger_text="",
        spotlight_history=[],
        continuation_override_actor="Celina",
    )
    assert issues == [
        "next_actor should match continuation override (Celina), got Mira",
    ]


def test_phase5_turn_selection_skips_preemption_when_source_fallback() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Mira",
            "source": "fallback",
            "environment_event": "",
            "tension_shift": "",
            "reason": "Fallback selection after director parse failure: ...",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Ayame", "Celina", "Mira"],
        trigger_text="",
        spotlight_history=[],
        pending_forced_speaker="Ayame",
        forced_speaker_consumed=False,
        continuation_override_actor="Celina",
    )
    assert issues == []


def test_phase5_turn_selection_skips_preemption_when_is_fallback() -> None:
    issues = validate_turn_selection_decision(
        decision={
            "next_actor": "Mira",
            "is_fallback": True,
            "environment_event": "",
            "tension_shift": "",
            "reason": "recovery",
        },
        participant_names=["Ayame", "Celina", "Mira"],
        available_actors=["Ayame", "Celina", "Mira"],
        trigger_text="",
        spotlight_history=[],
        pending_forced_speaker="Ayame",
        forced_speaker_consumed=False,
        continuation_override_actor="Celina",
    )
    assert issues == []


def test_phase3_bounded_dialogue_history_window() -> None:
    chat_history = [
        {"role": "system", "speaker": "system", "content": "ignore"},
        *[
            {
                "role": "assistant",
                "speaker": f"Char{idx}",
                "content": f"line {idx}",
            }
            for idx in range(PROMPT_DIALOGUE_HISTORY_LIMIT + 3)
        ],
    ]

    history = build_recent_dialogue_history(chat_history)

    assert len(history) == PROMPT_DIALOGUE_HISTORY_LIMIT
    assert history[0]["speaker"] == "Char3"
    assert all(item["role"] != "system" for item in history)


def test_phase3_memory_fact_summary_uses_compact_facts_not_raw_dialogue() -> None:
    summary = build_memory_fact_summary(
        "Ayame",
        {
            "action": "stepped between Celina and the forge",
            "dialogue": "No one touches it again.",
            "motivation": {
                "goal": "protect the forge",
                "tactic": "block access",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
        },
    )

    assert "Ayame stepped between Celina and the forge" in summary
    assert "spoke aloud" in summary
    assert "while pursuing: protect the forge" in summary
    assert "No one touches it again." not in summary


def test_phase3_one_on_one_scene_regression() -> None:
    manager = ContinuityManager(summary_interval=12, recent_event_window=8)
    manager.initialize_scene(
        location="Workshop",
        opening_description="Two rivals face each other.",
        present_characters=["Ayame", "Celina"],
    )

    manager.process_turn(
        acting_character="Ayame",
        move=_build_move(1),
        director_decision=_build_decision("Celina", tension_shift="escalate"),
        other_characters=["Celina"],
    )
    manager.process_turn(
        acting_character="Celina",
        move=_build_move(2, goal="keep the forge safe"),
        director_decision=_build_decision("Ayame", tension_shift="steady"),
        other_characters=["Ayame"],
    )

    snapshot = manager.get_snapshot()
    assert snapshot.scene_state.present_characters == ["Ayame", "Celina"]
    assert len(snapshot.recent_public_events) >= 2


def test_phase3_three_character_scene_regression() -> None:
    manager = ContinuityManager(summary_interval=12, recent_event_window=8)
    manager.initialize_scene(
        location="Harbor",
        opening_description="Three figures argue in the rain.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    for idx, actor in enumerate(["Ayame", "Celina", "Mira"], start=1):
        others = [name for name in ["Ayame", "Celina", "Mira"] if name != actor]
        manager.process_turn(
            acting_character=actor,
            move=_build_move(idx),
            director_decision=_build_decision(others[0], tension_shift="steady"),
            other_characters=others,
        )

    context = manager.get_character_context("Mira")
    assert context["scene_state"].present_characters == ["Ayame", "Celina", "Mira"]
    assert len(context["recent_events"]) >= 1


def test_phase3_long_session_regression_generates_summary_blocks() -> None:
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Archive",
        opening_description="A long debate unfolds among the stacks.",
        present_characters=["Ayame", "Celina"],
    )

    for idx in range(1, 9):
        actor = "Ayame" if idx % 2 else "Celina"
        other = ["Celina"] if actor == "Ayame" else ["Ayame"]
        manager.process_turn(
            acting_character=actor,
            move=_build_move(idx),
            director_decision=_build_decision(other[0]),
            other_characters=other,
        )

    assert manager.turn_counter == 8
    assert len(manager.summary_blocks) == 2
    assert len(manager.get_snapshot().recent_public_events) == 2


def test_phase3_reload_after_save_regression_preserves_continuity_state(
    tmp_path: Path,
) -> None:
    session_manager = SessionManager(tmp_path)
    continuity_manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    continuity_manager.initialize_scene(
        location="Workshop",
        opening_description="The forge glows in the dark.",
        present_characters=["Ayame", "Celina"],
    )

    for idx in range(1, 5):
        actor = "Ayame" if idx % 2 else "Celina"
        other = ["Celina"] if actor == "Ayame" else ["Ayame"]
        continuity_manager.process_turn(
            acting_character=actor,
            move=_build_move(idx),
            director_decision=_build_decision(other[0]),
            other_characters=other,
        )

    session_manager.save_session(
        session_id="reload_case",
        team_state={"scene": "state"},
        characters=["Ayame", "Celina"],
        metadata={
            "continuity_state": continuity_manager.to_dict(),
            "scene_status": "closed",
        },
        chat_history=[{"role": "assistant", "speaker": "Ayame", "content": "line"}],
    )

    loaded = session_manager.load_session("reload_case")
    restored = ContinuityManager.from_dict(loaded["metadata"]["continuity_state"])

    assert restored.scene_state is not None
    assert restored.scene_state.location == "Workshop"
    assert restored.turn_counter == continuity_manager.turn_counter
    assert len(restored.summary_blocks) == len(continuity_manager.summary_blocks)


def test_phase3_audit_summary_report_tracks_issue_categories(tmp_path: Path) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina"],
        opening_description="A tense workshop confrontation.",
        user_name="Alex",
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Validation: Selected actor ignored direct address preference for Celina",
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame held the line.",
        character_move={
            "action": "held the line",
            "dialogue": "",
            "motivation": {"goal": "protect the forge"},
        },
        director_decision={
            "reason": "Validation: Selected actor ignored direct address preference for Celina",
            "environment_event": "",
            "tension_shift": "steady",
        },
    )

    entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Director",
        bot_type="director",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response="duplicate duplicate",
        parsed_output={
            "reason": "Validation: Selected actor ignored direct address preference for Celina"
        },
        metadata={
            "parse_error": "[DUPLICATE] Repeated content structure",
            "turn_selection_issues": [
                "Selected actor ignored direct address preference for Celina"
            ],
        },
    )
    logger.log_bot_interaction(entry)

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert report["issue_categories"]["turn_selection_mistakes"]["count"] >= 1
    assert report["issue_categories"]["repetitive_phrasing"]["count"] >= 1
    assert report["heuristic_issue_categories"]["turn_selection_mistakes"]["count"] >= 1
    assert report["heuristic_issue_categories"]["repetitive_phrasing"]["count"] >= 1
    assert report["regression_checks"]["turn_selection_mistakes"] is False
    assert report["regression_checks"]["repetitive_phrasing"] is False


def test_phase3_audit_summary_report_keeps_reasoning_text_out_of_confirmed_selector_failures(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina"],
        opening_description="A tense workshop confrontation.",
        user_name="Alex",
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Celina was directly addressed, but spotlight remained balanced.",
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame held the line.",
        character_move={
            "action": "held the line",
            "dialogue": "",
            "motivation": {"goal": "protect the forge"},
        },
        director_decision={
            "reason": "Celina was directly addressed, but spotlight remained balanced.",
            "environment_event": "",
            "tension_shift": "steady",
        },
    )

    entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Director",
        bot_type="director",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response='{"next_actor": "Ayame", "reason": "Celina was directly addressed, but spotlight remained balanced."}',
        parsed_output={
            "reason": "Celina was directly addressed, but spotlight remained balanced."
        },
        metadata={
            "parse_error": "",
            "turn_selection_issues": [],
        },
    )
    logger.log_bot_interaction(entry)

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert report["issue_categories"]["turn_selection_mistakes"]["count"] == 0
    assert report["heuristic_issue_categories"]["turn_selection_mistakes"]["count"] >= 1
    assert report["regression_checks"]["turn_selection_mistakes"] is True


def test_phase3_audit_summary_report_tracks_summary_block_visibility(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina"],
        opening_description="A tense workshop confrontation.",
        user_name="Alex",
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Deterministic test decision.",
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame held the line.",
        character_move={
            "action": "held the line",
            "dialogue": "Stand down.",
            "motivation": {"goal": "protect the forge"},
        },
        director_decision={
            "reason": "Deterministic test decision.",
            "environment_event": "",
            "tension_shift": "steady",
        },
    )

    character_entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Ayame",
        bot_type="character",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response='{"action": "held the line"}',
        parsed_output={"action": "held the line", "dialogue": "Stand down."},
        metadata={
            "summary_blocks": {
                "summary_generation_eligible": True,
                "summary_blocks_generated_total": 2,
                "generated_summary_block_ids": ["summary_1_12", "summary_13_24"],
                "summary_blocks_available_count": 2,
                "available_summary_block_ids": ["summary_1_12", "summary_13_24"],
                "summary_blocks_selected_count": 1,
                "selected_summary_block_ids": ["summary_13_24"],
                "excluded_summary_block_ids": ["summary_1_12"],
                "selection_reason": "deterministic retrieval for character prompt",
                "skipped_reason": "",
                "fallback_used": False,
                "summary_limit": 3,
            }
        },
    )
    logger.log_bot_interaction(character_entry)

    narrator_entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Narrator",
        bot_type="narrator",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response="Ayame held the line.",
        parsed_output={"rendered": "Ayame held the line."},
        metadata={
            "summary_blocks": {
                "summary_generation_eligible": True,
                "summary_blocks_generated_total": 2,
                "generated_summary_block_ids": ["summary_1_12", "summary_13_24"],
                "summary_blocks_available_count": 0,
                "available_summary_block_ids": [],
                "summary_blocks_selected_count": 1,
                "selected_summary_block_ids": ["summary_1_12"],
                "excluded_summary_block_ids": [],
                "selection_reason": "fallback to recent summary blocks after filtered retrieval returned none",
                "skipped_reason": "",
                "fallback_used": True,
                "summary_limit": 2,
            }
        },
    )
    logger.log_bot_interaction(narrator_entry)

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    visibility = report["summary_block_visibility"]
    assert visibility["prompt_evaluations"] == 2
    assert visibility["prompt_evaluations_generation_eligible"] == 2
    assert visibility["summary_blocks_generated_total_max"] == 2
    assert visibility["summary_blocks_used_total"] == 2
    assert visibility["prompt_evaluations_with_summary_available"] == 1
    assert visibility["prompt_evaluations_with_summary_injection"] == 2
    assert visibility["first_prompt_with_summary_block"] == {
        "round_number": 1,
        "turn_number": 1,
        "bot_name": "Ayame",
    }
    assert visibility["prompt_evaluations_with_fallback_selection"] == [
        {"round_number": 1, "turn_number": 1, "bot_name": "Narrator"}
    ]

    round_usage = report["round_summaries"][0]["summary_block_usage"]
    assert round_usage["prompt_evaluations"] == 2
    assert round_usage["generated_total_max"] == 2
    assert round_usage["available_count_max"] == 2
    assert round_usage["selected_count_total"] == 2
    assert round_usage["selected_summary_block_ids"] == [
        "summary_13_24",
        "summary_1_12",
    ]
    assert round_usage["fallback_used"] is True
    assert len(round_usage["prompt_details"]) == 2


def test_phase3_audit_summary_report_tracks_continuity_state_change_metrics(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina"],
        opening_description="A negotiation reaches a hard refusal.",
        user_name="Alex",
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Ayame rejects the offer directly.",
        continuity_event_type="decision",
        state_change_count=1,
        issue_update_count=1,
        presence_change_count=0,
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame refused the offer and held her ground.",
        character_move={
            "action": "holds her ground",
            "dialogue": "I refuse.",
            "motivation": {"goal": "reject the offer"},
        },
        director_decision={
            "reason": "Ayame rejects the offer directly.",
            "environment_event": "",
            "tension_shift": "steady",
        },
        continuity_event={
            "event_type": "decision",
            "summary": "Ayame refused the current demand, request, or proposed course of action.",
            "significance": "pivotal",
            "related_issue_ids": ["issue_1"],
            "state_changes": [
                "Ayame refused the current demand, request, or proposed course of action."
            ],
            "actionable_implications": [
                "The cast must respond to the refusal or choose a different course."
            ],
        },
        scene_state_after={
            "recent_delta": "Ayame refused the current demand, request, or proposed course of action.",
            "phase": "rising",
            "current_tension_level": "moderate",
            "active_issue_ids": ["issue_1"],
            "present_characters": ["Ayame", "Celina"],
            "absent_but_relevant": [],
        },
        issue_updates=[
            {
                "issue_id": "issue_1",
                "description": "Resolve the offer standoff",
                "status": "escalating",
                "status_reason": "Escalation signal matched: refuse",
                "participants": ["Ayame", "Celina"],
            }
        ],
        presence_changes=[],
    )

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    round_summary = report["round_summaries"][0]
    assert round_summary["continuity_event_types"] == ["decision"]
    assert round_summary["state_change_count"] == 1
    assert round_summary["issue_update_count"] == 1
    assert round_summary["turns_with_state_change"] == 1
    assert round_summary["turns_with_issue_update"] == 1
    assert round_summary["turns_without_material_change"] == 0
    assert report["continuity_overview"]["turns_with_state_change"] == 1
    assert report["continuity_overview"]["issue_update_count"] == 1
    assert report["continuity_overview"]["decision_or_revelation_turns"] == 1


def test_phase3_audit_scene_template_metadata_flows_through_outputs(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    scene_template_kwargs = {
        "scene_template_id": "household_entry_evaluation",
        "scene_premise": "A host evaluates a newcomer while a guard remains present.",
        "role_assignments": {
            "Ayame": "host",
            "Celina": "applicant",
            "Mira": "guard",
        },
        "character_presence_constraints": {
            "Ayame": "must_remain",
            "Celina": "must_remain",
            "Mira": "must_remain",
        },
        "character_authority_labels": {
            "Ayame": "high",
            "Celina": "low",
            "Mira": "medium",
        },
    }

    manifest_path = logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina", "Mira"],
        opening_description="A guarded evaluation begins in the household foyer.",
        user_name="Alex",
        **scene_template_kwargs,
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="The host should anchor the first exchange.",
        acting_role="host",
        presence_constraint="must_remain",
        authority_label="high",
    )
    narrative_path = logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame greeted the newcomer and kept the guard close.",
        character_move={
            "action": "greeted the newcomer",
            "dialogue": "Stand where I can see you.",
            "motivation": {"goal": "control the evaluation"},
        },
        director_decision={
            "reason": "The host should anchor the first exchange.",
            "environment_event": "The guard shuts the door.",
            "tension_shift": "steady",
        },
        acting_role="host",
        presence_constraint="must_remain",
        authority_label="high",
        **scene_template_kwargs,
    )

    entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Director",
        bot_type="director",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response='{"next_actor": "Ayame"}',
        parsed_output={"next_actor": "Ayame"},
        context_snapshot={"participant_names": ["Ayame", "Celina", "Mira"]},
        **scene_template_kwargs,
    )

    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with open(narrative_path, "r", encoding="utf-8") as handle:
        narrative = json.load(handle)

    assert manifest["scene_template"]["template_id"] == "household_entry_evaluation"
    assert manifest["scene_template"]["role_assignments"]["Ayame"] == "host"
    assert (
        narrative["scene_template"]["character_presence_constraints"]["Mira"]
        == "must_remain"
    )
    assert narrative["turns"][0]["character_role"] == "host"
    assert narrative["turns"][0]["character_presence_constraint"] == "must_remain"
    assert narrative["turns"][0]["character_authority_label"] == "high"
    assert (
        entry.context_snapshot["scene_template"]["template_id"]
        == "household_entry_evaluation"
    )


def test_phase3_audit_summary_report_includes_role_coverage_for_scene_templates(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    scene_template_kwargs = {
        "scene_template_id": "household_entry_evaluation",
        "scene_premise": "A host evaluates a newcomer while a guard remains present.",
        "role_assignments": {
            "Ayame": "host",
            "Celina": "applicant",
            "Mira": "guard",
        },
        "character_presence_constraints": {
            "Ayame": "must_remain",
            "Celina": "must_remain",
            "Mira": "must_remain",
        },
        "character_authority_labels": {
            "Ayame": "high",
            "Celina": "low",
            "Mira": "medium",
        },
    }

    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina", "Mira"],
        opening_description="A guarded evaluation begins in the household foyer.",
        user_name="Alex",
        **scene_template_kwargs,
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="The host should anchor the first exchange.",
        acting_role="host",
        presence_constraint="must_remain",
        authority_label="high",
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame greeted the newcomer and kept the guard close.",
        character_move={
            "action": "greeted the newcomer",
            "dialogue": "Stand where I can see you.",
            "motivation": {"goal": "control the evaluation"},
        },
        director_decision={
            "reason": "The host should anchor the first exchange.",
            "environment_event": "The guard shuts the door.",
            "tension_shift": "steady",
        },
        acting_role="host",
        presence_constraint="must_remain",
        authority_label="high",
        **scene_template_kwargs,
    )

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    role_coverage = {
        item["character"]: item for item in report["scene_template"]["role_coverage"]
    }
    assert report["scene_template"]["template_id"] == "household_entry_evaluation"
    assert role_coverage["Ayame"]["role"] == "host"
    assert role_coverage["Ayame"]["turns"] == 1
    assert role_coverage["Mira"]["presence_constraint"] == "must_remain"
    assert role_coverage["Mira"]["turns"] == 0
    assert (
        "Mira" in report["scene_template"]["must_remain"]["characters_with_zero_turns"]
    )
    assert report["round_summaries"][0]["turn_roles"][0] == {
        "turn_number": 1,
        "character": "Ayame",
        "role": "host",
        "presence_constraint": "must_remain",
        "authority_label": "high",
    }


def test_phase3_audit_artifact_filenames_and_core_json_shapes_stay_stable(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))

    manifest_path = logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Celina"],
        opening_description="A tense workshop confrontation.",
        user_name="Alex",
    )
    index_path = logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Ayame was directly challenged and must respond.",
    )
    narrative_path = logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame held the line.",
        character_move={
            "action": "held the line",
            "dialogue": "Stand down.",
            "motivation": {"goal": "protect the forge"},
        },
        director_decision={
            "reason": "Ayame was directly challenged and must respond.",
            "environment_event": "The forge pops once.",
            "tension_shift": "steady",
        },
    )
    entry = logger.create_entry(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Director",
        bot_type="director",
        input_messages=[{"role": "system", "content": "prompt"}],
        raw_response='{"next_actor": "Ayame"}',
        parsed_output={"next_actor": "Ayame"},
    )
    full_path, light_path = logger.log_bot_interaction(entry)
    report_path = logger.write_summary_report("Ayame", 1)

    assert Path(manifest_path).parent.name == "session_001"
    assert Path(manifest_path).name == "_manifest.json"
    assert Path(index_path).name == "_round_index.json"
    assert Path(narrative_path).name == "_narrative.json"
    assert Path(report_path).name == "_audit_summary.json"
    assert Path(full_path).parent.name == "round_001"
    assert Path(light_path).parent.name == "round_001"
    assert Path(full_path).name == "ayame_session001_round001_turn01_director_full.json"
    assert (
        Path(light_path).name == "ayame_session001_round001_turn01_director_light.json"
    )

    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with open(index_path, "r", encoding="utf-8") as handle:
        index = json.load(handle)
    with open(narrative_path, "r", encoding="utf-8") as handle:
        narrative = json.load(handle)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert set(manifest) >= {
        "session_owner",
        "session_number",
        "timestamp",
        "cast",
        "user_name",
        "opening_description",
        "total_characters",
        "scene_template",
    }
    assert set(index) == {"rounds"}
    assert set(index["rounds"][0]["turns"][0]) >= {
        "turn_number",
        "acting_character",
        "director_reason",
        "acting_role",
        "presence_constraint",
        "authority_label",
        "continuity_event_type",
        "state_change_count",
        "issue_update_count",
        "presence_change_count",
        "timestamp",
    }
    assert set(narrative) >= {
        "session_owner",
        "session_number",
        "created_at",
        "complete_narrative",
        "turns",
        "character_stats",
        "scene_template",
        "last_updated",
        "total_rounds",
    }
    assert set(report) >= {
        "session_owner",
        "session_number",
        "generated_at",
        "manifest",
        "scene_template",
        "overview",
        "continuity_overview",
        "spotlight",
        "recent_rounds",
        "round_summaries",
        "summary_block_visibility",
        "summary_block_quality",
        "anomalies",
        "issue_categories",
        "heuristic_issue_categories",
        "regression_checks",
    }
