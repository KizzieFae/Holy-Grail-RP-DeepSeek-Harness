"""Unit tests for assignment:sleeping_surface binding enforcement (issue #30)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from response_validation_binding_sleeping_surface import (
    BINDING_RETRY_BLOCK_TEMPLATE,
    format_binding_sleeping_surface_retry_note,
    validate_binding_sleeping_surface_contradiction,
)
from response_validation_content import validate_bot_response
from turn_runner_turn import execute_character_turn


class _MiniStreamlit:
    __slots__ = ("session_state",)

    def __init__(self, session_state: dict) -> None:
        self.session_state = session_state


def _mini_st_with_grounding(scene_grounding: dict) -> _MiniStreamlit:
    return _MiniStreamlit(
        {
            "chat_history": [],
            "selector_decisions": [],
            "scene_grounding": scene_grounding,
        }
    )


def _grounding_fact(assignee: str, surface: str) -> dict:
    return {
        "fact_id": "t1",
        "category": "assignment",
        "key": "sleeping_surface",
        "value": {"assignee": assignee, "surface": surface},
        "value_summary": f"{assignee}: sleeping — {surface}",
        "source": {"kind": "resolved_outcome", "ref": "x"},
        "priority": 80,
        "supersedes": None,
        "source_turn_index": 1,
    }


def _scene_state_slots() -> dict:
    return {"sleeping_surface_slots": ["bunk_a", "couch"]}


class TestMustTriggerDenial:
    def test_never_assigned_bunk(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "I was never assigned a bunk.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert msg.startswith("[BINDING_SLEEPING_SURFACE]")
        assert "denial_of_assignment_existence" in msg

    def test_nobody_gave_bed(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {
            "dialogue": "Nobody gave me a bed; I'm making do on the floor.",
            "action": "",
        }
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert "denial_of_assignment_existence" in msg

    def test_no_sleeping_assignment_here(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "I don't have a sleeping assignment here.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert "denial_of_assignment_existence" in msg

    def test_no_bunk_with_my_name(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {
            "dialogue": "There's no bunk with my name on it—they skipped me.",
            "action": "",
        }
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert "denial_of_assignment_existence" in msg

    def test_nobody_gave_sleeping_spot(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "Nobody gave me a sleeping spot.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert "denial_of_assignment_existence" in msg


class TestMustTriggerIncorrectReassignment:
    def test_my_assignment_is_couch_not_bunk(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {
            "dialogue": "My assignment is the couch, not the bunk.",
            "action": "",
        }
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False
        assert "incorrect_reassignment_assertion" in msg


class TestMustNotTrigger:
    def test_refuse_to_sleep_there(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {
            "dialogue": "I don't care what they said, I'm not sleeping there.",
            "action": "",
        }
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True
        assert msg == ""

    def test_bullshit_bunk(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "This bunk is bullshit, but fine.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_call_housing(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "I'll call housing and get this changed.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_why_stick_me_here(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "Why did they stick me here?", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_rather_take_couch(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "I'd rather take the couch.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_negated_couch_not_assignment(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {
            "dialogue": "My assignment is the bunk, not the couch.",
            "action": "",
        }
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True


class TestTriggerConditions:
    def test_no_binding_skips(self) -> None:
        g = {"schema_version": 1, "facts": []}
        move = {"dialogue": "I was never assigned a bunk.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_binding_for_other_actor_skips(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("ayame", "bunk_a")]}
        move = {"dialogue": "I was never assigned a bunk.", "action": ""}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is True

    def test_action_contributes(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "", "action": "She muttered that she was never assigned a bunk."}
        ok, msg = validate_binding_sleeping_surface_contradiction(
            move=move,
            speaker="celina",
            scene_grounding=g,
            scene_state=_scene_state_slots(),
            continuity_manager=None,
        )
        assert ok is False


class TestValidateBotResponseIntegration:
    def test_prefix_on_fail(self) -> None:
        g = {"schema_version": 1, "facts": [_grounding_fact("celina", "bunk_a")]}
        move = {"dialogue": "I was never assigned a bunk.", "action": ""}
        ok, msg = validate_bot_response(
            "i was never assigned a bunk",
            "celina",
            "Alex",
            [],
            None,
            move,
            None,
            _scene_state_slots(),
            None,
            scene_grounding=g,
        )
        assert ok is False
        assert msg.startswith("[BINDING_SLEEPING_SURFACE]")


class TestRetryTemplate:
    def test_format_matches_spec(self) -> None:
        note = format_binding_sleeping_surface_retry_note("bunk_a")
        expected = BINDING_RETRY_BLOCK_TEMPLATE.format(surface_id="bunk_a")
        assert note == expected
        assert len(note) <= 400


@pytest.mark.asyncio
async def test_execute_character_turn_binding_retry_once_then_hard_fail() -> None:
    sg = {"schema_version": 1, "facts": [_grounding_fact("Celina", "bunk_a")]}
    orch = {"scene_state": {"sleeping_surface_slots": ["bunk_a", "couch"]}}
    fake_streamlit = _mini_st_with_grounding(sg)
    failures: list[tuple[str, str]] = []
    agent_calls: list[str] = []

    move_bad = {
        "action": "shrugged",
        "dialogue": "I was never assigned a bunk.",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_bad_again = {
        "action": "shrugged",
        "dialogue": "Nobody gave me a bed.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append("called")
            n = len(agent_calls)
            payload = json.dumps(move_bad if n == 1 else move_bad_again)
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

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
        orchestration_state=orch,
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("prompt", {"prompt_evaluations": 0}),
        parse_character_move_fn=lambda raw: (json.loads(raw), ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=validate_bot_response,
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_a, **_k: "fallback",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is None
    assert len(agent_calls) == 2
    assert any(s == "validation_binding_retry" for s, _ in failures)
    assert any(
        r.startswith("[BINDING_SLEEPING_SURFACE]") for _, r in failures if r
    )
    assert any(s == "validation" for s, _ in failures)


@pytest.mark.asyncio
async def test_execute_character_turn_binding_retry_succeeds_second_attempt() -> None:
    sg = {"schema_version": 1, "facts": [_grounding_fact("Celina", "bunk_a")]}
    orch = {"scene_state": {"sleeping_surface_slots": ["bunk_a", "couch"]}}
    fake_streamlit = _mini_st_with_grounding(sg)
    failures: list[tuple[str, str]] = []
    agent_calls: list[str] = []

    move_bad = {
        "action": "shrugged",
        "dialogue": "I was never assigned a bunk.",
        "motivation": {"goal": "x", "tactic": "y"},
    }
    move_ok = {
        "action": "exhaled",
        "dialogue": "This bunk is bullshit, but fine.",
        "motivation": {"goal": "x", "tactic": "y"},
    }

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls.append("called")
            payload = json.dumps(move_bad if len(agent_calls) == 1 else move_ok)
            return SimpleNamespace(chat_message=SimpleNamespace(content=payload))

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
        orchestration_state=orch,
        actors_failed_this_round=[],
        state_manager=None,
        build_character_turn_prompt_fn=lambda *_a, **_k: ("prompt", {"prompt_evaluations": 0}),
        parse_character_move_fn=lambda raw: (json.loads(raw), ""),
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: False,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("Ayame", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _scene: {},
        get_character_scene_audit_context_fn=lambda _name, _scene: {},
        validate_bot_response_fn=validate_bot_response,
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=lambda **_kwargs: None,
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        build_recent_scene_context_fn=lambda *_a, **_k: (
            "scene context",
            {"prompt_evaluations": 0},
        ),
        render_character_move_fn=fake_render_character_move,
        fallback_render_move_fn=lambda *_a, **_k: "fallback",
        assess_narrator_render_semantics_fn=fake_assess_narrator_render_semantics,
        log_turn_failure_fn=fake_log_turn_failure,
        get_character_display_name_fn=lambda name: name,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )

    assert result is not None
    assert len(agent_calls) == 2
    assert result["turn_execution_metadata"]["binding_retry_triggered"] is True
    assert (
        result["turn_execution_metadata"]["binding_retry_outcome"] == "success_after_retry"
    )
    assert any(s == "validation_binding_retry" for s, _ in failures)
