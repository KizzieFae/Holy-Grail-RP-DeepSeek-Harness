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
            narrator_output_audit_v1={},
            narrator_validation_audit_v1={},
            prose_dialogue_audit_v1={},
            audit_v2_narrator=None,
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
            effective_user_trigger="",
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
        narrator_output_audit_v1={},
        narrator_validation_audit_v1={},
        prose_dialogue_audit_v1={},
        audit_v2_narrator=None,
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
        effective_user_trigger="",
    )

    assert sync_calls == 1
    assert "scene_grounding" in st_module.session_state


class _CapturingContinuityManager:
    def __init__(self) -> None:
        self.scene_state = SimpleNamespace()
        self.turn_counter = 1
        self.turn_metadata_by_index: dict[int, dict[str, object]] = {
            1: {"consequences": []},
        }
        self.issues: dict[str, object] = {}
        self.captured: dict[str, object] = {}

    def process_turn(self, **kwargs: object) -> None:
        self.captured = dict(kwargs)


def test_apply_successful_turn_passes_session_mutation_candidates_from_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_module = FakeStreamlit()
    from continuity_mutation_pipeline import (
        CanonicalAtom,
        ContinuityMutationType,
        MutationRequest,
        MutationSourceClass,
    )

    cand = MutationRequest(
        mutation_type=ContinuityMutationType.EXCURSION_OPEN,
        atom=CanonicalAtom.EXCURSION_LIFECYCLE,
        source=MutationSourceClass.S,
        payload={
            "operation": "open",
            "excursion_id": "x",
            "participant_character_ids": ["B"],
        },
    )
    st_module.session_state["tier_b_session_mutation_by_turn"] = {3: [cand]}
    cm = _CapturingContinuityManager()
    st_module.session_state["continuity_manager"] = cm

    monkeypatch.setattr(
        turn_runner_updates,
        "rebuild_scene_grounding_from_continuity",
        lambda _m: {"schema_version": 1, "facts": [], "last_rebuilt_turn": 0},
    )

    turn_runner_updates.apply_successful_turn_updates(
        st_module=st_module,
        next_actor="A",
        char_names=["A", "B"],
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {"goal": "g", "tactic": "t", "risk_level": "low"},
        },
        decision={"next_actor": "B"},
        rendered="",
        narrator_raw="",
        narrator_prompt="",
        narrator_summary_block_audit={},
        narrator_semantic_assessment=None,
        narrator_output_audit_v1={},
        narrator_validation_audit_v1={},
        prose_dialogue_audit_v1={},
        audit_v2_narrator=None,
        round_number=1,
        turn_number=3,
        state_manager=None,
        record_character_memories_fn=lambda *_a, **_k: None,
        sync_orchestration_state_from_continuity_fn=lambda: None,
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
        effective_user_trigger="",
    )
    got = cm.captured.get("session_mutation_candidates")
    assert got is not None and len(got) == 1
    assert got[0].mutation_type == ContinuityMutationType.EXCURSION_OPEN
