from typing import Any

from audit_instrumentation import log_audit_exception


def split_character_prompt_audit_for_metadata(
    prompt_layer_audit: dict[str, Any],
) -> tuple[dict[str, Any], bool, str]:
    """Split summary-block audit dict from binding observability (prompt layer only).

    ``prompt_layer_audit`` is the dict returned with the character prompt from
    ``app_turn_prompting.build_character_turn_prompt`` (summary fields + binding keys).
    """
    merged = dict(prompt_layer_audit)
    bc_section = str(merged.pop("scene_binding_constraints_section", "") or "")
    has_raw = merged.pop("has_binding_constraints", None)
    if isinstance(has_raw, bool):
        has_bc = has_raw
    else:
        has_bc = bool(bc_section.strip())
    return merged, has_bc, bc_section


def promote_character_binding_fields_for_audit_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Hoist binding fields from ``metadata.summary_blocks`` to metadata top level (failure audits)."""
    base = dict(metadata or {})
    sb = base.get("summary_blocks")
    if not isinstance(sb, dict):
        return base
    cleaned, has_bc, bc_section = split_character_prompt_audit_for_metadata(dict(sb))
    base["summary_blocks"] = cleaned
    base["has_binding_constraints"] = has_bc
    base["scene_binding_constraints_section"] = bc_section
    return base


def _merge_character_audit_metadata(
    *,
    base: dict[str, Any],
    progression_advisory: dict[str, Any] | None,
    anti_regression_advisory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(base)
    if progression_advisory:
        out["progression_advisory"] = {
            "stall_score": progression_advisory.get("stall_score"),
            "progression_pressure": progression_advisory.get("progression_pressure"),
            "recommended_channels": progression_advisory.get("recommended_channels"),
            "note": progression_advisory.get("note"),
            "stall_components": progression_advisory.get("stall_components"),
        }
    if anti_regression_advisory:
        out["anti_regression_advisory"] = {
            "active": anti_regression_advisory.get("active"),
            "ping_pong_detected": anti_regression_advisory.get("ping_pong_detected"),
            "post_break_window_active": anti_regression_advisory.get(
                "post_break_window_active"
            ),
            "low_player_agency": anti_regression_advisory.get("low_player_agency"),
            "ping_pong_actors": anti_regression_advisory.get("ping_pong_actors"),
            "ticks_after_decrement": anti_regression_advisory.get(
                "ticks_after_decrement"
            ),
        }
    return out


def _get_turn_continuity_payload(*, continuity_manager: Any, next_actor: str) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
    """Extract continuity payload including consequences for audit logging."""
    if continuity_manager is None or continuity_manager.scene_state is None:
        return {}, {}, [], [], []

    current_turn_index = int(getattr(continuity_manager, "turn_counter", 0) or 0)
    continuity_event: dict[str, Any] = {}
    consequences: list[str] = []

    # Read consequences directly from turn-level metadata (not from serialized PublicEvent)
    turn_metadata = getattr(continuity_manager, "turn_metadata_by_index", {})
    turn_consequences = turn_metadata.get(current_turn_index, {})
    if turn_consequences:
        consequences = turn_consequences.get("consequences", [])

    public_events = list(getattr(continuity_manager, "public_events", []) or [])
    if public_events:
        event = public_events[-1]
        event_turn_index = int(getattr(event, "turn_index", 0) or 0)
        participants = [
            str(item)
            for item in getattr(event, "participants", [])
            if str(item).strip()
        ]
        if event_turn_index == current_turn_index and next_actor in participants:
            continuity_event = event.to_dict() if hasattr(event, "to_dict") else {}
            # Also enrich continuity_event with consequences from turn metadata
            if consequences and "consequences" not in continuity_event:
                continuity_event["consequences"] = consequences

    scene_state_after = (
        continuity_manager.scene_state.to_dict()
        if hasattr(continuity_manager.scene_state, "to_dict")
        else {}
    )

    issue_updates: list[dict[str, Any]] = []
    for issue in getattr(continuity_manager, "issues", {}).values():
        last_turn_index = int(getattr(issue, "last_turn_index", 0) or 0)
        if last_turn_index != current_turn_index:
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

    presence_changes: list[dict[str, Any]] = []
    for state_change in continuity_event.get("state_changes", []):
        summary = str(state_change or "").strip()
        lowered = summary.lower()
        if not summary:
            continue
        if "left the immediate scene" in lowered:
            presence_changes.append(
                {"character": next_actor, "change": "exit", "summary": summary}
            )
        elif "entered the immediate scene" in lowered or "arrived" in lowered:
            presence_changes.append(
                {"character": next_actor, "change": "entry", "summary": summary}
            )

    return (
        continuity_event,
        scene_state_after,
        issue_updates,
        presence_changes,
        consequences,
    )


def log_character_turn_audit(
    *,
    next_actor: str,
    move: dict[str, Any],
    task_prompt: str,
    char_raw_response: str,
    decision: dict[str, Any],
    char_names: list[str],
    continuity_manager: Any,
    round_number: int,
    turn_number: int,
    character_summary_block_audit: dict[str, Any],
    turn_execution_metadata: dict[str, Any] | None = None,
    progression_advisory: dict[str, Any] | None = None,
    anti_regression_advisory: dict[str, Any] | None = None,
    character_audit_v1: dict[str, Any] | None = None,
    audit_v2: dict[str, Any] | None = None,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
) -> None:
    if not is_audit_enabled_fn():
        return

    (
        continuity_event,
        scene_state_after,
        issue_updates,
        presence_changes,
        consequences,
    ) = _get_turn_continuity_payload(
        continuity_manager=continuity_manager,
        next_actor=next_actor,
    )

    char_audit = dict(character_summary_block_audit)
    retrieval_summary = char_audit.pop("retrieval_summary", None)
    summary_blocks_audit, has_binding_constraints, binding_constraints_section = (
        split_character_prompt_audit_for_metadata(char_audit)
    )

    try:
        audit_logger = get_audit_logger_fn()
        session_owner, session_num, _, _ = get_audit_context_fn()
        scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
            continuity_manager.scene_state if continuity_manager is not None else None
        )
        actor_scene_context = get_character_scene_audit_context_fn(
            next_actor, scene_audit_kwargs
        )
        char_entry = audit_logger.create_entry(
            session_owner=session_owner,
            session_number=session_num,
            round_number=round_number,
            turn_number=turn_number,
            bot_name=next_actor,
            bot_type="character",
            input_messages=[{"role": "system", "content": task_prompt}],
            raw_response=char_raw_response,
            parsed_output=move,
            context_snapshot={
                "director_decision": decision,
                "character_names": char_names,
                "continuity_event": continuity_event,
                "scene_state_after": scene_state_after,
                **actor_scene_context,
            },
            metadata=_merge_character_audit_metadata(
                base={
                    "parse_error": "",
                    "action": move.get("action", ""),
                    "has_dialogue": bool(move.get("dialogue")),
                    "issue_updates": issue_updates,
                    "presence_changes": presence_changes,
                    "consequences": consequences,
                    "summary_blocks": summary_blocks_audit,
                    "has_binding_constraints": has_binding_constraints,
                    "scene_binding_constraints_section": binding_constraints_section,
                    "turn_execution": turn_execution_metadata or {},
                    **(
                        {"retrieval_summary": retrieval_summary}
                        if isinstance(retrieval_summary, dict)
                        else {}
                    ),
                    **(
                        {"character_audit_v1": character_audit_v1}
                        if isinstance(character_audit_v1, dict)
                        else {}
                    ),
                    **(
                        {"audit_v2": audit_v2}
                        if isinstance(audit_v2, dict) and audit_v2
                        else {}
                    ),
                },
                progression_advisory=progression_advisory,
                anti_regression_advisory=anti_regression_advisory,
            ),
            **scene_audit_kwargs,
        )
        audit_logger.log_bot_interaction(char_entry)
    except Exception as exc:
        log_audit_exception(
            f"audit: character log_bot_interaction failed (round={round_number} "
            f"turn={turn_number} actor={next_actor})",
            exc,
        )


def log_narrator_render_audit(
    *,
    continuity_manager: Any,
    next_actor: str,
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
    round_number: int,
    turn_number: int,
    progression_advisory: dict[str, Any] | None = None,
    anti_regression_advisory: dict[str, Any] | None = None,
    audit_v2: dict[str, Any] | None = None,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
) -> None:
    if not narrator_raw or not is_audit_enabled_fn():
        return

    (
        continuity_event,
        scene_state_after,
        issue_updates,
        presence_changes,
        consequences,
    ) = _get_turn_continuity_payload(
        continuity_manager=continuity_manager,
        next_actor=next_actor,
    )

    try:
        audit_logger = get_audit_logger_fn()
        session_owner, session_num, _, _ = get_audit_context_fn()
        scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
            continuity_manager.scene_state if continuity_manager is not None else None
        )
        actor_scene_context = get_character_scene_audit_context_fn(
            next_actor, scene_audit_kwargs
        )
        narrator_entry = audit_logger.create_entry(
            session_owner=session_owner,
            session_number=session_num,
            round_number=round_number,
            turn_number=turn_number,
            bot_name="Narrator",
            bot_type="narrator",
            input_messages=[{"role": "system", "content": narrator_prompt}],
            raw_response=narrator_raw,
            parsed_output={
                "rendered": (
                    rendered[:500] + "..." if len(rendered) > 500 else rendered
                )
            },
            context_snapshot={
                "character": next_actor,
                "action": move.get("action", ""),
                "has_dialogue": bool(move.get("dialogue")),
                "environment_event": decision.get("environment_event", ""),
                "continuity_event": continuity_event,
                "scene_state_after": scene_state_after,
                **actor_scene_context,
            },
            # Narrator audit v1 layers are additive, non-mutating, and must remain
            # separate from semantic_validation (distinct metadata keys).
            metadata=_merge_character_audit_metadata(
                base={
                    "rendered_length": len(rendered),
                    "word_count": len(rendered.split()),
                    "issue_updates": issue_updates,
                    "presence_changes": presence_changes,
                    "consequences": consequences,
                    "summary_blocks": narrator_summary_block_audit,
                    "semantic_validation": narrator_semantic_assessment or {},
                    "narrator_output_audit_v1": narrator_output_audit_v1,
                    "narrator_validation_audit_v1": narrator_validation_audit_v1,
                    "prose_dialogue_audit_v1": prose_dialogue_audit_v1,
                    **(
                        {"audit_v2": audit_v2}
                        if isinstance(audit_v2, dict) and audit_v2
                        else {}
                    ),
                },
                progression_advisory=progression_advisory,
                anti_regression_advisory=anti_regression_advisory,
            ),
            **scene_audit_kwargs,
        )
        audit_logger.log_bot_interaction(narrator_entry)
    except Exception as exc:
        log_audit_exception(
            f"audit: narrator log_bot_interaction failed (round={round_number} "
            f"turn={turn_number} character={next_actor})",
            exc,
        )


def write_turn_audit_artifacts(
    *,
    continuity_manager: Any,
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    rendered: str,
    round_number: int,
    turn_number: int,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
) -> None:
    if not is_audit_enabled_fn():
        return

    # Extract continuity payload first
    (
        continuity_event,
        scene_state_after,
        issue_updates,
        presence_changes,
        consequences,
    ) = _get_turn_continuity_payload(
        continuity_manager=continuity_manager,
        next_actor=next_actor,
    )

    try:
        audit_logger = get_audit_logger_fn()
        session_owner, session_num, _, _ = get_audit_context_fn()
        scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
            continuity_manager.scene_state if continuity_manager is not None else None
        )
        actor_scene_context = get_character_scene_audit_context_fn(
            next_actor, scene_audit_kwargs
        )
        audit_logger.write_round_index(
            session_owner=session_owner,
            session_number=session_num,
            round_number=round_number,
            turn_number=turn_number,
            acting_character=next_actor,
            director_choice_reason=decision.get("reason", ""),
            acting_role=actor_scene_context.get("character_role", ""),
            presence_constraint=actor_scene_context.get(
                "character_presence_constraint", ""
            ),
            authority_label=actor_scene_context.get("character_authority_label", ""),
            continuity_event_type=str(continuity_event.get("event_type", "") or ""),
            state_change_count=len(continuity_event.get("state_changes", []) or []),
            issue_update_count=len(issue_updates),
            presence_change_count=len(presence_changes),
        )
    except Exception as exc:
        log_audit_exception(
            f"audit: write_round_index failed (round={round_number} "
            f"turn={turn_number} actor={next_actor})",
            exc,
        )

    try:
        audit_logger = get_audit_logger_fn()
        session_owner, session_num, _, _ = get_audit_context_fn()
        scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
            continuity_manager.scene_state if continuity_manager is not None else None
        )
        actor_scene_context = get_character_scene_audit_context_fn(
            next_actor, scene_audit_kwargs
        )
        audit_logger.update_narrative_summary(
            session_owner=session_owner,
            session_number=session_num,
            round_number=round_number,
            turn_number=turn_number,
            acting_character=next_actor,
            rendered_output=rendered,
            character_move=move,
            director_decision=decision,
            acting_role=actor_scene_context.get("character_role", ""),
            presence_constraint=actor_scene_context.get(
                "character_presence_constraint", ""
            ),
            authority_label=actor_scene_context.get("character_authority_label", ""),
            continuity_event=continuity_event,
            scene_state_after=scene_state_after,
            issue_updates=issue_updates,
            presence_changes=presence_changes,
            **scene_audit_kwargs,
        )
        # Update manifest with current total turn count
        audit_logger.update_manifest_turn_counter(
            session_owner=session_owner,
            session_number=session_num,
            total_turns=continuity_manager.turn_counter if continuity_manager else 0,
        )
    except Exception as exc:
        log_audit_exception(
            f"audit: update_narrative_summary or manifest update failed "
            f"(round={round_number} turn={turn_number} actor={next_actor})",
            exc,
        )


def refresh_audit_summary_report_if_enabled(
    *, is_audit_enabled_fn, refresh_audit_summary_report_fn
) -> None:
    if not is_audit_enabled_fn():
        return

    try:
        refresh_audit_summary_report_fn()
    except Exception as exc:
        log_audit_exception("audit: refresh_audit_summary_report failed", exc)
