"""Integration tests for #231 proposal coherence in character attempt phase."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner_character_attempt as tca
from turn_runner_character_attempt import CharacterAttemptOutcome, run_character_attempt_phase


def _v2_move_with_proposals() -> dict[str, Any]:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "action", "content": "waves from the doorway"}],
        "motivation": "test",
        "semantic_proposals": [
            {"character": "Alice", "kind": "off_focal", "operation": None}
        ],
    }


class _FakeSceneState:
    def to_dict(self) -> dict[str, Any]:
        return {"present_characters": ["Alice"]}


class _FakeCM:
    def __init__(self) -> None:
        self.scene_state = _FakeSceneState()
        self.turn_counter = 0
        self.turn_metadata_by_index: dict[int, dict[str, Any]] = {0: {}}

    def to_dict(self) -> dict[str, Any]:
        return {"cm": True}

    def get_orchestration_context(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "active_issues": [],
            "summary_blocks": [],
            "recent_public_events": [],
            "scene_canon_anchors": [],
        }

    def get_relevant_canon_anchors(self, _actor: str) -> list[Any]:
        return []

    def process_turn(self, **_kwargs: Any) -> None:
        self.turn_counter = 1


class _FakeAgent:
    def __init__(self, raw: str) -> None:
        self._raw = raw

    async def on_messages(self, _messages: Any, _cancellation_token: Any) -> Any:
        return SimpleNamespace(chat_message=SimpleNamespace(content=self._raw))


class _MiniSt:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {
            "chat_history": [],
            "selector_decisions": [],
            "scene_grounding": None,
            "simulation_scenario_id": None,
            "progression_enforcement_disabled": True,
        }


def _kwargs(
    *,
    st: _MiniSt,
    agent: Any,
    validate_fn: Any,
    assess_proposal_fn: Any,
    actors_failed: list[str],
    max_attempts: int = 3,
) -> dict[str, Any]:
    move = _v2_move_with_proposals()
    raw = json.dumps(move)

    return {
        "st_module": st,
        "agent": agent,
        "next_actor": "Alice",
        "char_names": ["Alice"],
        "decision": {"next_actor": "Alice"},
        "trigger_text": "hi",
        "user_name": "User",
        "cancellation_token": object(),
        "round_number": 1,
        "turn_number": 1,
        "orchestration_state": {"scene_state": {"present_characters": ["Alice"]}},
        "actors_failed_this_round": actors_failed,
        "state_manager": None,
        "task_prompt": "prompt",
        "character_summary_block_audit": {},
        "parse_character_move_fn": lambda _r: (move, ""),
        "get_continuity_manager_fn": lambda: _FakeCM(),
        "is_audit_enabled_fn": lambda: False,
        "is_llm_audit_enabled_fn": lambda: False,
        "get_audit_logger_fn": lambda: None,
        "get_audit_context_fn": lambda: ("Alice", 1, 1, 1),
        "get_scene_audit_logging_kwargs_fn": lambda _s: {},
        "get_character_scene_audit_context_fn": lambda _n, _s: {},
        "validate_bot_response_fn": validate_fn,
        "get_model_client_fn": lambda: object(),
        "assess_presence_violation_semantics_fn": AsyncMock(return_value=None),
        "should_override_presence_rejection_fn": lambda *_a, **_k: False,
        "assess_proposal_beat_contradiction_fn": assess_proposal_fn,
        "log_turn_failure_fn": lambda **_kw: None,
        "sync_orchestration_state_from_continuity_fn": lambda: None,
        "effective_user_trigger": "hi",
        "max_character_attempts": max_attempts,
    }


@pytest.mark.asyncio
async def test_llm_contradicted_triggers_proposal_retry_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    calls = {"n": 0}

    async def assess_fn(**_kw: Any) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "status": "contradicted",
                "reason_code": "off_focal_vs_beats",
                "explanation": "beats show on-stage focal presence",
            }
        return {"status": "aligned", "reason_code": ""}

    out = await run_character_attempt_phase(
        **_kwargs(
            st=st,
            agent=_FakeAgent(json.dumps(_v2_move_with_proposals())),
            validate_fn=lambda *_a, **_k: (True, ""),
            assess_proposal_fn=assess_fn,
            actors_failed=[],
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["proposal_coherence_retry_triggered"] is True
    assert calls["n"] == 2
    assert any(
        "proposal coherence" in d.lower()
        for d in st.session_state["selector_decisions"]
    )


@pytest.mark.asyncio
async def test_structural_reject_skips_llm_and_fails_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    assess_mock = AsyncMock(
        return_value={"status": "contradicted", "reason_code": "off_focal_vs_beats"}
    )

    move = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "content": "x"}],
        "motivation": "m",
        "semantic_proposals": [
            {"character": "Alice", "kind": "off_focal"},
            {"character": "Alice", "kind": "reentry"},
        ],
    }
    st = _MiniSt()
    actors: list[str] = []

    kw = _kwargs(
        st=st,
        agent=_FakeAgent(json.dumps(move)),
        validate_fn=lambda *_a, **_k: (True, ""),
        assess_proposal_fn=assess_mock,
        actors_failed=actors,
        max_attempts=1,
    )
    kw["parse_character_move_fn"] = lambda _r: (move, "")
    out = await run_character_attempt_phase(**kw)
    assert out is None
    assert "Alice" in actors
    assess_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_unclear_fail_open_to_validate_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    validate_calls = {"n": 0}

    def validate_fn(*_a, **_k):
        validate_calls["n"] += 1
        return True, ""

    async def assess_fn(**_kw: Any) -> dict[str, Any]:
        return {"status": "unclear", "reason_code": "checker_parse_error"}

    out = await run_character_attempt_phase(
        **_kwargs(
            st=st,
            agent=_FakeAgent(json.dumps(_v2_move_with_proposals())),
            validate_fn=validate_fn,
            assess_proposal_fn=assess_fn,
            actors_failed=[],
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert validate_calls["n"] == 1
