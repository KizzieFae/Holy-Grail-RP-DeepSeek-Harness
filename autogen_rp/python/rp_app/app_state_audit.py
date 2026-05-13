from typing import Any

from retrieval_audit_helpers import apply_retrieval_session_to_audit_summary


class AuditIdentityMissingError(RuntimeError):
    """Auditing is on but ``audit_session_owner`` is missing (Issue #106).

    ``scene_owner`` is not a valid fallback. Legacy saves without
    ``metadata.audit_session_owner`` are not audit-supported.
    """


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
    get_continuity_manager_fn: Any | None = None,
) -> None:
    if not is_audit_enabled_fn():
        return

    audit_logger = get_audit_logger_fn()
    session_owner, session_num, _, _ = get_audit_context_fn()
    cm = (
        get_continuity_manager_fn()
        if get_continuity_manager_fn is not None
        else None
    )
    report_path = audit_logger.write_summary_report(
        session_owner=session_owner,
        session_number=session_num,
        continuity_manager=cm,
    )
    st_module.session_state["audit_summary_report_path"] = report_path
    apply_retrieval_session_to_audit_summary(
        report_path,
        saw_nonempty_bundle=bool(
            st_module.session_state.get("sim_retrieval_saw_nonempty_bundle")
        ),
    )


# Issue #106: audit identity must come from ``audit_session_owner`` only.
# Do not derive from ``scene_owner`` or other UI fields.
def get_audit_context(
    *,
    st_module: Any,
    is_audit_enabled_fn,
    get_audit_logger_fn,
) -> tuple[str, int, int, int]:
    audit_on = is_audit_enabled_fn()
    raw_owner = st_module.session_state.get("audit_session_owner")
    session_owner = str(raw_owner).strip() if raw_owner is not None else ""
    if audit_on:
        if not session_owner:
            raise AuditIdentityMissingError(
                "audit_session_owner is required when auditing is enabled (Issue #106). "
                "scene_owner is not a fallback. Load legacy sessions without "
                "metadata.audit_session_owner with auditing disabled."
            )

    audit_session_num = st_module.session_state.get("audit_session_number")
    if audit_session_num is None and audit_on:
        audit_logger = get_audit_logger_fn()
        audit_session_num = audit_logger.claim_next_session_number()
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
