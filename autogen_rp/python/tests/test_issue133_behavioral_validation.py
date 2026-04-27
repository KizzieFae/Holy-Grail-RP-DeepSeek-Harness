"""Issue #133 behavioral validation: parse-retry lifecycle (controlled harness).

Session replay (e.g. session_663) is optional when audit JSON exists; this module
uses deterministic fakes to satisfy the validation criteria from the issue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from turn_runner_turn import _CHARACTER_MOVE_PARSE_JSON_DISCIPLINE_NOTE, execute_character_turn


async def _async_semantics_clean(**_kwargs):
    return {"valid": True, "should_use_fallback": False, "issues": []}


def _move_ok() -> dict:
    return {
        "action": "nodded",
        "dialogue": "Fine.",
        "motivation": {"goal": "x", "tactic": "y"},
    }


@pytest.mark.asyncio
async def test_issue133_malformed_then_valid_json_retry_lifecycle() -> None:
    """Goals 1–3 + 5 (success path): retry not forfeiture, same actor, decision, note, transcript."""
    session_state = {
        "chat_history": [],
        "selector_decisions": [],
    }
    st = SimpleNamespace(session_state=session_state)

    decision = {
        "next_actor": "Celina",
        "environment_event": "rain",
        "tension_shift": "low",
        "reason": "director-fixed-ref",
    }
    decision_id = id(decision)

    agent_prompts: list[str] = []
    failure_records: list[dict] = []

    class FakeAgent:
        async def on_messages(self, messages, _cancellation_token):
            agent_prompts.append(str(messages[0].content))
            if len(agent_prompts) == 1:
                return SimpleNamespace(
                    chat_message=SimpleNamespace(content='{"broken": true,}')
                )
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(_move_ok()))
            )

    def parse_fn(raw: str):
        if "broken" in raw or raw.strip().startswith("{"):
            try:
                return json.loads(raw), ""
            except json.JSONDecodeError:
                return None, "json decode error"
        return json.loads(raw), ""

    def log_failure(**kwargs) -> None:
        failure_records.append(dict(kwargs))

    actors_failed: list[str] = []

    async def fake_render(*_a, **_k):
        return (
            'Celina nodded.\n\n"Fine."',
            'Celina nodded.\n\n"Fine."',
            "np",
            False,
        )

    result = await execute_character_turn(
        st_module=st,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision=decision,
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=actors_failed,
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("BASE_PROMPT", {"prompt_evaluations": 0}),
        parse_character_move_fn=parse_fn,
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_a, **_k: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render,
        fallback_render_move_fn=lambda *_a, **_k: "fallback",
        assess_narrator_render_semantics_fn=_async_semantics_clean,
        log_turn_failure_fn=log_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert len(agent_prompts) == 2
    assert agent_prompts[0] == "BASE_PROMPT"
    assert _CHARACTER_MOVE_PARSE_JSON_DISCIPLINE_NOTE in agent_prompts[1]
    assert "BASE_PROMPT" in agent_prompts[1]

    assert actors_failed == []
    assert len(session_state["chat_history"]) == 1

    stages = [r.get("stage") for r in failure_records]
    assert stages == ["parse_retry"]
    assert id(failure_records[0].get("parsed_output")) == decision_id

    meta = result["turn_execution_metadata"]
    assert meta["parse_retry_triggered"] is True
    assert meta["parse_retry_outcome"] == "success_after_retry"
    assert meta.get("parse_retry_reason")


@pytest.mark.asyncio
async def test_issue133_chat_history_not_mutated_until_successful_pipeline() -> None:
    """Goal 3: no transcript append before successful parse + validation + render path."""
    session_state = {
        "chat_history": [],
        "selector_decisions": [],
    }
    st = SimpleNamespace(session_state=session_state)
    calls: list[int] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                return SimpleNamespace(chat_message=SimpleNamespace(content="NOT_JSON"))
            assert len(session_state["chat_history"]) == 0
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(_move_ok()))
            )

    def parse_fn(raw: str):
        if raw == "NOT_JSON":
            assert len(session_state["chat_history"]) == 0
            return None, "nope"
        assert len(session_state["chat_history"]) == 0
        return json.loads(raw), ""

    async def fake_render(*_a, **_k):
        return ("r", "r", "p", False)

    await execute_character_turn(
        st_module=st,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={"next_actor": "Celina", "environment_event": "", "tension_shift": "", "reason": "t"},
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("p", {"prompt_evaluations": 0}),
        parse_character_move_fn=parse_fn,
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda *_name, _scene: {},
        validate_bot_response_fn=lambda *_a, **_k: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: ("ctx", {"prompt_evaluations": 0}),
        render_character_move_fn=fake_render,
        fallback_render_move_fn=lambda *_a, **_k: "f",
        assess_narrator_render_semantics_fn=_async_semantics_clean,
        log_turn_failure_fn=lambda **_k: None,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert len(session_state["chat_history"]) == 1


@pytest.mark.asyncio
async def test_issue133_terminal_exhaustion_stages_and_forfeiture() -> None:
    """Goals 4–5 (exhaustion): actors_failed only after final parse; parse_retry then parse."""
    from turn_runner_turn import DEFAULT_MAX_CHARACTER_ATTEMPTS

    session_state = {"chat_history": [], "selector_decisions": []}
    st = SimpleNamespace(session_state=session_state)
    failures: list[tuple[str, str]] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(chat_message=SimpleNamespace(content="x"))

    def log_failure(**kwargs) -> None:
        failures.append((str(kwargs.get("stage", "")), str(kwargs.get("reason", ""))))

    actors_failed: list[str] = []
    result = await execute_character_turn(
        st_module=st,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Marlene_Fletcher",
        char_names=["Marlene_Fletcher"],
        decision={"next_actor": "Marlene_Fletcher", "environment_event": "", "tension_shift": "", "reason": "t"},
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=2,
        turn_number=3,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=actors_failed,
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("p", {"prompt_evaluations": 0}),
        parse_character_move_fn=lambda _r: (None, "invalid structured move"),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_a, **_k: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: ("ctx", {"prompt_evaluations": 0}),
        render_character_move_fn=lambda *_a, **_k: ("r", "r", "p", False),
        fallback_render_move_fn=lambda *_a, **_k: "f",
        assess_narrator_render_semantics_fn=_async_semantics_clean,
        log_turn_failure_fn=log_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is None
    assert actors_failed == ["Marlene_Fletcher"]
    assert failures.count(("parse_retry", "invalid structured move")) == DEFAULT_MAX_CHARACTER_ATTEMPTS - 1
    assert failures[-1] == ("parse", "invalid structured move")
    assert session_state["chat_history"] == []


@pytest.mark.asyncio
async def test_issue133_audit_metadata_parse_retry_fields() -> None:
    """Goal 5: character audit row carries turn_execution parse_retry_* after recovery."""
    session_state = {"chat_history": [], "selector_decisions": []}
    st = SimpleNamespace(session_state=session_state)
    audit_entries: list[dict] = []

    call_box = {"n": 0}

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            call_box["n"] += 1
            if call_box["n"] == 1:
                return SimpleNamespace(chat_message=SimpleNamespace(content="```json\noops"))
            return SimpleNamespace(chat_message=SimpleNamespace(content=json.dumps(_move_ok())))

    class CapturingAuditLogger:
        def create_entry(self, **kwargs):
            return kwargs

        def log_bot_interaction(self, entry):
            audit_entries.append(entry)

    def parse_fn(raw: str):
        if raw.startswith("```"):
            return None, "fenced prose"
        return json.loads(raw), ""

    async def fake_render(*_a, **_k):
        return ("r", "r", "p", False)

    await execute_character_turn(
        st_module=st,
        agent=FakeAgent(),
        narrator=object(),
        next_actor="Celina",
        char_names=["Celina"],
        decision={"next_actor": "Celina", "environment_event": "", "tension_shift": "", "reason": "t"},
        trigger_text="test",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=1,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("p", {"prompt_evaluations": 0}),
        parse_character_move_fn=parse_fn,
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: True,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: CapturingAuditLogger(),
        get_audit_context_fn=lambda: ("Owner", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=lambda *_a, **_k: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: ("ctx", {"prompt_evaluations": 0}),
        render_character_move_fn=fake_render,
        fallback_render_move_fn=lambda *_a, **_k: "f",
        assess_narrator_render_semantics_fn=_async_semantics_clean,
        log_turn_failure_fn=lambda **_k: None,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert len(audit_entries) == 1
    turn_ex = audit_entries[0].get("metadata", {}).get("turn_execution", {})
    assert turn_ex.get("parse_retry_triggered") is True
    assert turn_ex.get("parse_retry_outcome") == "success_after_retry"
    assert turn_ex.get("parse_retry_reason")
