"""User Callout controls (Issue #55) for audit-backed Streamlit sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app_state_audit import AuditIdentityMissingError
from user_callouts import (
    UserCalloutDocumentError,
    get_user_callouts_path,
    new_callout,
)


def _runtime_session_id(st_module: Any) -> str | None:
    raw = st_module.session_state.get("session_id")
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _scene_template_id(
    st_module: Any, get_continuity_manager_fn: Callable[[], Any | None]
) -> str | None:
    try:
        cm = get_continuity_manager_fn()
    except Exception:
        return None
    if cm is None or getattr(cm, "scene_state", None) is None:
        return None
    tid = getattr(cm.scene_state, "scene_template_id", None)
    if not tid:
        return None
    s = str(tid).strip()
    return s or None


def _continuity_turn_index(
    st_module: Any, get_continuity_manager_fn: Callable[[], Any | None]
) -> int | None:
    try:
        cm = get_continuity_manager_fn()
    except Exception:
        return None
    if cm is None:
        return None
    try:
        return int(getattr(cm, "turn_counter", 0) or 0)
    except (TypeError, ValueError):
        return None


def _session_state_path(
    st_module: Any, session_manager_cls: Any
) -> Path | None:
    sid = _runtime_session_id(st_module)
    if not sid:
        return None
    sm = session_manager_cls()
    p = sm.sessions_dir / f"{sid}.json"
    if p.is_file():
        return p
    return None


def render_user_callout_controls(
    *,
    st_module: Any,
    is_audit_enabled_fn: Callable[[], bool],
    get_audit_context_fn: Callable[
        [],
        tuple[str, int, int, int],
    ],
    get_audit_logger_fn: Callable[[], Any],
    get_continuity_manager_fn: Callable[[], Any | None],
    session_manager_cls: Any,
) -> None:
    if not st_module.session_state.get("scene_started", False):
        return
    if not is_audit_enabled_fn():
        return

    st_module.subheader("User callouts")
    st_module.caption(
        "Append a non-authoritative triage note to **user_callouts_v1.json** for this "
        "audit session. Does not change scene behavior, continuity, or validation."
    )

    st_module.text_area(
        "Optional note",
        key="user_callout_note_area_v1",
        height=80,
        placeholder="e.g. Check grounding vs dialogue on next review",
    )

    if st_module.button("Save user callout", key="user_callout_save_v1", type="secondary"):
        note_raw = str(st_module.session_state.get("user_callout_note_area_v1", "") or "")
        try:
            owner, snum, rnum, tnum = get_audit_context_fn()
        except AuditIdentityMissingError as exc:
            st_module.error(str(exc))
            return

        if not is_audit_enabled_fn():
            st_module.error("Auditing is off; enable before **Start Scene** to use callouts.")
            return

        logger = get_audit_logger_fn()
        base_dir = getattr(logger, "base_dir", None)
        if base_dir is None:
            st_module.error("Audit logger has no base_dir.")
            return
        if not isinstance(base_dir, Path):
            base_dir = Path(base_dir)

        path = get_user_callouts_path(
            base_dir=base_dir, audit_session_number=int(snum)
        )
        session_state_path = _session_state_path(st_module, session_manager_cls)
        try:
            record = new_callout(
                base_dir=base_dir,
                path=path,
                audit_session_owner=owner,
                audit_session_number=int(snum),
                audit_round_number=int(rnum),
                audit_turn_number=int(tnum),
                runtime_session_id=_runtime_session_id(st_module),
                scene_template_id=_scene_template_id(
                    st_module, get_continuity_manager_fn
                ),
                continuity_turn_index=_continuity_turn_index(
                    st_module, get_continuity_manager_fn
                ),
                note=note_raw.strip() or None,
                session_state_json=session_state_path,
            )
        except UserCalloutDocumentError as exc:
            st_module.error(
                f"**user_callouts_v1.json** is invalid or corrupt; file was not changed. {exc}"
            )
            return
        except (OSError, ValueError) as exc:
            st_module.error(f"Could not save user callout: {exc}")
            return

        rel = str(path).replace("\\", "/")
        st_module.success(
            f"Saved user callout **{record.get('callout_id', '')}** to `{rel}`"
        )
        st_module.session_state.pop("user_callout_note_area_v1", None)
