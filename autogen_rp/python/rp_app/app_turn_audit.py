from typing import Any

from audit_instrumentation import log_audit_exception


def log_turn_failure(
    *,
    st_module: Any,
    round_number: int,
    turn_number: int,
    bot_name: str,
    bot_type: str,
    stage: str,
    reason: str,
    input_messages: list[dict[str, Any]] | None,
    raw_response: str,
    parsed_output: dict[str, Any] | None,
    context_snapshot: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    build_attempted_post_details_fn,
    get_continuity_manager_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
) -> None:
    rejection = {
        "speaker": bot_name,
        "content": (
            raw_response[:200] if raw_response else str(parsed_output or {})[:200]
        ),
        "reason": f"{stage}: {reason}",
    }
    st_module.session_state["rejected_messages"].append(rejection)
    st_module.session_state["selector_decisions"].append(
        f"Turn failure for {bot_name} at {stage}: {reason}"
    )

    if not is_audit_enabled_fn():
        return

    try:
        audit_logger = get_audit_logger_fn()
        session_owner, session_num, _, _ = get_audit_context_fn()
        attempted_post = build_attempted_post_details_fn(raw_response, parsed_output)
        continuity_manager = get_continuity_manager_fn()
        scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
            continuity_manager.scene_state if continuity_manager is not None else None
        )
        failure_context_snapshot = dict(context_snapshot or {})
        if bot_type == "character":
            failure_context_snapshot.update(
                get_character_scene_audit_context_fn(bot_name, scene_audit_kwargs)
            )
        entry = audit_logger.create_entry(
            session_owner=session_owner,
            session_number=session_num,
            round_number=round_number,
            turn_number=turn_number,
            bot_name=f"{bot_name}_{stage}",
            bot_type=f"{bot_type}_failure",
            input_messages=input_messages or [],
            raw_response=raw_response,
            parsed_output=parsed_output or {},
            context_snapshot=failure_context_snapshot,
            metadata={
                "failure_stage": stage,
                "failure_reason": reason,
                **({"attempted_post": attempted_post} if attempted_post else {}),
                **(metadata or {}),
            },
            **scene_audit_kwargs,
        )
        audit_logger.log_bot_interaction(entry)
    except Exception as exc:
        log_audit_exception(
            f"audit: log_turn_failure log_bot_interaction failed "
            f"(round={round_number} turn={turn_number} bot={bot_name})",
            exc,
        )
