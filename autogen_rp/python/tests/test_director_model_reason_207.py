"""GitHub #207: director_model_reason additive attribution (Phase B)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_director import choose_next_actor as choose_next_actor_impl  # noqa: E402
from beat_shift_state import default_pending_beat_shift  # noqa: E402
from response_validation_parsing import parse_director_decision  # noqa: E402
from response_validation_selection import validate_turn_selection_decision  # noqa: E402
from semantic_validation import reconcile_turn_selection_issues  # noqa: E402


class _FakeDirResp:
    __slots__ = ("chat_message",)

    def __init__(self, content: str) -> None:
        self.chat_message = SimpleNamespace(content=content)


class _FakeDirector:
    def __init__(self, content: str) -> None:
        self._content = content

    async def on_messages(self, _messages, _token):
        return _FakeDirResp(self._content)


def _default_orch() -> dict:
    return {
        "pending_beat_shift": default_pending_beat_shift(),
        "spotlight_history": [],
        "scene_state": {
            "opening_description": "",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "present_characters": ["Ayame", "Celina"],
            "offstage_characters": [],
        },
        "recent_structured_moves": [],
    }


async def _async_none(**_kwargs):
    return None


def test_parse_sets_director_model_reason_for_reason_key() -> None:
    raw = {
        "next_actor": "Ayame",
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "Ayame was directly addressed.",
        "end_round": False,
    }
    decision, error = parse_director_decision(
        json.dumps(raw),
        ["Ayame", "Celina"],
        ["Ayame", "Celina"],
    )
    assert error == ""
    assert decision is not None
    assert decision["director_model_reason"] == "Ayame was directly addressed."
    assert decision["reason"] == "Ayame was directly addressed."


def test_parse_sets_director_model_reason_for_reason_for_choice() -> None:
    raw = {
        "next_actor": "Celina",
        "environment_event": "",
        "tension_shift": "steady",
        "reason_for_choice": "legacy rationale",
        "end_round": False,
    }
    decision, error = parse_director_decision(
        json.dumps(raw),
        ["Ayame", "Celina"],
        ["Ayame", "Celina"],
    )
    assert error == ""
    assert decision is not None
    assert decision["director_model_reason"] == "legacy rationale"
    assert decision["reason"] == "legacy rationale"


def test_parse_omits_director_model_reason_without_rationale_keys() -> None:
    raw = {
        "next_actor": "Ayame",
        "environment_event": "",
        "tension_shift": "steady",
        "end_round": False,
    }
    decision, error = parse_director_decision(
        json.dumps(raw),
        ["Ayame", "Celina"],
        ["Ayame", "Celina"],
    )
    assert error == ""
    assert decision is not None
    assert "director_model_reason" not in decision
    assert decision["reason"] == ""


@pytest.mark.asyncio
async def test_parse_failure_omits_director_model_reason() -> None:
    st = SimpleNamespace(session_state={"chat_history": [], "selector_decisions": []})
    decision = await choose_next_actor_impl(
        st_module=st,
        director=_FakeDirector('{"not":"director"}'),
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="hello",
        cancellation_token=None,
        round_number=1,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        actors_used_this_round=[],
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: _default_orch(),
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=lambda _p: "",
        parse_director_decision_fn=lambda *_a, **_k: (None, "bad parse"),
        choose_fallback_actor_fn=lambda *_a, **_k: "Celina",
        validate_turn_selection_decision_fn=validate_turn_selection_decision,
        assess_turn_selection_decision_semantics_fn=_async_none,
        reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues,
        get_character_display_name_fn=lambda k: k,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )
    assert "director_model_reason" not in decision
    assert decision.get("source") == "fallback"
    assert "Fallback selection after director parse failure" in str(
        decision.get("reason") or ""
    )


@pytest.mark.asyncio
async def test_hard_route_forced_speaker_omits_director_model_reason() -> None:
    st = SimpleNamespace(
        session_state={
            "pending_forced_speaker": "Ayame",
            "forced_speaker_consumed": False,
            "selector_decisions": [],
        }
    )
    decision = await choose_next_actor_impl(
        st_module=st,
        director=None,
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="hello",
        cancellation_token=None,
        round_number=1,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        actors_used_this_round=[],
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: _default_orch(),
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=lambda _p: "",
        parse_director_decision_fn=lambda *_a, **_k: ({}, ""),
        choose_fallback_actor_fn=lambda *_a, **_k: "",
        validate_turn_selection_decision_fn=lambda *_a, **_k: [],
        assess_turn_selection_decision_semantics_fn=_async_none,
        reconcile_turn_selection_issues_fn=lambda issues, _a, **_: issues,
        get_character_display_name_fn=lambda k: k,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )
    assert "director_model_reason" not in decision
    assert decision.get("next_actor") == "Ayame"


@pytest.mark.asyncio
async def test_director_model_reason_not_display_normalized() -> None:
    """Merged reason gets display substitution; director_model_reason stays parse-time."""
    raw = {
        "next_actor": "Ayame",
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "Ayame should speak — scene focus on Ayame.",
        "end_round": False,
    }
    st = SimpleNamespace(session_state={"chat_history": [], "selector_decisions": []})
    decision = await choose_next_actor_impl(
        st_module=st,
        director=_FakeDirector(json.dumps(raw)),
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="hello",
        cancellation_token=None,
        round_number=1,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        actors_used_this_round=[],
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: _default_orch(),
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=lambda _p: "",
        parse_director_decision_fn=parse_director_decision,
        choose_fallback_actor_fn=lambda *_a, **_k: "Ayame",
        validate_turn_selection_decision_fn=validate_turn_selection_decision,
        assess_turn_selection_decision_semantics_fn=_async_none,
        reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues,
        get_character_display_name_fn=lambda k: "Lady Ayame" if k == "Ayame" else k,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )
    assert decision.get("director_model_reason") == (
        "Ayame should speak — scene focus on Ayame."
    )
    merged = str(decision.get("reason") or "")
    assert "Lady Ayame" in merged
    assert merged != decision.get("director_model_reason")


@pytest.mark.asyncio
async def test_sim_metrics_selection_attribution_includes_director_model_reason() -> None:
    raw = {
        "next_actor": "Ayame",
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "pick Ayame",
        "end_round": False,
    }
    st = SimpleNamespace(
        session_state={
            "chat_history": [],
            "selector_decisions": [],
            "sim_progression_metrics": [],
        }
    )
    await choose_next_actor_impl(
        st_module=st,
        director=_FakeDirector(json.dumps(raw)),
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="hello",
        cancellation_token=None,
        round_number=1,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        actors_used_this_round=[],
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: _default_orch(),
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=lambda _p: "",
        parse_director_decision_fn=parse_director_decision,
        choose_fallback_actor_fn=lambda *_a, **_k: "Ayame",
        validate_turn_selection_decision_fn=validate_turn_selection_decision,
        assess_turn_selection_decision_semantics_fn=_async_none,
        reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues,
        get_character_display_name_fn=lambda k: k,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )
    events = st.session_state["sim_progression_metrics"]
    rows = [e for e in events if e.get("kind") == "selection_attribution"]
    assert rows
    assert rows[-1].get("director_model_reason") == "pick Ayame"
