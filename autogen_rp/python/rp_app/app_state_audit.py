from typing import Any


def is_audit_enabled(*, st_module: Any) -> bool:
    return bool(st_module.session_state.get("audit_enabled", False))


def is_llm_audit_enabled(*, st_module: Any) -> bool:
    return bool(st_module.session_state.get("llm_audit_enabled", False))


def refresh_audit_summary_report(
    *,
    st_module: Any,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
) -> None:
    if not is_audit_enabled_fn():
        return

    audit_logger = get_audit_logger_fn()
    session_owner, session_num, _, _ = get_audit_context_fn()
    report_path = audit_logger.write_summary_report(
        session_owner=session_owner,
        session_number=session_num,
    )
    st_module.session_state["audit_summary_report_path"] = report_path


def get_audit_context(
    *,
    st_module: Any,
    is_audit_enabled_fn,
    get_audit_logger_fn,
) -> tuple[str, int, int, int]:
    session_owner = (
        st_module.session_state.get("audit_session_owner")
        or st_module.session_state.get("scene_owner")
        or "Unknown"
    )

    audit_session_num = st_module.session_state.get("audit_session_number")
    if audit_session_num is None and is_audit_enabled_fn():
        audit_logger = get_audit_logger_fn()
        audit_session_num = audit_logger.get_next_session_number()
        st_module.session_state["audit_session_number"] = audit_session_num

    round_number = st_module.session_state.get("audit_round_number", 0)
    turn_number = st_module.session_state.get("audit_turn_number", 0)

    return session_owner, audit_session_num or 0, round_number, turn_number


def start_audit_round(*, st_module: Any) -> int:
    current = st_module.session_state.get("audit_round_number", 0) + 1
    st_module.session_state["audit_round_number"] = current
    st_module.session_state["audit_turn_number"] = 0
    return current


def set_audit_turn(*, st_module: Any, turn_number: int) -> int:
    st_module.session_state["audit_turn_number"] = turn_number
    return turn_number
