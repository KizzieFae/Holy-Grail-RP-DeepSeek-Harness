"""Payload parity regression tests for ``director_prompt_payload`` (GitHub #172)."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from director_prompt_payload import DirectorPromptAssembly, build_director_prompt_payload


def _assert_payload_deep_parity(left: Any, right: Any) -> None:
    assert type(left) is type(right)
    if isinstance(left, dict):
        assert set(left.keys()) == set(right.keys()), (
            f"key mismatch: {set(left.keys()) ^ set(right.keys())}"
        )
        for k in sorted(left.keys()):
            _assert_payload_deep_parity(left[k], right[k])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for a, b in zip(left, right, strict=True):
            _assert_payload_deep_parity(a, b)
    else:
        assert left == right


def _assert_assembly_parity(a: DirectorPromptAssembly, b: DirectorPromptAssembly) -> None:
    _assert_payload_deep_parity(a.director_payload, b.director_payload)
    _assert_payload_deep_parity(a.summary_block_audit, b.summary_block_audit)
    _assert_payload_deep_parity(a.scene_state_for_prompt, b.scene_state_for_prompt)
    assert a.continuity_manager is b.continuity_manager
    _assert_payload_deep_parity(a.orchestration_state, b.orchestration_state)
    _assert_payload_deep_parity(
        a.progression_advisory_snapshot, b.progression_advisory_snapshot
    )
    assert a.anti_prefix == b.anti_prefix
    _assert_payload_deep_parity(a.anti_blob, b.anti_blob)
    assert a.beat_shift_active == b.beat_shift_active
    assert (
        a.low_pressure_turn_guidance_active_flag
        == b.low_pressure_turn_guidance_active_flag
    )
    _assert_payload_deep_parity(a.responder_hint_for_audit, b.responder_hint_for_audit)
    _assert_payload_deep_parity(a.director_prefix_eligible, b.director_prefix_eligible)
    _assert_payload_deep_parity(
        a.director_prefix_in_prompt, b.director_prefix_in_prompt
    )
    assert a.spotlight_recent == b.spotlight_recent
    assert a.spotlight_last_before_pick == b.spotlight_last_before_pick


class _FakeIssue:
    def __init__(self, d: dict[str, Any]) -> None:
        self._d = dict(d)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._d)


class _FakeStateManager:
    def public_state_snapshot(self) -> dict[str, Any]:
        return {"Alice": {"goal": "x"}}


class _FakeSceneState:
    def __init__(self, d: dict[str, Any]) -> None:
        self._d = dict(d)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._d)


class _FakeContinuitySnapshot:
    def __init__(self, scene_dict: dict[str, Any]) -> None:
        self.scene_state = _FakeSceneState(scene_dict)


class _FakeCM:
    def __init__(
        self, orch_ctx: dict[str, Any], scene_state_dict: dict[str, Any]
    ) -> None:
        self.summary_blocks: list[Any] = []
        self.summary_interval = 0
        self.turn_counter = 0
        self._orch = orch_ctx
        self._scene_state_dict = scene_state_dict

    def get_snapshot(self) -> _FakeContinuitySnapshot:
        return _FakeContinuitySnapshot(self._scene_state_dict)

    def get_orchestration_context(self, **kwargs: Any) -> dict[str, Any]:
        return self._orch

    def retrieve_summary_blocks(self, limit: int = 0) -> list[Any]:
        _ = limit
        return []


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any]) -> None:
        self.session_state = session_state


def _minimal_session() -> _FakeStreamlit:
    return _FakeStreamlit(
        {
            "character_state_manager": _FakeStateManager(),
            "chat_history": [{"role": "user", "text": "hi"}],
            "scene_grounding": None,
        }
    )


def _minimal_orch(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "scene_state": {
            "opening_description": "Cold open",
            "recent_environment_events": [],
            "tension_history": ["up"],
            "resolved_events": [],
            "location": "Room",
            "phase": 1,
            "current_tension_level": "medium",
            "recent_delta": "",
            "scene_template_id": "t1",
            "scene_premise": "Test premise",
            "location_entry_slots": ["door"],
            "present_characters": ["Alice", "Bob"],
            "offstage_characters": [],
        },
        "spotlight_history": ["Alice"],
        "recent_structured_moves": [
            {
                "speaker": "Alice",
                "dialogue": "Hello Bob?",
                "action": "",
                "audibility": "directed",
                "audience": ["Bob"],
            }
        ],
    }
    base.update(overrides)
    return base


@pytest.fixture
def minimal_orchestration_state() -> dict[str, Any]:
    return _minimal_orch()


@pytest.fixture
def minimal_continuity(minimal_orchestration_state: dict[str, Any]) -> _FakeCM:
    ctx = {
        "active_issues": [
            _FakeIssue({"status": "active", "id": "i1", "title": "T"}),
            _FakeIssue({"status": "resolved", "id": "i2", "title": "Old"}),
        ],
        "summary_blocks": [],
        "recent_public_events": [],
        "scene_canon_anchors": [],
    }
    return _FakeCM(ctx, dict(minimal_orchestration_state["scene_state"]))


def _call_build(
    *,
    st: _FakeStreamlit,
    orch: dict[str, Any],
    cm: Any,
) -> DirectorPromptAssembly:
    return build_director_prompt_payload(
        st_module=st,
        orchestration_state=orch,
        continuity_manager=cm,
        participant_names=["Alice", "Bob"],
        trigger_text="User line",
        available_actors=["Alice", "Bob"],
        used_this_round=[],
        continuation_override_actor=None,
        build_scene_role_prompt_context_fn=lambda scene, names: {"roles": list(names)},
        serialize_summary_blocks_for_prompt_fn=lambda blocks: [{"b": b} for b in blocks],
        build_summary_block_audit_metadata_fn=lambda **kw: {
            "audit": True,
            "kw_keys": sorted(kw.keys()),
        },
        serialize_events_for_prompt_fn=lambda events: [{"e": e} for e in events],
        serialize_canon_anchors_for_prompt_fn=lambda anchors: [{"a": a} for a in anchors],
        build_recent_dialogue_history_fn=lambda chat, limit, viewer_character_name=None: [
            str(x) for x in chat[-limit:]
        ],
        prompt_dialogue_history_limit=8,
        director_spotlight_history_limit=4,
    )


def test_build_idempotent_pair(
    minimal_orchestration_state: dict[str, Any], minimal_continuity: _FakeCM
) -> None:
    orch1 = copy.deepcopy(minimal_orchestration_state)
    a = _call_build(st=_minimal_session(), orch=orch1, cm=minimal_continuity)
    orch2 = copy.deepcopy(minimal_orchestration_state)
    b = _call_build(st=_minimal_session(), orch=orch2, cm=minimal_continuity)
    _assert_assembly_parity(a, b)


def test_base_payload_key_and_nested_shape(
    minimal_orchestration_state: dict[str, Any], minimal_continuity: _FakeCM
) -> None:
    assembly = _call_build(
        st=_minimal_session(),
        orch=minimal_orchestration_state,
        cm=minimal_continuity,
    )
    dp = assembly.director_payload
    top_required = {
        "current_scene_state",
        "scene_template",
        "scene_roles",
        "recent_structured_character_actions",
        "character_states",
        "recent_dialogue_history",
        "spotlight_history",
        "active_issues",
        "stalled_background_issues",
        "summary_blocks",
        "recent_public_events",
        "scene_canon_anchors",
        "participants",
        "available_next_actors",
        "actors_already_used_this_round",
        "response_cycle_acting_counts",
        "responder_obligation",
        "action_responsibility",
        "settled_scene_facts_prompt",
    }
    assert top_required <= set(dp.keys())
    nested = dp["current_scene_state"]
    for k in (
        "opening_description",
        "recent_environment_events",
        "tension_history",
        "resolved_events",
        "location",
        "scene_phase",
        "current_tension_level",
        "recent_delta",
        "latest_trigger",
        "present_characters",
        "offstage_characters",
    ):
        assert k in nested


def test_progression_high_conditional_keys(
    monkeypatch: pytest.MonkeyPatch,
    minimal_orchestration_state: dict[str, Any],
    minimal_continuity: _FakeCM,
) -> None:
    import director_prompt_payload as dpp

    def _fake_sync(*, orchestration_state: Any, continuity_manager: Any) -> dict[str, Any]:
        return {"progression_pressure": "high", "stall_score": 12.0}

    monkeypatch.setattr(dpp, "sync_progression_advisory_for_prompts", _fake_sync)
    monkeypatch.setattr(
        dpp,
        "build_progression_director_prompt_prefix",
        lambda snap: "PROG_PREFIX",
    )
    assembly = _call_build(
        st=_minimal_session(),
        orch=minimal_orchestration_state,
        cm=minimal_continuity,
    )
    dp = assembly.director_payload
    assert "progression_director_hints" in dp
    assert dp["progression_director_hints"]["prompt_prefix"] == "PROG_PREFIX"


def test_beat_shift_conditional_keys(
    monkeypatch: pytest.MonkeyPatch,
    minimal_orchestration_state: dict[str, Any],
    minimal_continuity: _FakeCM,
) -> None:
    import director_prompt_payload as dpp

    monkeypatch.setattr(dpp, "is_pending_beat_shift_active", lambda state: True)
    monkeypatch.setattr(
        dpp,
        "build_director_beat_shift_prompt_prefix",
        lambda: "BEAT_PREFIX",
    )
    assembly = _call_build(
        st=_minimal_session(),
        orch=minimal_orchestration_state,
        cm=minimal_continuity,
    )
    dp = assembly.director_payload
    assert "beat_shift_director_hints" in dp
    assert dp["beat_shift_director_hints"]["prompt_prefix"] == "BEAT_PREFIX"


def test_low_pressure_conditional_nested(
    monkeypatch: pytest.MonkeyPatch,
    minimal_orchestration_state: dict[str, Any],
    minimal_continuity: _FakeCM,
) -> None:
    import director_prompt_payload as dpp

    monkeypatch.setattr(
        dpp,
        "sync_progression_advisory_for_prompts",
        lambda **kw: {"progression_pressure": "low", "stall_score": 0},
    )
    monkeypatch.setattr(
        dpp,
        "sync_anti_regression_advisory_for_prompts",
        lambda **kw: {"prompt_prefix": "", "advisory_blob": {}},
    )
    assembly = _call_build(
        st=_minimal_session(),
        orch=minimal_orchestration_state,
        cm=minimal_continuity,
    )
    dp = assembly.director_payload
    assert "low_pressure_turn_selection" in dp
    assert "responder_hint" in dp
    assert "low_pressure_turn_director_hints" in dp


def test_arch_quality_suppression_conditional_exclusions(
    monkeypatch: pytest.MonkeyPatch,
    minimal_orchestration_state: dict[str, Any],
    minimal_continuity: _FakeCM,
) -> None:
    import director_prompt_payload as dpp

    monkeypatch.setattr(
        dpp,
        "arch_quality_a1_suppress_director_soft_prefixes",
        lambda st_module: True,
    )
    monkeypatch.setattr(
        dpp,
        "sync_progression_advisory_for_prompts",
        lambda **kw: {"progression_pressure": "high", "stall_score": 1},
    )
    monkeypatch.setattr(
        dpp,
        "build_progression_director_prompt_prefix",
        lambda snap: "P",
    )
    assembly = _call_build(
        st=_minimal_session(),
        orch=minimal_orchestration_state,
        cm=minimal_continuity,
    )
    dp = assembly.director_payload
    assert "progression_director_hints" not in dp
    assert "anti_regression_director_hints" not in dp
