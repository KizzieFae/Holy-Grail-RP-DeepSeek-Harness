"""Character turn attempt budget: parse recovery + unified max attempts (Issue #133)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from turn_runner_turn import DEFAULT_MAX_CHARACTER_ATTEMPTS, execute_character_turn


async def _async_semantics_clean(**_kwargs):
    return {"valid": True, "should_use_fallback": False, "issues": []}


class _MiniStreamlit:
    __slots__ = ("session_state",)

    def __init__(self, session_state: dict) -> None:
        self.session_state = session_state


def _mini_st() -> _MiniStreamlit:
    return _MiniStreamlit(
        {
            "chat_history": [],
            "selector_decisions": [],
        }
    )


def _move_ok() -> dict:
    return {
        "action": "nodded",
        "dialogue": "Fine.",
        "motivation": {"goal": "x", "tactic": "y"},
    }


async def _fake_render_character_move(*args, **_kwargs):
    move = args[2]
    rendered = f'{args[1]} {move["action"]}.\n\n"{move["dialogue"]}"'
    return (rendered, rendered, "prompt", False)


def _base_execute_kwargs(
    *,
    fake_streamlit: _MiniStreamlit,
    agent,
    parse_character_move_fn,
    validate_bot_response_fn,
    log_turn_failure_fn,
    actors_failed: list[str],
) -> dict:
    return {
        "st_module": fake_streamlit,
        "agent": agent,
        "narrator": object(),
        "next_actor": "Celina",
        "char_names": ["Celina"],
        "decision": {
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "",
            "reason": "test",
        },
        "trigger_text": "test",
        "user_name": "Alex",
        "cancellation_token": object(),
        "round_number": 1,
        "turn_number": 1,
        "orchestration_state": {"scene_state": {}},
        "actors_failed_this_round": actors_failed,
        "state_manager": None,
        "build_character_turn_prompt_fn": lambda *_a, **_k: ("prompt", {"prompt_evaluations": 0}),
        "parse_character_move_fn": parse_character_move_fn,
        "get_continuity_manager_fn": lambda: None,
        "is_audit_enabled_fn": lambda: False,
        "is_llm_audit_enabled_fn": lambda: False,
        "get_audit_logger_fn": lambda: None,
        "get_audit_context_fn": lambda: ("Ayame", 1, 1, 1),
        "get_scene_audit_logging_kwargs_fn": lambda _scene: {},
        "get_character_scene_audit_context_fn": lambda _name, _scene: {},
        "validate_bot_response_fn": validate_bot_response_fn,
        "get_model_client_fn": lambda: object(),
        "assess_presence_violation_semantics_fn": lambda **_kwargs: None,
        "should_override_presence_rejection_fn": lambda *_a, **_k: False,
        "build_recent_scene_context_fn": lambda *_a, **_k: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        "render_character_move_fn": _fake_render_character_move,
        "fallback_render_move_fn": lambda *_a, **_k: "fallback",
        "assess_narrator_render_semantics_fn": _async_semantics_clean,
        "log_turn_failure_fn": log_turn_failure_fn,
        "get_character_display_name_fn": lambda name: name,
        "sync_orchestration_state_from_continuity_fn": lambda: None,
    }


@pytest.mark.asyncio
async def test_parse_retry_then_succeeds_without_actors_failed() -> None:
    st = _mini_st()
    failures: list[tuple[str, str]] = []
    agent_calls: list[int] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append(1)
            if len(agent_calls) == 1:
                return SimpleNamespace(chat_message=SimpleNamespace(content="NOT_JSON"))
            return SimpleNamespace(
                chat_message=SimpleNamespace(content=json.dumps(_move_ok()))
            )

    def parse_fn(raw: str):
        if raw == "NOT_JSON":
            return None, "expected object"
        return json.loads(raw), ""

    def fake_log(**kwargs) -> None:
        failures.append((str(kwargs.get("stage", "")), str(kwargs.get("reason", ""))))

    actors_failed: list[str] = []
    result = await execute_character_turn(
        **{
            **_base_execute_kwargs(
                fake_streamlit=st,
                agent=FakeAgent(),
                parse_character_move_fn=parse_fn,
                validate_bot_response_fn=lambda *_a, **_k: (True, ""),
                log_turn_failure_fn=fake_log,
                actors_failed=actors_failed,
            ),
        }
    )

    assert result is not None
    assert len(agent_calls) == 2
    assert actors_failed == []
    assert any(s == "parse_retry" for s, _ in failures)
    meta = result["turn_execution_metadata"]
    assert meta["parse_retry_triggered"] is True
    assert meta["parse_retry_outcome"] == "success_after_retry"
    assert meta["attempt_index"] == 1
    assert any("parse failure" in x.lower() for x in st.session_state["selector_decisions"])


@pytest.mark.asyncio
async def test_parse_exhausted_after_default_attempt_cap() -> None:
    st = _mini_st()
    failures: list[tuple[str, str]] = []

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            return SimpleNamespace(chat_message=SimpleNamespace(content="garbage"))

    def fake_log(**kwargs) -> None:
        failures.append((str(kwargs.get("stage", "")), str(kwargs.get("reason", ""))))

    actors_failed: list[str] = []
    result = await execute_character_turn(
        **{
            **_base_execute_kwargs(
                fake_streamlit=st,
                agent=FakeAgent(),
                parse_character_move_fn=lambda _raw: (None, "no json"),
                validate_bot_response_fn=lambda *_a, **_k: (True, ""),
                log_turn_failure_fn=fake_log,
                actors_failed=actors_failed,
            ),
        }
    )

    assert result is None
    assert actors_failed == ["Celina"]
    assert failures.count(("parse_retry", "no json")) == DEFAULT_MAX_CHARACTER_ATTEMPTS - 1
    assert failures[-1][0] == "parse"
    assert failures[-1][1] == "no json"


@pytest.mark.asyncio
async def test_parse_retry_then_duplicate_retry_then_success() -> None:
    st = _mini_st()
    agent_calls: list[int] = []

    move_dup = {
        "action": "waited",
        "dialogue": "Same line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_ok = {
        "action": "sighed",
        "dialogue": "Different line.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append(1)
            n = len(agent_calls)
            if n == 1:
                payload = "NOT_JSON"
            elif n == 2:
                payload = json.dumps(move_dup)
            else:
                payload = json.dumps(move_ok)
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

    def parse_fn(raw: str):
        if raw == "NOT_JSON":
            return None, "bad"
        return json.loads(raw), ""

    def validate_fn(content, *_a, **_k):
        if "Same line." in str(content):
            return False, "[DUPLICATE] repeated"
        return True, ""

    result = await execute_character_turn(
        **{
            **_base_execute_kwargs(
                fake_streamlit=st,
                agent=FakeAgent(),
                parse_character_move_fn=parse_fn,
                validate_bot_response_fn=validate_fn,
                log_turn_failure_fn=lambda **_k: None,
                actors_failed=[],
            ),
        }
    )

    assert result is not None
    assert len(agent_calls) == 3
    meta = result["turn_execution_metadata"]
    assert meta["parse_retry_triggered"] is True
    assert meta["duplicate_retry_triggered"] is True
    assert meta["attempt_index"] == 2


@pytest.mark.asyncio
async def test_duplicate_only_one_continue_even_with_extra_attempt_budget() -> None:
    st = _mini_st()
    agent_calls: list[int] = []

    move_a = {
        "action": "a",
        "dialogue": "dup line",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_b = {
        "action": "b",
        "dialogue": "dup line",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append(1)
            n = len(agent_calls)
            if n <= 2:
                payload = json.dumps(move_a if n == 1 else move_b)
            else:
                payload = json.dumps(_move_ok())
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

    def validate_fn(content, *_a, **_k):
        if "dup line" in str(content):
            return False, "[DUPLICATE] same"
        return True, ""

    actors_failed: list[str] = []
    result = await execute_character_turn(
        **{
            **_base_execute_kwargs(
                fake_streamlit=st,
                agent=FakeAgent(),
                parse_character_move_fn=lambda raw: (json.loads(raw), ""),
                validate_bot_response_fn=validate_fn,
                log_turn_failure_fn=lambda **_k: None,
                actors_failed=actors_failed,
            ),
            "max_character_attempts": 5,
        }
    )

    assert result is None
    assert len(agent_calls) == 2
    assert actors_failed == ["Celina"]
