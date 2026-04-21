"""Issue #84 — scene-start audit failures must be visible (not silently swallowed)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import app  # noqa: E402
from scene_opener import OpenerManager  # noqa: E402
from test_rp_app_smoke_flows import (  # noqa: E402
    FakeAuditLogger,
    FakeCharacterStateManager,
    FakeContinuityManager,
    FakeStreamlit,
    init_fake_session,
    make_loader,
)


class _AuditLoggerManifestFail(FakeAuditLogger):
    def write_session_manifest(self, **_kwargs) -> None:
        raise RuntimeError("manifest failed")


class _AuditLoggerManifestOk(FakeAuditLogger):
    def write_session_manifest(self, **_kwargs) -> None:
        return None


@pytest.fixture
def fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> FakeStreamlit:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_st)
    return fake_st


@pytest.mark.asyncio
async def test_start_scene_audit_manifest_failure_surfaces_error_and_continues(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["opening_mode"] = "custom"
    session_state["custom_opener_text"] = "Opening line."
    session_state["audit_enabled"] = True
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            opening_description="",
            environment_description="",
            location="",
            time_of_day="",
            present_characters=["Ayame"],
            absent_but_relevant=[],
            scene_template_id=None,
            scene_premise="",
            role_assignments={},
            character_presence_constraints={},
            character_authority_labels={},
        )
    )
    run_calls: dict[str, object] = {}

    async def fake_run_character_turns(**kwargs) -> None:
        run_calls.update(kwargs)

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(app, "close_active_scene_if_needed", fake_close_active_scene_if_needed)
    monkeypatch.setattr(app, "shutdown_runtime_resources", fake_shutdown_runtime_resources)
    monkeypatch.setattr(app, "CharacterLoader", make_loader({"ayame": "Ayame"}))
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(
        app, "resolve_scene_template_setup", lambda *_a, **_k: (None, "")
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_a, **_k: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(app, "sync_orchestration_state_from_continuity", lambda: None)
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(app, "load_cross_session_memories", lambda *_a, **_k: {})
    monkeypatch.setattr(app, "apply_cross_session_memories", lambda *_a, **_k: None)
    monkeypatch.setattr(app, "create_narrator_agent", lambda _c: object())
    monkeypatch.setattr(app, "create_director_agent", lambda _c: object())
    monkeypatch.setattr(
        app,
        "SessionManager",
        lambda: SimpleNamespace(generate_session_id=lambda _chars: "scene_123"),
    )
    monkeypatch.setattr(app, "OpenerManager", OpenerManager)
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)
    monkeypatch.setattr(app, "get_audit_logger", lambda: _AuditLoggerManifestFail())

    started = await app.start_scene(["ayame"])

    assert started is True
    assert session_state["scene_started"] is True
    assert len(fake_streamlit.errors) == 1
    assert "Audit logging failed during scene start" in fake_streamlit.errors[0]
    assert "manifest failed" in fake_streamlit.errors[0]
    assert run_calls.get("trigger_text") == "Opening line."


@pytest.mark.asyncio
async def test_start_scene_audit_refresh_failure_surfaces_error_and_continues(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["opening_mode"] = "custom"
    session_state["custom_opener_text"] = "Opening line."
    session_state["audit_enabled"] = True
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            opening_description="",
            environment_description="",
            location="",
            time_of_day="",
            present_characters=["Ayame"],
            absent_but_relevant=[],
            scene_template_id=None,
            scene_premise="",
            role_assignments={},
            character_presence_constraints={},
            character_authority_labels={},
        )
    )

    async def fake_run_character_turns(**_kwargs) -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(app, "close_active_scene_if_needed", fake_close_active_scene_if_needed)
    monkeypatch.setattr(app, "shutdown_runtime_resources", fake_shutdown_runtime_resources)
    monkeypatch.setattr(app, "CharacterLoader", make_loader({"ayame": "Ayame"}))
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(
        app, "resolve_scene_template_setup", lambda *_a, **_k: (None, "")
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_a, **_k: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(app, "sync_orchestration_state_from_continuity", lambda: None)
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(app, "load_cross_session_memories", lambda *_a, **_k: {})
    monkeypatch.setattr(app, "apply_cross_session_memories", lambda *_a, **_k: None)
    monkeypatch.setattr(app, "create_narrator_agent", lambda _c: object())
    monkeypatch.setattr(app, "create_director_agent", lambda _c: object())
    monkeypatch.setattr(
        app,
        "SessionManager",
        lambda: SimpleNamespace(generate_session_id=lambda _chars: "scene_124"),
    )
    monkeypatch.setattr(app, "OpenerManager", OpenerManager)
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)
    monkeypatch.setattr(app, "get_audit_logger", lambda: _AuditLoggerManifestOk())

    def boom_refresh() -> None:
        raise RuntimeError("refresh failed")

    monkeypatch.setattr(app, "refresh_audit_summary_report", boom_refresh)

    started = await app.start_scene(["ayame"])

    assert started is True
    assert len(fake_streamlit.errors) == 1
    assert "Audit logging failed during scene start" in fake_streamlit.errors[0]
    assert "refresh failed" in fake_streamlit.errors[0]
