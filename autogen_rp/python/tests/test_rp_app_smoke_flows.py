import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import app
from scene_opener import OpenerManager
from session_manager import SessionManager
from turn_runner_turn import execute_character_turn


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def info(self, message: str) -> None:
        self.infos.append(message)

    def spinner(self, _message: str):
        return nullcontext()

    def chat_message(self, _role: str):
        return nullcontext()

    def markdown(self, *_args, **_kwargs) -> None:
        return None

    def caption(self, *_args, **_kwargs) -> None:
        return None

    def title(self, *_args, **_kwargs) -> None:
        return None


class FakeAuditLogger:
    def get_next_session_number(self) -> int:
        return 1


class DummyState:
    def __init__(self, name: str) -> None:
        self.name = name
        self.relationships: dict[str, object] = {}

    def set_relationship_context(self, target_name: str, **kwargs) -> None:
        relationship = dict(self.relationships.get(target_name, {}))
        relationship.update({key: value for key, value in kwargs.items() if value})
        relationship["entity_type"] = str(
            relationship.get("entity_type", "character") or "character"
        )
        self.relationships[target_name] = relationship

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "relationships": self.relationships}


class FakeCharacterStateManager:
    def __init__(self) -> None:
        self.states: dict[str, object] = {}

    def register_character(self, name: str, state: object) -> None:
        self.states[name] = state


class FakeContinuityManager:
    def __init__(self, scene_state: SimpleNamespace) -> None:
        self.scene_state = scene_state
        self.seeded_character_states: dict[str, object] | None = None
        self.anchor_character_id: str | None = None
        self.setup_seam_complete: bool = False

    def bootstrap_present_characters_from_cast(self, character_names: list[str]) -> None:
        if self.scene_state is None:
            return
        cur = getattr(self.scene_state, "present_characters", None) or []
        if not cur and character_names:
            self.scene_state.present_characters = list(character_names)

    def apply_must_remain_presence_from_fn(self, get_must_remain_characters_fn) -> None:
        if self.scene_state is None:
            return
        if not hasattr(self.scene_state, "present_characters"):
            self.scene_state.present_characters = []
        to_dict = getattr(self.scene_state, "to_dict", None)
        d = to_dict() if callable(to_dict) else {}
        try:
            must = get_must_remain_characters_fn(d)
        except Exception:
            return
        for n in must:
            if n not in self.scene_state.present_characters:
                self.scene_state.present_characters.append(n)

    def seed_character_canon_anchors(self, char_states: dict[str, object]) -> None:
        self.seeded_character_states = dict(char_states)

    def notify_raw_location_bypass_for_audit(self) -> None:
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_state": {
                "scene_template_id": self.scene_state.scene_template_id,
                "scene_premise": self.scene_state.scene_premise,
                "role_assignments": dict(self.scene_state.role_assignments),
            }
        }


def make_loader(name_map: dict[str, str]):
    class Loader:
        def load_and_create_agent(self, char_file: str, _model_client):
            display_name = name_map.get(char_file, str(char_file))
            return SimpleNamespace(name=display_name), DummyState(display_name)

        def load_character_card(self, identifier: str) -> dict[str, str]:
            return {"name": name_map.get(identifier, str(identifier))}

        def list_available_characters(self) -> list[str]:
            return list(name_map)

    return Loader


def init_fake_session(fake_st: FakeStreamlit) -> dict[str, object]:
    app.init_session_state()
    fake_st.session_state["user_name"] = "Alex"
    return fake_st.session_state


@pytest.fixture
def fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> FakeStreamlit:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "get_audit_logger", lambda: FakeAuditLogger())
    return fake_st


@pytest.mark.asyncio
async def test_start_scene_smoke_initializes_scene_and_posts_opening(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["opening_mode"] = "custom"
    session_state["custom_opener_text"] = "Opening line."
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
    save_calls: list[str] = []

    async def fake_run_character_turns(**kwargs) -> None:
        run_calls.update(kwargs)

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        save_calls.append("saved")

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(app, "CharacterLoader", make_loader({"ayame": "Ayame"}))
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(
        app, "resolve_scene_template_setup", lambda *_args, **_kwargs: (None, "")
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(app, "sync_orchestration_state_from_continuity", lambda: None)
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "load_cross_session_memories", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(app, "create_narrator_agent", lambda _client: object())
    monkeypatch.setattr(app, "create_director_agent", lambda _client: object())
    monkeypatch.setattr(
        app,
        "SessionManager",
        lambda: SimpleNamespace(generate_session_id=lambda: "scene_123"),
    )
    monkeypatch.setattr(app, "OpenerManager", OpenerManager)
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)

    started = await app.start_scene(["ayame"])

    assert started is True
    assert session_state["session_id"] == "scene_123"
    bi = session_state.get("bootstrap_interpretation") or {}
    assert bi.get("opening_resolved_text") == "Opening line."
    assert bi.get("first_round_user_line") == "Opening line."
    assert bi.get("opening_strategy") == "template_static_text"
    assert session_state["scene_started"] is True
    assert session_state["bot_reply_limit"] == 1
    assert "Opening line." in str(session_state["chat_history"][0]["content"])
    assert run_calls["trigger_text"] == "Opening line."
    assert run_calls["user_name"] == "Alex"
    assert continuity_manager.seeded_character_states is not None
    assert save_calls == ["saved"]


@pytest.mark.asyncio
async def test_start_scene_fails_on_invalid_opening_mode_before_compose(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_fake_session(fake_streamlit)
    fake_streamlit.session_state["opening_mode"] = "not_a_valid_mode"

    async def _compose_should_not_run(*_a, **_k) -> object:
        raise AssertionError("compose_streamlit_bootstrap should not be called for invalid mode")

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    import scene_lifecycle_start as sls

    monkeypatch.setattr(sls, "compose_streamlit_bootstrap", _compose_should_not_run)

    started = await app.start_scene(["ayame"])

    assert started is False
    assert fake_streamlit.errors
    err_blob = " ".join(fake_streamlit.errors).lower()
    assert "invalid" in err_blob and "opening_mode" in err_blob


@pytest.mark.asyncio
async def test_start_scene_fails_on_unset_opening_mode_before_compose(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["opening_mode"] = None

    async def _compose_should_not_run(*_a, **_k) -> object:
        raise AssertionError("compose_streamlit_bootstrap should not be called when mode unset")

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    import scene_lifecycle_start as sls

    monkeypatch.setattr(sls, "compose_streamlit_bootstrap", _compose_should_not_run)

    started = await app.start_scene(["ayame"])

    assert started is False
    assert fake_streamlit.errors
    err_blob = " ".join(fake_streamlit.errors).lower()
    assert "required" in err_blob and "opening_mode" in err_blob


@pytest.mark.asyncio
async def test_start_scene_smoke_seeds_role_relationship_context_from_scene_template(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["opening_mode"] = "custom"
    session_state["custom_opener_text"] = "Opening line."
    scene_state = SimpleNamespace(
        opening_description="",
        environment_description="",
        location="",
        time_of_day="",
        present_characters=[],
        absent_but_relevant=[],
        scene_template_id=None,
        scene_premise="",
        role_assignments={},
        character_presence_constraints={},
        character_authority_labels={},
    )
    scene_state.to_dict = lambda: {
        "scene_template_id": scene_state.scene_template_id,
        "scene_premise": scene_state.scene_premise,
        "role_assignments": dict(scene_state.role_assignments),
        "character_presence_constraints": dict(
            scene_state.character_presence_constraints
        ),
        "character_authority_labels": dict(scene_state.character_authority_labels),
        "present_characters": list(scene_state.present_characters),
    }
    continuity_manager = FakeContinuityManager(scene_state)

    async def fake_run_character_turns(**_kwargs) -> None:
        return None

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    async def fake_shutdown_runtime_resources() -> None:
        return None

    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(
        app, "CharacterLoader", make_loader({"celina": "Celina", "kizzie": "Kizzie"})
    )
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(
        app,
        "resolve_scene_template_setup",
        lambda *_args, **_kwargs: (
            {
                "template_id": "celina_apartment_recovery_watch",
                "premise": "A protector stabilizes a recovering demi-human in a private refuge.",
                "opening_text": "",
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
            "",
        ),
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(app, "sync_orchestration_state_from_continuity", lambda: None)
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "load_cross_session_memories", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(app, "create_narrator_agent", lambda _client: object())
    monkeypatch.setattr(app, "create_director_agent", lambda _client: object())
    monkeypatch.setattr(
        app,
        "SessionManager",
        lambda: SimpleNamespace(generate_session_id=lambda: "scene_456"),
    )
    monkeypatch.setattr(app, "OpenerManager", OpenerManager)
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)
    import scene_lifecycle_start as sls

    def _noop_finalize(cm: FakeContinuityManager, *, cast: list[str] | None = None) -> None:
        _ = cast
        cm.setup_seam_complete = True

    monkeypatch.setattr(sls, "finalize_continuity_setup_seam", _noop_finalize)

    started = await app.start_scene(["celina", "kizzie"])

    assert started is True
    assert continuity_manager.seeded_character_states is not None
    celina_state = continuity_manager.seeded_character_states["Celina"]
    kizzie_state = continuity_manager.seeded_character_states["Kizzie"]
    assert (
        celina_state.relationships["Kizzie"]["medium_term_goal"]
        == "stabilize Kizzie while controlling the immediate scene around them"
    )
    assert (
        celina_state.relationships["Kizzie"]["current_objective"]
        == "assess Kizzie's condition and keep them responsive"
    )
    assert (
        kizzie_state.relationships["Celina"]["medium_term_goal"]
        == "secure safety from Celina without surrendering autonomy"
    )
    assert (
        kizzie_state.relationships["Celina"]["current_objective"]
        == "judge whether Celina's control is safe enough to cooperate with"
    )


@pytest.mark.asyncio
async def test_process_user_message_smoke_records_user_turn_and_saves(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["characters"] = [
        SimpleNamespace(name="Ayame"),
        SimpleNamespace(name="Celina"),
    ]
    session_state["chat_history"] = [
        {"role": "assistant", "speaker": "Ayame", "content": "Speak."}
    ]
    run_capture: dict[str, object] = {}
    saved: list[str] = []
    remembered: list[tuple[str, str]] = []

    async def fake_recreate_team_from_state():
        return session_state["characters"], object(), object(), object()

    async def fake_run_character_turns(**kwargs) -> None:
        run_capture["pending_forced_speaker"] = session_state.get(
            "pending_forced_speaker"
        )
        run_capture.update(kwargs)

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        saved.append("saved")

    monkeypatch.setattr(app, "recreate_team_from_state", fake_recreate_team_from_state)
    monkeypatch.setattr(
        app, "detect_forced_speaker", lambda *_args, **_kwargs: "Celina"
    )
    monkeypatch.setattr(
        app,
        "record_user_memories",
        lambda user_name, user_input: remembered.append((user_name, user_input)),
    )
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)

    await app.process_user_message("Celina, answer me.")

    assert session_state["chat_history"][-1] == {
        "role": "user",
        "content": "Celina, answer me.",
        "speaker": "Alex",
    }
    assert run_capture["trigger_text"] == "Celina, answer me."
    assert run_capture["pending_forced_speaker"] == "Celina"
    assert remembered == [("Alex", "Celina, answer me.")]
    assert session_state["pending_forced_speaker"] is None
    assert session_state["forced_speaker_consumed"] is False
    assert saved == ["saved"]


@pytest.mark.asyncio
async def test_execute_character_turn_smoke_uses_semantic_presence_override_and_narrator_fallback(
    fake_streamlit: FakeStreamlit,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    move = {
        "action": "held perfectly still",
        "dialogue": "Hai.",
        "motivation": {
            "goal": "cooperate",
            "tactic": "stay still",
            "emotional_driver": "trust",
            "risk_level": "low",
        },
    }
    failures: list[str] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(move))
            )

    async def fake_assess_presence_violation_semantics(**_kwargs):
        return {"is_valid": True, "reason": "left side refers to an injury location"}

    async def fake_render_character_move(*_args, **_kwargs):
        return ("Celina spoke for Kizzie.", "Celina spoke for Kizzie.", "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {
            "valid": False,
            "should_use_fallback": True,
            "issues": ["Narrator introduced other-character action"],
        }

    def fake_log_turn_failure(**kwargs) -> None:
        failures.append(str(kwargs.get("reason", "")))

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Kizzie",
        char_names=["Celina", "Kizzie"],
        decision={
            "next_actor": "Kizzie",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="Celina reaches toward Kizzie's left side.",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda _raw: (move, ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_args, **_kwargs: (
            False,
            "[SCENE_PRESENCE] Move contradicts must_remain presence for Celina",
        ),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=fake_assess_presence_violation_semantics,
        should_override_presence_rejection_fn=lambda reason, assessment: bool(
            reason.startswith("[SCENE_PRESENCE]")
            and assessment
            and assessment.get("is_valid")
        ),
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda char_name, rendered_move, _decision: f'{char_name} {rendered_move["action"]}.\n\n"{rendered_move["dialogue"]}"',
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert result["rendered"] == 'Kizzie held perfectly still.\n\n"Hai."'
    assert (
        session_state["chat_history"][-1]["content"]
        == 'Kizzie held perfectly still.\n\n"Hai."'
    )
    assert any(
        "Semantic validation kept Kizzie's turn" in item
        for item in session_state["selector_decisions"]
    )
    assert any(
        "Narrator fallback render used for Kizzie" in item
        for item in session_state["selector_decisions"]
    )
    assert failures == []
    nv = result["narrator_validation_audit_v1"]
    assert nv["derived"]["semantic_fallback_deterministic_critical"] is True
    assert nv["derived"]["semantic_fallback_llm_requested"] is True
    assert nv["derived"]["semantic_fallback_effective"] is True


@pytest.mark.asyncio
async def test_execute_character_turn_narrator_guardrail_without_llm_fallback_flag(
    fake_streamlit: FakeStreamlit,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    move = {
        "action": "held perfectly still",
        "dialogue": "Hai.",
        "motivation": {
            "goal": "cooperate",
            "tactic": "stay still",
            "emotional_driver": "trust",
            "risk_level": "low",
        },
    }
    failures: list[str] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(move))
            )

    async def fake_assess_presence_violation_semantics(**_kwargs):
        return {"is_valid": True, "reason": "left side refers to an injury location"}

    async def fake_render_character_move(*_args, **_kwargs):
        return ("Celina spoke for Kizzie.", "Celina spoke for Kizzie.", "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {
            "valid": False,
            "should_use_fallback": False,
            "dialogue_preserved": True,
            "stayed_in_scope": True,
            "issues": ["scope"],
        }

    def fake_log_turn_failure(**kwargs) -> None:
        failures.append(str(kwargs.get("reason", "")))

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Kizzie",
        char_names=["Celina", "Kizzie"],
        decision={
            "next_actor": "Kizzie",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="Celina reaches toward Kizzie's left side.",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda _raw: (move, ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_args, **_kwargs: (
            False,
            "[SCENE_PRESENCE] Move contradicts must_remain presence for Celina",
        ),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=fake_assess_presence_violation_semantics,
        should_override_presence_rejection_fn=lambda reason, assessment: bool(
            reason.startswith("[SCENE_PRESENCE]")
            and assessment
            and assessment.get("is_valid")
        ),
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda char_name, rendered_move, _decision: f'{char_name} {rendered_move["action"]}.\n\n"{rendered_move["dialogue"]}"',
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert result["rendered"] == 'Kizzie held perfectly still.\n\n"Hai."'
    assert any(
        "Narrator fallback render used for Kizzie" in item
        for item in session_state["selector_decisions"]
    )
    nv = result["narrator_validation_audit_v1"]
    assert nv["derived"]["semantic_fallback_deterministic_critical"] is True
    assert nv["derived"]["semantic_fallback_llm_requested"] is False
    assert nv["derived"]["semantic_fallback_effective"] is True
    assert failures == []


@pytest.mark.asyncio
async def test_execute_character_turn_no_narrator_fallback_when_semantics_clean(
    fake_streamlit: FakeStreamlit,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    move = {
        "action": "nods once",
        "dialogue": "Ok.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(move))
            )

    async def fake_render_character_move(*_args, **_kwargs):
        return ("MODEL_RENDERED", "RAW", "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {
            "valid": True,
            "should_use_fallback": False,
            "issues": [],
        }

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda _raw: (move, ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_args, **_kwargs: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_args, **_kwargs: False,
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_args, **_kwargs: "FALLBACK_TEMPLATE",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=lambda **_kwargs: None,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert result["rendered"] == "MODEL_RENDERED"
    assert not any(
        "Narrator fallback render used for Celina" in item
        for item in session_state["selector_decisions"]
    )
    nv = result["narrator_validation_audit_v1"]
    assert nv["derived"]["semantic_fallback_effective"] is False


@pytest.mark.asyncio
async def test_execute_character_turn_character_audit_v1_orchestration_only_logged(
    fake_streamlit: FakeStreamlit,
) -> None:
    """No continuity manager → turn_runner_turn else branch → orchestration_only audit blob in metadata."""
    init_fake_session(fake_streamlit)
    audit_entries: list[dict[str, object]] = []
    move = {
        "action": "nods once",
        "dialogue": "Ok.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(move))
            )

    class CapturingAuditLogger:
        def create_entry(self, **kwargs):
            return kwargs

        def log_bot_interaction(self, entry):
            audit_entries.append(entry)

    async def fake_render_character_move(*_args, **_kwargs):
        return ("MODEL_RENDERED", "RAW", "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {
            "valid": True,
            "should_use_fallback": False,
            "issues": [],
        }

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda _raw: (move, ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: True,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: CapturingAuditLogger(),
        get_audit_context_fn=lambda: ("Owner", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_args, **_kwargs: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_args, **_kwargs: False,
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_args, **_kwargs: "FALLBACK_TEMPLATE",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=lambda **_kwargs: None,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert len(audit_entries) == 1
    entry = audit_entries[0]
    metadata = entry["metadata"]
    assert "audit_v2" in metadata
    av2 = metadata["audit_v2"]
    assert av2["schema_version"] == 1
    assert "character_decision" in av2
    assert av2["character_decision"]["llm"]["status"] == "skipped"
    assert "character_audit_v1" in metadata
    audit_v1 = metadata["character_audit_v1"]
    assert isinstance(audit_v1, dict)
    assert audit_v1["observed"]["continuity_scope"] == "orchestration_only"
    assert (
        audit_v1["observed"]["scene_state_pre_source"]
        == "orchestration_state.scene_state_allowlist"
    )


@pytest.mark.asyncio
async def test_execute_character_turn_string_should_use_fallback_does_not_trigger(
    fake_streamlit: FakeStreamlit,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    move = {
        "action": "nods once",
        "dialogue": "Ok.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(move))
            )

    async def fake_render_character_move(*_args, **_kwargs):
        return ("MODEL_RENDERED", "RAW", "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {
            "valid": True,
            "should_use_fallback": "false",
            "issues": [],
        }

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda _raw: (move, ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_args, **_kwargs: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_args, **_kwargs: False,
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_args, **_kwargs: "FALLBACK_TEMPLATE",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=lambda **_kwargs: None,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert result["rendered"] == "MODEL_RENDERED"
    nv = result["narrator_validation_audit_v1"]
    assert nv["derived"]["semantic_fallback_llm_requested"] is False


@pytest.mark.asyncio
async def test_execute_character_turn_retries_once_on_duplicate_and_succeeds(
    fake_streamlit: FakeStreamlit,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    failures: list[tuple[str, str]] = []
    agent_calls: list[str] = []

    move_1 = {
        "action": "shifted her weight",
        "dialogue": "Repeated line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_2 = {
        "action": "leaned back",
        "dialogue": "New line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append("called")
            payload = json.dumps(move_1 if len(agent_calls) == 1 else move_2)
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

    def fake_validate_bot_response(content, *_args, **_kwargs):
        if "Repeated line." in str(content):
            return False, "[DUPLICATE] Exact duplicate dialogue detected"
        return True, ""

    async def fake_render_character_move(*_args, **_kwargs):
        move = _args[2]
        rendered = f'Celina {move["action"]}.\n\n"{move["dialogue"]}"'
        return (rendered, rendered, "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {"valid": True, "should_use_fallback": False, "issues": []}

    def fake_log_turn_failure(**kwargs) -> None:
        failures.append((str(kwargs.get("stage", "")), str(kwargs.get("reason", ""))))

    result = await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda raw: (json.loads(raw), ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=fake_validate_bot_response,
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_args, **_kwargs: False,
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_args, **_kwargs: "fallback",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert len(agent_calls) == 2
    assert session_state["chat_history"][-1]["content"].endswith('"New line."')
    assert any(
        "Retrying Celina after duplicate-output rejection" in item
        for item in session_state["selector_decisions"]
    )
    assert any(stage == "validation_duplicate_retry" for stage, _reason in failures)


@pytest.mark.asyncio
async def test_execute_character_turn_logs_retry_lineage_in_character_audit_metadata(
    fake_streamlit: FakeStreamlit,
) -> None:
    init_fake_session(fake_streamlit)
    failures: list[tuple[str, str]] = []
    agent_calls: list[str] = []
    audit_entries: list[dict[str, object]] = []

    move_1 = {
        "action": "shifted her weight",
        "dialogue": "Repeated line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_2 = {
        "action": "leaned back",
        "dialogue": "New line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append("called")
            payload = json.dumps(move_1 if len(agent_calls) == 1 else move_2)
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

    def fake_validate_bot_response(content, *_args, **_kwargs):
        if "Repeated line." in str(content):
            return False, "[DUPLICATE] Dialogue repetition detected"
        return True, ""

    async def fake_render_character_move(*_args, **_kwargs):
        move = _args[2]
        rendered = f'Celina {move["action"]}.\n\n"{move["dialogue"]}"'
        return (rendered, rendered, "prompt", False)

    async def fake_assess_narrator_render_semantics(**_kwargs):
        return {"valid": True, "should_use_fallback": False, "issues": []}

    def fake_log_turn_failure(**kwargs) -> None:
        failures.append((str(kwargs.get("stage", "")), str(kwargs.get("reason", ""))))

    class FakeAuditLogger:
        def create_entry(self, **kwargs):
            return kwargs

        def log_bot_interaction(self, entry):
            audit_entries.append(entry)

    await execute_character_turn(
        st_module=fake_streamlit,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_args, **_kwargs: (
            "prompt",
            {"prompt_evaluations": 0},
        ),
        parse_character_move_fn=lambda raw: (json.loads(raw), ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: True,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: FakeAuditLogger(),
        get_audit_context_fn=lambda: ("Owner", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=fake_validate_bot_response,
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_args, **_kwargs: False,
        build_recent_scene_context_fn=lambda *_args, **_kwargs: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_args, **_kwargs: "fallback",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert len(agent_calls) == 2
    assert any(stage == "validation_duplicate_retry" for stage, _reason in failures)
    assert len(audit_entries) == 1
    entry_metadata = audit_entries[0].get("metadata", {})
    assert isinstance(entry_metadata, dict)
    turn_execution = entry_metadata.get("turn_execution", {})
    assert isinstance(turn_execution, dict)
    assert turn_execution.get("attempt_index") == 1
    assert turn_execution.get("duplicate_retry_triggered") is True
    assert turn_execution.get("duplicate_retry_outcome") == "success_after_retry"


@pytest.mark.asyncio
async def test_skip_turn_smoke_appends_observer_message_and_saves(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    run_capture: dict[str, object] = {}
    saved: list[str] = []

    async def fake_recreate_team_from_state():
        return [SimpleNamespace(name="Ayame")], object(), object(), object()

    async def fake_run_character_turns(**kwargs) -> None:
        run_capture.update(kwargs)

    async def fake_save_current_session(*_args, **_kwargs) -> None:
        saved.append("saved")

    monkeypatch.setattr(app, "recreate_team_from_state", fake_recreate_team_from_state)
    monkeypatch.setattr(app, "run_character_turns", fake_run_character_turns)
    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)

    await app.skip_turn()

    assert session_state["chat_history"][-1]["content"] == "*Alex observes silently...*"
    assert "Alex is present but silent" in str(run_capture["trigger_text"])
    assert run_capture["user_name"] == "Alex"
    assert saved == ["saved"]


@pytest.mark.asyncio
async def test_end_scene_smoke_closes_scene_saves_and_shuts_down(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["session_id"] = "session_42"
    session_state["scene_started"] = True
    save_calls: list[tuple[str | None, str | None]] = []
    shutdown_calls: list[str] = []

    async def fake_save_current_session(
        scene_status=None, scene_closed_reason=None
    ) -> None:
        save_calls.append((scene_status, scene_closed_reason))

    async def fake_shutdown_runtime_resources() -> None:
        shutdown_calls.append("shutdown")

    monkeypatch.setattr(app, "save_current_session", fake_save_current_session)
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )

    await app.end_scene()

    assert session_state["scene_started"] is False
    assert session_state["scene_ended"] is True
    assert "session_42" in str(session_state["chat_history"][-1]["content"])
    assert save_calls == [("closed", "user_ended")]
    assert shutdown_calls == ["shutdown"]


@pytest.mark.asyncio
async def test_load_existing_session_restores_scene_template_and_audit_state(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    manager = SessionManager(tmp_path)
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            scene_template_id="household_entry_evaluation",
            scene_premise="A guarded evaluation.",
            role_assignments={"Ayame": "host", "Celina": "guard"},
        )
    )
    manager.save_session(
        session_id="saved_scene",
        team_state={"scene_state": {"opening_description": "Old opening"}},
        characters=["Ayame", "Celina"],
        metadata={
            "scene_template_id": "household_entry_evaluation",
            "scene_role_assignments": {"Ayame": "host", "Celina": "guard"},
            "audit_enabled": True,
            "audit_session_number": 7,
            "audit_round_number": 3,
            "audit_turn_number": 1,
            "scene_owner": "Ayame",
            "audit_session_owner": "Ayame",
            "opening_mode": "template",
            "selected_opener_id": "default",
            "custom_opener_text": "",
            "scene_status": "closed",
        },
        chat_history=[
            {"role": "system", "speaker": "Narrator", "content": "Saved opening"}
        ],
    )

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    monkeypatch.setattr(app, "SessionManager", lambda: manager)
    monkeypatch.setattr(
        app, "CharacterLoader", make_loader({"Ayame": "Ayame", "Celina": "Celina"})
    )
    monkeypatch.setattr(app, "resolve_character_file", lambda _loader, name: name)
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )

    await app.load_existing_session("saved_scene")

    assert session_state["session_id"] == "saved_scene"
    assert session_state["selected_scene_template_id"] == "household_entry_evaluation"
    assert session_state["scene_role_assignments"] == {
        "Ayame": "host",
        "Celina": "guard",
    }
    assert session_state["audit_enabled"] is True
    assert session_state["audit_session_number"] == 7
    assert session_state["audit_round_number"] == 3
    assert session_state["audit_turn_number"] == 1
    assert session_state["scene_owner"] == "Ayame"
    assert session_state["audit_session_owner"] == "Ayame"
    assert session_state["opening_mode"] == "template"
    assert session_state["scene_started"] is True
    assert session_state["scene_ended"] is False


@pytest.mark.asyncio
async def test_load_existing_session_unsets_noncanonical_opening_mode(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Invalid saved opening_mode (Issue #100) becomes unset — not coerced to 'character'."""
    init_fake_session(fake_streamlit)
    manager = SessionManager(tmp_path)
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            scene_template_id=None,
            scene_premise="",
            role_assignments={},
        )
    )
    manager.save_session(
        session_id="legacy_mode_scene",
        team_state={},
        characters=["Ayame"],
        metadata={
            "opening_mode": "pre_canonical_saved_value",
            "scene_status": "closed",
        },
        chat_history=[],
    )

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    monkeypatch.setattr(app, "SessionManager", lambda: manager)
    monkeypatch.setattr(
        app, "CharacterLoader", make_loader({"Ayame": "Ayame"})
    )
    monkeypatch.setattr(app, "resolve_character_file", lambda _loader, name: name)
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "load_cross_session_memories", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        app, "has_player_character_conflict", lambda *_a, **_k: False
    )

    await app.load_existing_session("legacy_mode_scene")

    om = fake_streamlit.session_state.get("opening_mode")
    assert om is None
    assert om != "character"


@pytest.mark.asyncio
async def test_load_existing_session_migrates_character_opening_mode_with_template(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Issue #108: saved ``character`` opener mode becomes ``template`` when a template id exists."""
    session_state = init_fake_session(fake_streamlit)
    manager = SessionManager(tmp_path)
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            scene_template_id="household_entry_evaluation",
            scene_premise="",
            role_assignments={},
        )
    )
    manager.save_session(
        session_id="mig_char_tpl",
        team_state={"scene_state": {"opening_description": "x"}},
        characters=["Ayame"],
        metadata={
            "scene_template_id": "household_entry_evaluation",
            "opening_mode": "character",
            "selected_opener_id": "legacy_pick",
            "scene_status": "closed",
        },
        chat_history=[],
    )

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    monkeypatch.setattr(app, "SessionManager", lambda: manager)
    monkeypatch.setattr(app, "CharacterLoader", make_loader({"Ayame": "Ayame"}))
    monkeypatch.setattr(app, "resolve_character_file", lambda _loader, name: name)
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "load_cross_session_memories", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        app, "has_player_character_conflict", lambda *_a, **_k: False
    )

    await app.load_existing_session("mig_char_tpl")

    assert session_state["opening_mode"] == "template"
    assert session_state["selected_opener_id"] is None


@pytest.mark.asyncio
async def test_load_existing_session_migrates_character_opening_mode_without_template(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Issue #108: saved ``character`` mode becomes ``custom`` when no template is selected."""
    session_state = init_fake_session(fake_streamlit)
    manager = SessionManager(tmp_path)
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            scene_template_id=None,
            scene_premise="",
            role_assignments={},
        )
    )
    manager.save_session(
        session_id="mig_char_custom",
        team_state={"scene_state": {"opening_description": "x"}},
        characters=["Ayame"],
        metadata={
            "opening_mode": "character",
            "selected_opener_id": "legacy_pick",
            "scene_status": "closed",
        },
        chat_history=[],
    )

    async def fake_shutdown_runtime_resources() -> None:
        return None

    async def fake_close_active_scene_if_needed(_reason: str) -> None:
        return None

    monkeypatch.setattr(app, "SessionManager", lambda: manager)
    monkeypatch.setattr(app, "CharacterLoader", make_loader({"Ayame": "Ayame"}))
    monkeypatch.setattr(app, "resolve_character_file", lambda _loader, name: name)
    monkeypatch.setattr(app, "create_deepseek_client", lambda: object())
    monkeypatch.setattr(app, "CharacterStateManager", FakeCharacterStateManager)
    monkeypatch.setattr(
        app, "apply_cross_session_memories", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        app,
        "restore_or_initialize_continuity_manager",
        lambda *_args, **_kwargs: continuity_manager,
    )
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(
        app, "shutdown_runtime_resources", fake_shutdown_runtime_resources
    )
    monkeypatch.setattr(
        app, "close_active_scene_if_needed", fake_close_active_scene_if_needed
    )
    monkeypatch.setattr(
        app, "load_cross_session_memories", lambda *_a, **_k: {}
    )
    monkeypatch.setattr(
        app, "has_player_character_conflict", lambda *_a, **_k: False
    )

    await app.load_existing_session("mig_char_custom")

    assert session_state["opening_mode"] == "custom"
    assert session_state["selected_opener_id"] is None


@pytest.mark.asyncio
async def test_save_current_session_persists_scene_template_and_audit_metadata(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    manager = SessionManager(tmp_path)
    continuity_manager = FakeContinuityManager(
        SimpleNamespace(
            scene_template_id="household_entry_evaluation",
            scene_premise="A guarded evaluation.",
            role_assignments={"Ayame": "host", "Celina": "guard"},
        )
    )
    session_state.update(
        {
            "session_id": "active_scene",
            "team_state": {"scene_state": {"opening_description": "Opening"}},
            "characters": [
                SimpleNamespace(name="Ayame"),
                SimpleNamespace(name="Celina"),
            ],
            "character_states": {
                "Ayame": DummyState("Ayame"),
                "Celina": DummyState("Celina"),
            },
            "chat_history": [{"role": "user", "speaker": "Alex", "content": "Hello"}],
            "scene_started": True,
            "audit_enabled": True,
            "audit_session_number": 4,
            "audit_round_number": 1,
            "audit_turn_number": 2,
            "scene_owner": "Ayame",
            "audit_session_owner": "Ayame",
            "bot_reply_limit": 2,
        }
    )

    monkeypatch.setattr(app, "SessionManager", lambda: manager)
    monkeypatch.setattr(app, "sync_orchestration_state_from_continuity", lambda: None)
    monkeypatch.setattr(app, "get_continuity_manager", lambda: continuity_manager)
    monkeypatch.setattr(
        app,
        "build_memory_buckets",
        lambda summary, _manager, _history, _user_name: {
            "session_summary": summary,
            "persistent_world_facts": [],
            "user_preferences": [],
        },
    )
    monkeypatch.setattr(app, "get_current_bot_reply_limit", lambda _count: 2)

    await app.save_current_session()

    saved = manager.load_session("active_scene")
    metadata = saved["metadata"]

    assert metadata["scene_template_id"] == "household_entry_evaluation"
    assert metadata["scene_role_assignments"] == {"Ayame": "host", "Celina": "guard"}
    assert metadata["audit_enabled"] is True
    assert metadata["audit_session_number"] == 4
    assert metadata["audit_session_owner"] == "Ayame"
    assert metadata["scene_status"] == "active"


def test_run_app_startup_smoke_recovers_sessions_and_loads_pending_session(
    fake_streamlit: FakeStreamlit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_state = init_fake_session(fake_streamlit)
    session_state["load_session_id"] = "saved_scene"
    loaded_session_ids: list[str] = []

    class FakeStartupSessionManager:
        def finalize_incomplete_sessions(self) -> list[str]:
            return ["recovered_scene"]

    async def fake_load_existing_session(session_id: str) -> None:
        loaded_session_ids.append(session_id)

    monkeypatch.setattr(app, "SessionManager", FakeStartupSessionManager)
    monkeypatch.setattr(app, "load_existing_session", fake_load_existing_session)

    app.run_app_startup()

    assert session_state["recovered_session_ids"] == ["recovered_scene"]
    assert session_state["startup_recovery_completed"] is True
    assert loaded_session_ids == ["saved_scene"]
    assert "load_session_id" not in session_state
