"""Cross-cutting validation: beat-shift activation → director prompt → fallback → semantic kwarg → audit metadata.

These tests replay the production call graph with stubs (no live LLM). They are the automated
checkpoint for the behavioral chain.

Run:

    python -m pytest tests/test_beat_shift_replay_validation.py -v

Manual follow-up (not LLM-judge automatable here): after a live play session, open the latest
Director ``*_full.json`` under ``rp_app/data/rp_audits/`` and confirm ``metadata.beat_shift_active``
matches rounds where you used a short/OOC trigger or hit plateau detection; skim the following
character/narrator moves for an observable state change vs. pure reframing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_director import choose_next_actor as choose_next_actor_impl
from beat_shift_state import (
    build_director_beat_shift_prompt_prefix,
    default_pending_beat_shift,
    maybe_activate_pending_beat_shift,
)
from orchestration_helpers import choose_fallback_actor
from prompt_builders import build_director_selection_prompt
from response_validation_parsing import parse_director_decision


async def _async_none(**_kwargs):
    return None


class _FakeDirectorResponse:
    __slots__ = ("chat_message",)

    def __init__(self, content: str) -> None:
        self.chat_message = SimpleNamespace(content=content)


class FakeDirector:
    """Returns director raw text; default invalid JSON forces fallback path."""

    def __init__(self, content: str = "{}") -> None:
        self._content = content

    async def on_messages(self, _messages, _token):
        return _FakeDirectorResponse(self._content)


def _minimal_orch(*, beat_active: bool) -> dict:
    pbs = default_pending_beat_shift()
    if beat_active:
        pbs = {"active": True, "reason": "short_user_message", "source_turn_id": "user_round_3"}
    return {
        "pending_beat_shift": pbs,
        "spotlight_history": ["Ayame"],
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


@pytest.mark.asyncio
async def test_validation_activation_short_message_matches_turn_runner_contract() -> None:
    orch = {
        "pending_beat_shift": default_pending_beat_shift(),
        "beat_shift_scene_snapshots": [],
    }
    maybe_activate_pending_beat_shift(
        orch, trigger_text="Knot!", source_turn_id="user_round_5"
    )
    assert orch["pending_beat_shift"]["active"] is True
    assert orch["pending_beat_shift"]["reason"] == "short_user_message"


def test_validation_director_json_omits_hints_but_prefix_present() -> None:
    prefix = build_director_beat_shift_prompt_prefix()
    p = build_director_selection_prompt(
        {
            "participants": ["Ayame", "Celina"],
            "available_next_actors": ["Ayame", "Celina"],
            "beat_shift_director_hints": {"active": True, "prompt_prefix": prefix},
        }
    )
    assert p.startswith(prefix)
    assert "BEAT SHIFT (ACTIVE)" in p
    assert "beat_shift_director_hints" not in p
    assert '"participants"' in p


@pytest.mark.asyncio
async def test_validation_replay_director_fallback_semantic_and_audit_under_beat_shift() -> (
    None
):
    orch = _minimal_orch(beat_active=True)
    captured_audit_metadata: dict = {}
    captured_input_content = ""
    captured_semantic: dict = {}

    async def assess_fn(**kwargs):
        captured_semantic.update(kwargs)
        return None

    class _AuditLogger:
        def create_entry(self, **kwargs):
            captured_audit_metadata.update(kwargs.get("metadata") or {})
            nonlocal captured_input_content
            msgs = kwargs.get("input_messages") or []
            if msgs:
                captured_input_content = str(msgs[0].get("content", "") or "")
            return SimpleNamespace()

        def log_bot_interaction(self, _entry):
            pass

    decision = await choose_next_actor_impl(
        st_module=SimpleNamespace(
            session_state={"chat_history": [], "selector_decisions": []}
        ),
        director=FakeDirector(content="{}"),
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="Do it.",
        cancellation_token=None,
        round_number=3,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: orch,
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=build_director_selection_prompt,
        parse_director_decision_fn=parse_director_decision,
        choose_fallback_actor_fn=lambda avail, forced, *, prefer_continuing_spotlight=False: choose_fallback_actor(
            avail,
            forced,
            orch["spotlight_history"],
            prefer_continuing_spotlight=prefer_continuing_spotlight,
        ),
        validate_turn_selection_decision_fn=lambda *_a, **_k: [],
        assess_turn_selection_decision_semantics_fn=assess_fn,
        reconcile_turn_selection_issues_fn=lambda issues, _a: issues,
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _AuditLogger(),
        get_audit_context_fn=lambda: ("owner", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )

    assert decision.get("next_actor") == "Ayame"
    assert "Fallback selection after director parse failure" in str(
        decision.get("reason", "") or ""
    )
    assert captured_semantic.get("beat_shift_active") is True
    assert captured_audit_metadata.get("beat_shift_active") is True
    assert "DIRECTOR SELECTION" in captured_input_content or "BEAT SHIFT (ACTIVE)" in (
        captured_input_content
    )
    assert "beat_shift_director_hints" not in captured_input_content


@pytest.mark.asyncio
async def test_validation_replay_director_prompt_without_beat_shift_has_no_beat_prefix() -> (
    None
):
    orch = _minimal_orch(beat_active=False)
    captured_input_content = ""

    class _AuditLogger:
        def create_entry(self, **kwargs):
            nonlocal captured_input_content
            msgs = kwargs.get("input_messages") or []
            if msgs:
                captured_input_content = str(msgs[0].get("content", "") or "")
            return SimpleNamespace()

        def log_bot_interaction(self, _entry):
            pass

    await choose_next_actor_impl(
        st_module=SimpleNamespace(
            session_state={"chat_history": [], "selector_decisions": []}
        ),
        director=FakeDirector(content="{}"),
        get_model_client_fn=lambda: None,
        participant_names=["Ayame", "Celina"],
        trigger_text="Long enough player line that does not alone trigger beat shift.",
        cancellation_token=None,
        round_number=3,
        turn_number=1,
        available_actors=["Ayame", "Celina"],
        continuation_override_actor=None,
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: orch,
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda _ss, _names: [],
        serialize_summary_blocks_for_prompt_fn=lambda *_a, **_k: [],
        build_summary_block_audit_metadata_fn=lambda **_k: {},
        serialize_events_for_prompt_fn=lambda *_a, **_k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_a, **_k: [],
        build_director_selection_prompt_fn=build_director_selection_prompt,
        parse_director_decision_fn=parse_director_decision,
        choose_fallback_actor_fn=lambda avail, forced, *, prefer_continuing_spotlight=False: choose_fallback_actor(
            avail,
            forced,
            orch["spotlight_history"],
            prefer_continuing_spotlight=prefer_continuing_spotlight,
        ),
        validate_turn_selection_decision_fn=lambda *_a, **_k: [],
        assess_turn_selection_decision_semantics_fn=_async_none,
        reconcile_turn_selection_issues_fn=lambda issues, _a: issues,
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _AuditLogger(),
        get_audit_context_fn=lambda: ("owner", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_a, **_k: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )

    assert not captured_input_content.startswith(
        build_director_beat_shift_prompt_prefix()
    )
    assert "beat_shift_director_hints" not in captured_input_content
