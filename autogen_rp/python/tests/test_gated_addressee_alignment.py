"""Gated addressee alignment under progression enforcement (Director selection)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_director import choose_next_actor as choose_next_actor_impl
from semantic_validation import (
    SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD,
    apply_gated_addressee_alignment_under_progression_enforcement,
    reconcile_turn_selection_issues,
)
from response_validation_selection import validate_turn_selection_decision


def test_apply_gated_override_when_all_conditions_met() -> None:
    decision = {
        "next_actor": "Ayame",
        "environment_event": "",
        "tension_shift": "",
        "reason": "pick",
    }
    sem = {
        "supports_selected_actor": False,
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "should_flag_repeat_spotlight": False,
        "confidence": 0.95,
        "reason": "m",
    }
    applied, prev, tgt = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=True,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Celina"],
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is True
    assert prev == "Ayame"
    assert tgt == "Celina"
    assert decision["next_actor"] == "Celina"
    assert "Addressee alignment (progression gate)" in decision["reason"]


def test_apply_gated_no_override_when_gate_inactive() -> None:
    decision = {"next_actor": "Ayame", "reason": "r"}
    sem = {
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "confidence": 0.95,
    }
    applied, _, _ = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=False,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Celina"],
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is False
    assert decision["next_actor"] == "Ayame"


def test_apply_gated_no_override_when_addressee_not_in_pool() -> None:
    decision = {"next_actor": "Ayame", "reason": "r"}
    sem = {
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "confidence": 0.95,
    }
    applied, _, _ = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=True,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Mira"],
        participant_names=["Ayame", "Mira", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is False
    assert decision["next_actor"] == "Ayame"


def test_apply_gated_no_override_when_director_already_aligned() -> None:
    decision = {"next_actor": "Celina", "reason": "r"}
    sem = {
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": False,
        "confidence": 0.95,
    }
    applied, _, _ = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=True,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Celina"],
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is False


def test_apply_gated_no_override_low_confidence() -> None:
    decision = {"next_actor": "Ayame", "reason": "r"}
    sem = {
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "confidence": SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD - 0.01,
    }
    applied, _, _ = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=True,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Celina"],
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is False
    assert decision["next_actor"] == "Ayame"


def test_apply_gated_no_override_on_end_round() -> None:
    decision = {"next_actor": "Ayame", "end_round": True, "reason": "r"}
    sem = {
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "confidence": 0.95,
    }
    applied, _, _ = apply_gated_addressee_alignment_under_progression_enforcement(
        decision=decision,
        progression_enforcement_gate=True,
        effective_semantic_assessment=sem,
        available_actors=["Ayame", "Celina"],
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert applied is False


class _FakeDirResp:
    __slots__ = ("chat_message",)

    def __init__(self, content: str) -> None:
        self.chat_message = SimpleNamespace(content=content)


class _FakeDirector:
    def __init__(self, content: str) -> None:
        self._content = content

    async def on_messages(self, _messages, _token):
        return _FakeDirResp(self._content)


@pytest.mark.asyncio
async def test_choose_next_actor_addressee_alignment_integration_gate_on() -> None:
    orch = {
        "pending_beat_shift": {"active": False},
        "spotlight_history": [],
        "scene_state": {
            "opening_description": "",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "present_characters": ["Ayame", "Celina", "Mira"],
            "offstage_characters": [],
        },
        "recent_structured_moves": [],
    }
    semantic_payload = {
        "supports_selected_actor": False,
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "should_flag_repeat_spotlight": False,
        "confidence": 0.95,
        "reason": "test",
    }

    async def _semantic(**_kwargs):
        return dict(semantic_payload)

    with patch(
        "app_turn_director.progression_delta_required",
        lambda **_k: True,
    ):
        decision = await choose_next_actor_impl(
            st_module=SimpleNamespace(
                session_state={"chat_history": [], "selector_decisions": []}
            ),
            director=_FakeDirector("{}"),
            get_model_client_fn=lambda: object(),
            participant_names=["Ayame", "Celina", "Mira"],
            trigger_text='Celina: "Answer me now."',
            cancellation_token=None,
            round_number=1,
            turn_number=1,
            available_actors=["Ayame", "Celina", "Mira"],
            continuation_override_actor=None,
            actors_used_this_round=[],
            enforce_must_remain_presence_fn=lambda: None,
            get_orchestration_state_fn=lambda: orch,
            get_continuity_manager_fn=lambda: None,
            build_scene_role_prompt_context_fn=lambda _ss, _names: [],
            serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
            build_summary_block_audit_metadata_fn=lambda **_k: {},
            serialize_events_for_prompt_fn=lambda *_a, **_k: [],
            serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
            build_director_selection_prompt_fn=lambda _p: "",
            parse_director_decision_fn=lambda *_a, **_k: (
                {
                    "next_actor": "Ayame",
                    "environment_event": "",
                    "tension_shift": "",
                    "reason": "director",
                },
                None,
            ),
            choose_fallback_actor_fn=lambda *_a, **_k: "Ayame",
            validate_turn_selection_decision_fn=validate_turn_selection_decision,
            assess_turn_selection_decision_semantics_fn=_semantic,
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

    assert decision.get("next_actor") == "Celina"
    assert "Addressee alignment (progression gate)" in str(decision.get("reason") or "")


@pytest.mark.asyncio
async def test_choose_next_actor_no_addressee_alignment_when_gate_off() -> None:
    orch = {
        "pending_beat_shift": {"active": False},
        "spotlight_history": [],
        "scene_state": {
            "opening_description": "",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "present_characters": ["Ayame", "Celina", "Mira"],
            "offstage_characters": [],
        },
        "recent_structured_moves": [],
    }
    semantic_payload = {
        "supports_selected_actor": False,
        "direct_address_target": "Celina",
        "should_flag_direct_address_miss": True,
        "should_flag_repeat_spotlight": False,
        "confidence": 0.95,
        "reason": "test",
    }

    async def _semantic(**_kwargs):
        return dict(semantic_payload)

    with patch(
        "app_turn_director.progression_delta_required",
        lambda **_k: False,
    ):
        decision = await choose_next_actor_impl(
            st_module=SimpleNamespace(
                session_state={"chat_history": [], "selector_decisions": []}
            ),
            director=_FakeDirector("{}"),
            get_model_client_fn=lambda: object(),
            participant_names=["Ayame", "Celina", "Mira"],
            trigger_text='Celina: "Answer me now."',
            cancellation_token=None,
            round_number=1,
            turn_number=1,
            available_actors=["Ayame", "Celina", "Mira"],
            continuation_override_actor=None,
            actors_used_this_round=[],
            enforce_must_remain_presence_fn=lambda: None,
            get_orchestration_state_fn=lambda: orch,
            get_continuity_manager_fn=lambda: None,
            build_scene_role_prompt_context_fn=lambda _ss, _names: [],
            serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
            build_summary_block_audit_metadata_fn=lambda **_k: {},
            serialize_events_for_prompt_fn=lambda *_a, **_k: [],
            serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
            build_director_selection_prompt_fn=lambda _p: "",
            parse_director_decision_fn=lambda *_a, **_k: (
                {
                    "next_actor": "Ayame",
                    "environment_event": "",
                    "tension_shift": "",
                    "reason": "director",
                },
                None,
            ),
            choose_fallback_actor_fn=lambda *_a, **_k: "Ayame",
            validate_turn_selection_decision_fn=validate_turn_selection_decision,
            assess_turn_selection_decision_semantics_fn=_semantic,
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

    assert decision.get("next_actor") == "Ayame"
    assert "Addressee alignment (progression gate)" not in str(decision.get("reason") or "")
