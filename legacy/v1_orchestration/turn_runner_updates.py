import logging
from collections.abc import Callable
from typing import Any

from anti_regression_advisory import (
    arm_post_break_window,
    get_cached_anti_regression_advisory,
)
from progression_advisory import get_cached_progression_advisory
from beat_shift_state import (
    append_scene_snapshot_after_turn,
    consume_pending_beat_shift_if_active,
)
from scene_grounding import rebuild_scene_grounding_from_continuity
from turn_runner_audit import log_narrator_render_audit, write_turn_audit_artifacts
from tier_b_session_schedule import session_mutation_candidates_for_turn

logger = logging.getLogger(__name__)


def apply_successful_turn_updates(
    *,
    st_module: Any,
    next_actor: str,
    char_names: list[str],
    move: dict[str, Any],
    decision: dict[str, Any],
    rendered: str,
    narrator_raw: str,
    narrator_prompt: str,
    narrator_summary_block_audit: dict[str, Any],
    narrator_semantic_assessment: dict[str, Any] | None,
    narrator_output_audit_v1: dict[str, Any],
    narrator_validation_audit_v1: dict[str, Any],
    prose_dialogue_audit_v1: dict[str, Any],
    audit_v2_narrator: dict[str, Any] | None,
    round_number: int,
    turn_number: int,
    state_manager: Any,
    record_character_memories_fn,
    sync_orchestration_state_from_continuity_fn,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
    append_turn_to_orchestration_state_fn,
    orchestration_state: dict[str, Any],
    spotlight_history_limit: int,
    structured_move_history_limit: int,
    director_decision_history_limit: int,
    environment_history_limit: int,
    tension_history_limit: int,
    effective_user_trigger: str,
    skip_continuity_process_turn: bool = False,
    memory_display_name_for_key: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    if state_manager:
        state_manager.update_character_move(
            next_actor,
            move["action"],
            move.get("dialogue", ""),
            move.get("motivation", {}),
        )

    record_character_memories_fn(
        next_actor,
        move,
        decision,
        st_module=st_module,
        char_names=char_names,
        display_name_for_key=memory_display_name_for_key,
    )

    continuity_manager = st_module.session_state.get("continuity_manager")
    consequences: list[str] | None = None
    issue_updates: list[dict[str, Any]] | None = None
    presence_changes: list[dict[str, Any]] | None = None
    if continuity_manager:
        try:
            if not skip_continuity_process_turn:
                sched_cand = session_mutation_candidates_for_turn(
                    st_module, orchestration_turn=turn_number
                )
                proc_kw: dict[str, Any] = {}
                if sched_cand:
                    proc_kw["session_mutation_candidates"] = sched_cand
                continuity_manager.process_turn(
                    acting_character=next_actor,
                    move=move,
                    director_decision=decision,
                    other_characters=[name for name in char_names if name != next_actor],
                    **proc_kw,
                )
            sync_orchestration_state_from_continuity_fn()

            turn_index = int(getattr(continuity_manager, "turn_counter", 0) or 0)
            metadata_by_index = getattr(continuity_manager, "turn_metadata_by_index", {})
            turn_meta = metadata_by_index.get(turn_index, {}) if isinstance(metadata_by_index, dict) else {}
            candidate_consequences = (
                turn_meta.get("consequences", []) if isinstance(turn_meta, dict) else []
            )
            consequences = (
                [str(item) for item in candidate_consequences if str(item or "").strip()]
                if isinstance(candidate_consequences, list)
                else []
            )

            issue_updates = []
            for issue in getattr(continuity_manager, "issues", {}).values():
                last_turn_index = int(getattr(issue, "last_turn_index", 0) or 0)
                if last_turn_index != turn_index:
                    continue
                status = getattr(issue, "status", "")
                issue_updates.append(
                    {
                        "issue_id": str(getattr(issue, "issue_id", "") or ""),
                        "description": str(getattr(issue, "description", "") or ""),
                        "status": str(getattr(status, "value", status) or ""),
                        "status_reason": str(getattr(issue, "status_reason", "") or ""),
                        "participants": [
                            str(item)
                            for item in getattr(issue, "participants", [])
                            if str(item).strip()
                        ],
                    }
                )

            presence_changes = []
            if isinstance(consequences, list):
                if "exit" in consequences:
                    presence_changes.append({"character": next_actor, "change": "exit"})
                if "arrival" in consequences:
                    presence_changes.append({"character": next_actor, "change": "entry"})
        except Exception:
            logger.exception(
                "Post-turn continuity update failed for actor %s", next_actor
            )
            raise

        try:
            st_module.session_state["scene_grounding"] = (
                rebuild_scene_grounding_from_continuity(continuity_manager)
            )
        except Exception:
            logger.exception(
                "Scene grounding rebuild failed after actor %s turn", next_actor
            )
            raise

    log_narrator_render_audit(
        continuity_manager=continuity_manager,
        next_actor=next_actor,
        move=move,
        decision=decision,
        rendered=rendered,
        narrator_raw=narrator_raw,
        narrator_prompt=narrator_prompt,
        narrator_summary_block_audit=narrator_summary_block_audit,
        narrator_semantic_assessment=narrator_semantic_assessment,
        narrator_output_audit_v1=narrator_output_audit_v1,
        narrator_validation_audit_v1=narrator_validation_audit_v1,
        prose_dialogue_audit_v1=prose_dialogue_audit_v1,
        audit_v2=audit_v2_narrator,
        round_number=round_number,
        turn_number=turn_number,
        progression_advisory=get_cached_progression_advisory(orchestration_state),
        anti_regression_advisory=get_cached_anti_regression_advisory(
            orchestration_state
        ),
        scene_grounding_state=st_module.session_state.get("scene_grounding"),
        effective_user_trigger=effective_user_trigger,
        is_audit_enabled_fn=is_audit_enabled_fn,
        get_audit_logger_fn=get_audit_logger_fn,
        get_audit_context_fn=get_audit_context_fn,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
        get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
    )
    write_turn_audit_artifacts(
        continuity_manager=continuity_manager,
        next_actor=next_actor,
        move=move,
        decision=decision,
        rendered=rendered,
        round_number=round_number,
        turn_number=turn_number,
        is_audit_enabled_fn=is_audit_enabled_fn,
        get_audit_logger_fn=get_audit_logger_fn,
        get_audit_context_fn=get_audit_context_fn,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
        get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
    )

    orchestration_state = append_turn_to_orchestration_state_fn(
        orchestration_state=orchestration_state,
        next_actor=next_actor,
        move=move,
        decision=decision,
        consequences=consequences,
        issue_updates=issue_updates,
        presence_changes=presence_changes,
        spotlight_history_limit=spotlight_history_limit,
        structured_move_history_limit=structured_move_history_limit,
        director_decision_history_limit=director_decision_history_limit,
        environment_history_limit=environment_history_limit,
        tension_history_limit=tension_history_limit,
    )
    if consume_pending_beat_shift_if_active(orchestration_state):
        arm_post_break_window(orchestration_state)
    append_scene_snapshot_after_turn(orchestration_state)
    st_module.session_state["team_state"] = orchestration_state
    return orchestration_state
