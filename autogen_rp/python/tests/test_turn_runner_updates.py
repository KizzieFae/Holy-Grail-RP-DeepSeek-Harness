from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner_updates


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}


class RaisingContinuityManager:
    def __init__(self) -> None:
        self.scene_state = SimpleNamespace()
        self.turn_counter = 0
        self.turn_metadata_by_index: dict[int, dict[str, object]] = {}

    def process_turn(self, **_kwargs) -> None:
        raise RuntimeError("continuity exploded")


def _unexpected_call(*_args, **_kwargs):
    raise AssertionError("unexpected call after continuity failure")


def test_apply_successful_turn_updates_propagates_continuity_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_module = FakeStreamlit()
    continuity_manager = RaisingContinuityManager()
    st_module.session_state["continuity_manager"] = continuity_manager

    grounding_calls: list[str] = []
    append_calls: list[str] = []

    def fake_rebuild_scene_grounding_from_continuity(_manager):
        grounding_calls.append("called")
        return {"schema_version": 1, "facts": [], "last_rebuilt_turn": 0}

    def fake_append_turn_to_orchestration_state_fn(**kwargs):
        append_calls.append("called")
        return kwargs["orchestration_state"]

    monkeypatch.setattr(
        turn_runner_updates,
        "rebuild_scene_grounding_from_continuity",
        fake_rebuild_scene_grounding_from_continuity,
    )

    with pytest.raises(RuntimeError, match="continuity exploded"):
        turn_runner_updates.apply_successful_turn_updates(
            st_module=st_module,
            next_actor="Kizzie",
            char_names=["Kizzie", "Celina"],
            move={
                "action": "steps back",
                "dialogue": "",
                "motivation": {
                    "goal": "leave space",
                    "tactic": "retreat",
                    "emotional_driver": "fear",
                    "risk_level": "low",
                },
            },
            decision={
                "next_actor": "Kizzie",
                "reason": "test",
                "environment_event": "",
                "tension_shift": "",
            },
            rendered="",
            narrator_raw="",
            narrator_prompt="",
            narrator_summary_block_audit={},
            narrator_semantic_assessment=None,
            round_number=1,
            turn_number=1,
            state_manager=None,
            record_character_memories_fn=lambda *_args, **_kwargs: None,
            sync_orchestration_state_from_continuity_fn=_unexpected_call,
            is_audit_enabled_fn=lambda: False,
            get_audit_logger_fn=lambda: None,
            get_audit_context_fn=lambda: ("", 0, 0, 0),
            get_scene_audit_logging_kwargs_fn=lambda _event: {},
            get_character_scene_audit_context_fn=lambda _name, _decision: {},
            append_turn_to_orchestration_state_fn=fake_append_turn_to_orchestration_state_fn,
            orchestration_state={"scene_state": {}},
            spotlight_history_limit=10,
            structured_move_history_limit=10,
            director_decision_history_limit=10,
            environment_history_limit=10,
            tension_history_limit=10,
        )

    assert grounding_calls == []
    assert append_calls == []
    assert "scene_grounding" not in st_module.session_state
    assert "team_state" not in st_module.session_state


class SkipProcessTurnContinuityManager:
    """Continuity already updated in execute_character_turn; process_turn must not run."""

    def __init__(self) -> None:
        self.scene_state = SimpleNamespace()
        self.turn_counter = 2
        self.turn_metadata_by_index: dict[int, dict[str, object]] = {
            2: {"consequences": ["revelation"]},
        }
        self.issues: dict[str, object] = {}

    def process_turn(self, **_kwargs) -> None:
        raise AssertionError("process_turn should be skipped when flag is set")


def test_apply_successful_turn_updates_skips_process_turn_when_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_module = FakeStreamlit()
    continuity_manager = SkipProcessTurnContinuityManager()
    st_module.session_state["continuity_manager"] = continuity_manager
    sync_calls = 0

    def sync_fn() -> None:
        nonlocal sync_calls
        sync_calls += 1

    monkeypatch.setattr(
        turn_runner_updates,
        "rebuild_scene_grounding_from_continuity",
        lambda _m: {"schema_version": 1, "facts": [], "last_rebuilt_turn": 0},
    )

    turn_runner_updates.apply_successful_turn_updates(
        st_module=st_module,
        next_actor="Kizzie",
        char_names=["Kizzie", "Celina"],
        move={
            "action": "nods",
            "dialogue": "Yes.",
            "motivation": {"goal": "agree", "tactic": "simple", "risk_level": "low"},
        },
        decision={
            "next_actor": "Kizzie",
            "reason": "test",
            "environment_event": "",
            "tension_shift": "",
        },
        rendered="Kizzie nodded.",
        narrator_raw="raw",
        narrator_prompt="np",
        narrator_summary_block_audit={},
        narrator_semantic_assessment=None,
        round_number=1,
        turn_number=1,
        state_manager=None,
        record_character_memories_fn=lambda *_a, **_k: None,
        sync_orchestration_state_from_continuity_fn=sync_fn,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda _e: {},
        get_character_scene_audit_context_fn=lambda _n, _d: {},
        append_turn_to_orchestration_state_fn=lambda **kw: kw["orchestration_state"],
        orchestration_state={"scene_state": {}},
        spotlight_history_limit=10,
        structured_move_history_limit=10,
        director_decision_history_limit=10,
        environment_history_limit=10,
        tension_history_limit=10,
        skip_continuity_process_turn=True,
    )

    assert sync_calls == 1
    assert "scene_grounding" in st_module.session_state
