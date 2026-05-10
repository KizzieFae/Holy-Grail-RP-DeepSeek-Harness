"""Issue #174: import surface + glue behavioral parity (app facade extraction)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import app  # noqa: E402
import app_turn_helpers as turn_helpers  # noqa: E402
from app_actor_selection_glue import choose_fallback_actor_from_orchestration  # noqa: E402
from app_audit_glue import build_scene_audit_logging_kwargs_for_audit  # noqa: E402
from app_dialogue_glue import build_recent_dialogue_history_from_session  # noqa: E402
from cross_session_memory_policy import compact_report_for_audit  # noqa: E402
from orchestration_helpers import choose_fallback_actor as choose_fallback_actor_impl  # noqa: E402
from perception_audibility import build_recent_dialogue_history_for_viewer  # noqa: E402
from summary_audit_helpers import get_scene_audit_logging_kwargs  # noqa: E402


KNOWN_FROM_APP_IMPORT_SYMBOLS = frozenset(
    {
        "PROMPT_DIALOGUE_HISTORY_LIMIT",
        "build_memory_fact_summary",
        "build_recent_dialogue_history",
        "get_player_control_mode",
        "has_player_character_conflict",
        "resolve_bot_reply_limit",
    }
)

KNOWN_APP_ATTRIBUTE_SYMBOLS = frozenset(
    {
        "init_session_state",
        "start_scene",
        "process_user_message",
        "skip_turn",
        "end_scene",
        "load_existing_session",
        "save_current_session",
        "run_app_startup",
    }
)


def test_app_import_surface_parity() -> None:
    missing = sorted(
        n
        for n in KNOWN_FROM_APP_IMPORT_SYMBOLS | KNOWN_APP_ATTRIBUTE_SYMBOLS
        if not hasattr(app, n)
    )
    assert not missing, f"missing on app module: {missing}"


def test_app_reexports_constants_from_app_constants() -> None:
    from app_constants import (  # noqa: E402
        DIRECTOR_SPOTLIGHT_HISTORY_LIMIT,
        ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT,
        ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT,
        ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT,
        ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT,
        ORCHESTRATION_TENSION_HISTORY_LIMIT,
        PROMPT_DIALOGUE_HISTORY_LIMIT,
        PROMPT_STRUCTURED_MOVE_LIMIT,
    )

    assert app.PROMPT_DIALOGUE_HISTORY_LIMIT is PROMPT_DIALOGUE_HISTORY_LIMIT
    assert app.PROMPT_STRUCTURED_MOVE_LIMIT is PROMPT_STRUCTURED_MOVE_LIMIT
    assert app.DIRECTOR_SPOTLIGHT_HISTORY_LIMIT is DIRECTOR_SPOTLIGHT_HISTORY_LIMIT
    assert app.ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT is ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT
    assert (
        app.ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT
        is ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT
    )
    assert (
        app.ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT
        is ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT
    )
    assert (
        app.ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT
        is ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT
    )
    assert app.ORCHESTRATION_TENSION_HISTORY_LIMIT is ORCHESTRATION_TENSION_HISTORY_LIMIT


def test_audit_glue_matches_baseline_merge() -> None:
    scene_state = SimpleNamespace(
        scene_template_id="t1",
        scene_premise="prem",
        role_assignments={"A": "r"},
        character_presence_constraints={},
        character_authority_labels={},
    )
    report = {"sections": [{"preview": "x" * 200}]}
    session_state: dict = {"cross_session_injection_report": report}

    expected = dict(get_scene_audit_logging_kwargs(scene_state))
    expected["cross_session_injection_report"] = compact_report_for_audit(report)

    assert build_scene_audit_logging_kwargs_for_audit(scene_state, session_state) == expected

    assert build_scene_audit_logging_kwargs_for_audit(
        scene_state, {}
    ) == get_scene_audit_logging_kwargs(scene_state)


def test_dialogue_glue_matches_direct_viewer_call() -> None:
    class _C:
        def __init__(self, name: str) -> None:
            self.name = name

    session_state = {"characters": [_C("Alice"), _C("Bob")]}
    chat_history = [
        {"role": "assistant", "name": "Alice", "content": "Hi"},
        {"role": "assistant", "name": "Bob", "content": "Hey"},
    ]

    def _display(n: str) -> str:
        return n.upper()

    direct = build_recent_dialogue_history_for_viewer(
        chat_history=chat_history,
        viewer_character_name="Alice",
        character_names=["Alice", "Bob"],
        get_character_display_name_fn=_display,
        limit=6,
    )
    glued = build_recent_dialogue_history_from_session(
        chat_history,
        session_state=session_state,
        limit=6,
        viewer_character_name="Alice",
        get_character_display_name_fn=_display,
    )
    assert glued == direct


def test_fallback_actor_glue_matches_turn_helper_path() -> None:
    orch = {"spotlight_history": ["Alice", "Bob"]}
    available = ["Alice", "Bob"]

    expected = turn_helpers.choose_fallback_actor(
        available_actors=available,
        forced_speaker=None,
        spotlight_history=orch.get("spotlight_history", []),
        choose_fallback_actor_impl_fn=choose_fallback_actor_impl,
        prefer_continuing_spotlight=False,
    )
    got = choose_fallback_actor_from_orchestration(
        available,
        None,
        orchestration_state=orch,
        prefer_continuing_spotlight=False,
    )
    assert got == expected


def test_app_thin_wrappers_delegate_to_glue_modules() -> None:
    with mock.patch("app.build_scene_audit_logging_kwargs_for_audit") as audit_glue:
        audit_glue.return_value = {"ok": True}
        assert app.get_scene_audit_logging_kwargs_for_audit(None) == {"ok": True}
        audit_glue.assert_called_once_with(None, app.st.session_state)

    with mock.patch("app.build_recent_dialogue_history_from_session") as dlg_glue:
        dlg_glue.return_value = []
        app.build_recent_dialogue_history(
            [], limit=4, viewer_character_name="viewer"
        )
        dlg_glue.assert_called_once_with(
            [],
            session_state=app.st.session_state,
            limit=4,
            viewer_character_name="viewer",
            get_character_display_name_fn=app.get_character_display_name,
        )

    orch = {"spotlight_history": ["x"]}
    with mock.patch.object(app, "get_orchestration_state", return_value=orch):
        with mock.patch("app.choose_fallback_actor_from_orchestration") as act_glue:
            act_glue.return_value = "Alice"
            got = app.choose_fallback_actor(
                ["Alice"], None, prefer_continuing_spotlight=True
            )
            assert got == "Alice"
            act_glue.assert_called_once_with(
                ["Alice"],
                None,
                orchestration_state=orch,
                prefer_continuing_spotlight=True,
            )
