from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner
from orchestration_helpers import append_turn_to_orchestration_state, ensure_orchestration_state


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}

    def spinner(self, _message: str):
        return nullcontext()


class FakeContinuityManager:
    def __init__(self, present_characters: list[str]) -> None:
        self.turn_counter = 0
        self.turn_metadata_by_index: dict[int, dict[str, object]] = {}
        self.scene_state = SimpleNamespace(present_characters=present_characters)

    def get_active_issues(self, limit: int = 24) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_continuation_override_does_not_bypass_used_actor_restriction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_module = FakeStreamlit()

    char_agents = [SimpleNamespace(name="A"), SimpleNamespace(name="B")]

    orchestration_state = ensure_orchestration_state(None)
    continuity_manager = FakeContinuityManager(["A", "B"])

    call_snapshots: list[dict[str, object]] = []

    def get_orchestration_state_fn() -> dict[str, object]:
        return orchestration_state

    def start_audit_round_fn() -> int:
        return 1

    def resolve_bot_reply_limit_fn(_num_chars: int, _max_turns: int | None) -> int:
        return 2

    def get_current_bot_reply_limit_fn(_num_chars: int) -> int:
        return 2

    def get_available_actors_fn(
        participant_names: list[str],
        used_actors: list[str],
        eligible_participants: list[str] | None,
        offstage_characters: list[str] | None = None,
    ) -> list[str]:
        used = set(used_actors)
        eligible = set(eligible_participants or participant_names)
        off = set(offstage_characters or [])
        return [
            name
            for name in participant_names
            if name not in used and name in eligible and name not in off
        ]

    def set_audit_turn_fn(turn_number: int) -> int:
        return turn_number

    async def choose_next_actor_fn(**kwargs) -> dict[str, object]:
        call_snapshots.append(
            {
                "available_actors": list(kwargs.get("available_actors", [])),
                "continuation_override_actor": kwargs.get("continuation_override_actor"),
            }
        )
        available_actors = list(kwargs.get("available_actors", []))
        return {
            "next_actor": available_actors[0] if available_actors else "",
            "end_round": False,
            "reason": "test",
            "environment_event": "",
            "tension_shift": "",
        }

    def log_turn_failure_fn(**_kwargs) -> None:
        raise AssertionError("turn selection should not fail in this test")

    def build_character_turn_prompt_fn(*_args, **_kwargs):
        return "", {}

    def parse_character_move_fn(_text: str):
        return None, ""

    def is_audit_enabled_fn() -> bool:
        return False

    def get_audit_logger_fn():
        return None

    def get_audit_context_fn():
        return "", 0, 0, 0

    def get_scene_audit_logging_kwargs_fn(_continuity_event):
        return {}

    def get_character_scene_audit_context_fn(_name: str, _decision):
        return {}

    def get_continuity_manager_fn():
        return continuity_manager

    def get_model_client_fn():
        return None

    def validate_bot_response_fn(**_kwargs):
        return True, ""

    async def assess_presence_violation_semantics_fn(**_kwargs):
        return None

    def should_override_presence_rejection_fn(*_args, **_kwargs) -> bool:
        return False

    def build_recent_scene_context_fn(_messages, _state):
        return "", {}

    async def render_character_move_fn(**_kwargs):
        return "", "", ""

    def fallback_render_move_fn(*_args, **_kwargs) -> str:
        return ""

    async def assess_narrator_render_semantics_fn(**_kwargs):
        return None

    def record_character_memories_fn(*_args, **_kwargs) -> None:
        return None

    def sync_orchestration_state_from_continuity_fn() -> None:
        return None

    def refresh_audit_summary_report_fn() -> None:
        return None

    async def reset_agents_fn(_agents, _token) -> None:
        return None

    def get_character_display_name_fn(name: str) -> str:
        return name

    def append_turn_to_orchestration_state_fn(**kwargs):
        return append_turn_to_orchestration_state(**kwargs)

    async def execute_character_turn_stub(**kwargs) -> dict[str, object]:
        actor = str(kwargs.get("next_actor"))
        return {
            "move": {"action": "acted", "dialogue": "", "motivation": {"goal": "x", "tactic": "y"}},
            "rendered": "",
            "narrator_raw": "",
            "narrator_prompt": "",
            "narrator_summary_block_audit": None,
            "narrator_semantic_assessment": None,
        }

    def apply_successful_turn_updates_stub(**kwargs):
        nonlocal orchestration_state
        orchestration_state = append_turn_to_orchestration_state(
            orchestration_state=kwargs["orchestration_state"],
            next_actor=kwargs["next_actor"],
            move=kwargs["move"],
            decision=kwargs["decision"],
            spotlight_history_limit=10,
            structured_move_history_limit=10,
            director_decision_history_limit=10,
            environment_history_limit=10,
            tension_history_limit=10,
        )
        return orchestration_state

    monkeypatch.setattr(turn_runner, "execute_character_turn", execute_character_turn_stub)
    monkeypatch.setattr(turn_runner, "apply_successful_turn_updates", apply_successful_turn_updates_stub)

    await turn_runner.run_character_turns(
        st_module=st_module,
        char_agents=char_agents,
        narrator=object(),
        director=object(),
        trigger_text="",
        user_name="User",
        max_turns=2,
        get_orchestration_state_fn=get_orchestration_state_fn,
        start_audit_round_fn=start_audit_round_fn,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit_fn,
        get_current_bot_reply_limit_fn=get_current_bot_reply_limit_fn,
        get_available_actors_fn=get_available_actors_fn,
        set_audit_turn_fn=set_audit_turn_fn,
        choose_next_actor_fn=choose_next_actor_fn,
        log_turn_failure_fn=log_turn_failure_fn,
        build_character_turn_prompt_fn=build_character_turn_prompt_fn,
        parse_character_move_fn=parse_character_move_fn,
        is_audit_enabled_fn=is_audit_enabled_fn,
        get_audit_logger_fn=get_audit_logger_fn,
        get_audit_context_fn=get_audit_context_fn,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
        get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
        get_continuity_manager_fn=get_continuity_manager_fn,
        get_model_client_fn=get_model_client_fn,
        validate_bot_response_fn=validate_bot_response_fn,
        assess_presence_violation_semantics_fn=assess_presence_violation_semantics_fn,
        should_override_presence_rejection_fn=should_override_presence_rejection_fn,
        build_recent_scene_context_fn=build_recent_scene_context_fn,
        render_character_move_fn=render_character_move_fn,
        fallback_render_move_fn=fallback_render_move_fn,
        assess_narrator_render_semantics_fn=assess_narrator_render_semantics_fn,
        record_character_memories_fn=record_character_memories_fn,
        sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity_fn,
        refresh_audit_summary_report_fn=refresh_audit_summary_report_fn,
        reset_agents_fn=reset_agents_fn,
        get_character_display_name_fn=get_character_display_name_fn,
        append_turn_to_orchestration_state_fn=append_turn_to_orchestration_state_fn,
        spotlight_history_limit=10,
        structured_move_history_limit=10,
        director_decision_history_limit=10,
        environment_history_limit=10,
        tension_history_limit=10,
    )

    assert len(call_snapshots) == 2

    first_call = call_snapshots[0]
    second_call = call_snapshots[1]

    assert first_call["available_actors"] == ["A", "B"]
    assert first_call["continuation_override_actor"] is None

    assert second_call["continuation_override_actor"] == "A"
    assert second_call["available_actors"] == ["B"]
