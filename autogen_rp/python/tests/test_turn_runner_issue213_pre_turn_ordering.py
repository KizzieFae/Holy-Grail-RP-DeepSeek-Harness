"""Issue #213: per-orchestration-turn pre-turn presence routing before eligibility (LLM-free).

Before #213, ``run_character_turns`` called ``apply_pre_turn_user_presence_routing`` only once
per user round using ``resolve_effective_user_trigger(1)``. With per-beat trigger schedules,
each Director turn must run pre-turn alignment using *this* beat's effective trigger before
``available_actors`` is computed.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner
from continuity_manager import ContinuityManager
from continuity_state import SceneState
from orchestration_helpers import append_turn_to_orchestration_state, ensure_orchestration_state
from response_validation_selection import get_available_actors
from user_trigger_schedule import make_resolve_effective_user_trigger


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {"pending_forced_speaker": None}

    def spinner(self, _message: str):
        return nullcontext()


class RecordingContinuityManager(ContinuityManager):
    """Records ``trigger_text`` passed into pre-turn routing (Issue #213 contract)."""

    def __init__(self) -> None:
        super().__init__()
        self.pre_turn_triggers: list[str] = []

    def apply_pre_turn_user_presence_routing(
        self,
        *,
        trigger_text: str,
        participant_names: list[str],
        get_character_display_name_fn: Callable[[str], str],
        pending_forced_speaker: str | None,
    ) -> None:
        self.pre_turn_triggers.append(trigger_text)
        return super().apply_pre_turn_user_presence_routing(
            trigger_text=trigger_text,
            participant_names=participant_names,
            get_character_display_name_fn=get_character_display_name_fn,
            pending_forced_speaker=pending_forced_speaker,
        )


@pytest.mark.asyncio
async def test_issue213_pre_turn_runs_per_beat_with_scheduled_trigger_before_eligibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each orchestration turn applies pre-turn routing with that turn's effective trigger."""
    st_module = FakeStreamlit()
    char_agents = [
        SimpleNamespace(name="Alice"),
        SimpleNamespace(name="Bob"),
        SimpleNamespace(name="Hannah"),
    ]
    orchestration_state = ensure_orchestration_state(None)

    manager = RecordingContinuityManager()
    manager.scene_state = SceneState(
        present_characters=["Alice", "Bob", "Hannah"],
        offstage_characters=[],
        role_assignments={"Alice": "a", "Bob": "b", "Hannah": "h"},
    )

    resolve_trigger = make_resolve_effective_user_trigger(
        {
            1: "turn_one_trigger",
            2: "turn_two_trigger",
            3: "turn_three_trigger",
        },
        cli_trigger_provided=False,
        cli_trigger_value="",
        json_default=None,
        built_in_fallback="fallback_should_not_run_in_this_test",
    )

    director_triggers: list[str] = []

    def get_orchestration_state_fn() -> dict[str, object]:
        return orchestration_state

    def start_audit_round_fn() -> int:
        return 1

    def resolve_bot_reply_limit_fn(_num_chars: int, _max_turns: int | None) -> int:
        return 3

    def get_current_bot_reply_limit_fn(_num_chars: int) -> int:
        return 3

    def set_audit_turn_fn(turn_number: int) -> int:
        return turn_number

    async def choose_next_actor_fn(**kwargs: object) -> dict[str, object]:
        director_triggers.append(str(kwargs.get("trigger_text") or ""))
        av = list(kwargs.get("available_actors") or [])
        return {
            "next_actor": av[0],
            "end_round": False,
            "reason": "test",
            "environment_event": "",
            "tension_shift": "",
        }

    def log_turn_failure_fn(**_kwargs: object) -> None:
        raise AssertionError("unexpected turn failure")

    def build_character_turn_prompt_fn(*_args: object, **_kwargs: object):
        return "", {}

    def parse_character_move_fn(_text: str):
        return (
            {
                "dialogue": "x",
                "action": "y",
                "motivation": {
                    "goal": "g",
                    "tactic": "t",
                    "emotional_driver": "e",
                    "risk_level": "low",
                },
            },
            "",
        )

    def is_audit_enabled_fn() -> bool:
        return False

    def get_audit_logger_fn():
        return None

    def get_audit_context_fn():
        return ("", 0, 0, 0)

    def get_scene_audit_logging_kwargs_fn(_scene_state):
        return {}

    def get_character_scene_audit_context_fn(_name, _ctx):
        return {}

    def get_continuity_manager_fn():
        return manager

    def get_model_client_fn():
        return object()

    def validate_bot_response_fn(*_a, **_kw):
        return True, ""

    async def assess_presence_violation_semantics_fn(*_a, **_kw):
        return None

    def should_override_presence_rejection_fn(*_a, **_kw):
        return False

    def build_recent_scene_context_fn(*_a, **_kw):
        return "", {}

    async def render_character_move_fn(*_a, **_kw):
        return "r", "nr", "np", False

    def fallback_render_move_fn(*_a, **_kw):
        return ""

    async def assess_narrator_render_semantics_fn(*_a, **_kw):
        return None

    def record_character_memories_fn(*_a, **_kw):
        return None

    def sync_orchestration_state_from_continuity_fn():
        return None

    def refresh_audit_summary_report_fn():
        return None

    async def reset_agents_fn(_agents, _token):
        return None

    def get_character_display_name_fn(name: str) -> str:
        return name

    def append_turn_to_orchestration_state_stub(**kwargs):
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

    async def execute_character_turn_stub(**kwargs):
        return {
            "move": {
                "dialogue": "x",
                "action": "y",
                "motivation": {
                    "goal": "g",
                    "tactic": "t",
                    "emotional_driver": "e",
                    "risk_level": "low",
                },
            },
            "rendered": "r",
            "narrator_raw": "nr",
            "narrator_prompt": "np",
            "narrator_summary_block_audit": None,
            "narrator_semantic_assessment": None,
            "narrator_output_audit_v1": {},
            "narrator_validation_audit_v1": {},
            "prose_dialogue_audit_v1": {},
            "audit_v2_narrator": None,
            "continuity_applied_in_execute": False,
        }

    monkeypatch.setattr(turn_runner, "execute_character_turn", execute_character_turn_stub)
    monkeypatch.setattr(
        turn_runner, "apply_successful_turn_updates", append_turn_to_orchestration_state_stub
    )

    await turn_runner.run_character_turns(
        st_module=st_module,
        char_agents=char_agents,
        narrator=object(),
        director=object(),
        trigger_text="unused_when_schedule_provided",
        user_name="User",
        max_turns=3,
        get_orchestration_state_fn=get_orchestration_state_fn,
        start_audit_round_fn=start_audit_round_fn,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit_fn,
        get_current_bot_reply_limit_fn=get_current_bot_reply_limit_fn,
        get_available_actors_fn=get_available_actors,
        set_audit_turn_fn=set_audit_turn_fn,
        choose_next_actor_fn=choose_next_actor_fn,
        log_turn_failure_fn=log_turn_failure_fn,
        build_character_turn_prompt_fn=build_character_turn_prompt_fn,
        parse_character_move_fn=parse_character_move_fn,
        is_audit_enabled_fn=is_audit_enabled_fn,
        is_llm_audit_enabled_fn=lambda: False,
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
        append_turn_to_orchestration_state_fn=append_turn_to_orchestration_state,
        spotlight_history_limit=10,
        structured_move_history_limit=10,
        director_decision_history_limit=10,
        environment_history_limit=10,
        tension_history_limit=10,
        ignore_director_end_round=False,
        get_effective_user_trigger=resolve_trigger,
    )

    expected = [resolve_trigger(i) for i in (1, 2, 3)]
    assert manager.pre_turn_triggers == expected, manager.pre_turn_triggers
    assert director_triggers == expected
