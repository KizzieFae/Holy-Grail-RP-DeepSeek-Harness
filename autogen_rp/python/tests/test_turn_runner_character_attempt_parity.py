"""Branch topology parity tests for ``turn_runner_character_attempt`` (GitHub #173)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner_character_attempt as tca
from turn_runner_character_attempt import CharacterAttemptOutcome, run_character_attempt_phase


def _v2_move() -> dict[str, Any]:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "action", "content": "nods"}],
        "motivation": "test",
    }


class _FakeSceneState:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class _FakeCM:
    def __init__(self, *, scene_present: bool = True) -> None:
        self.scene_state: _FakeSceneState | None
        if scene_present:
            self.scene_state = _FakeSceneState({"present_characters": ["Alice"]})
        else:
            self.scene_state = None
        self.turn_counter = 0
        self.turn_metadata_by_index: dict[int, dict[str, Any]] = {0: {}}
        self._raise_on_pt = False
        self.issues: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {"cm": id(self), "turn": self.turn_counter}

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
        if self._raise_on_pt:
            raise RuntimeError("boom_process_turn")
        self.turn_counter = max(1, int(self.turn_counter) + 1)


class _FakeAgentQueue:
    def __init__(self, contents: list[str]) -> None:
        self._q = list(contents)

    async def on_messages(self, _messages: Any, _cancellation_token: Any) -> Any:
        raw = self._q.pop(0)
        return SimpleNamespace(chat_message=SimpleNamespace(content=raw))


class _MiniSt:
    def __init__(self, **session_overrides: Any) -> None:
        self.session_state: dict[str, Any] = {
            "chat_history": [],
            "selector_decisions": [],
            "scene_grounding": None,
            "simulation_scenario_id": None,
            "progression_enforcement_disabled": False,
        }
        self.session_state.update(session_overrides)


def _base_kwargs(
    *,
    st: _MiniSt,
    agent: Any,
    parse_fn: Any,
    validate_fn: Any,
    actors_failed: list[str],
    get_cm: Any,
    max_character_attempts: int = 3,
) -> dict[str, Any]:
    return {
        "st_module": st,
        "agent": agent,
        "next_actor": "Alice",
        "char_names": ["Alice"],
        "decision": {"next_actor": "Alice", "reason": "t"},
        "trigger_text": "hi",
        "user_name": "User",
        "cancellation_token": object(),
        "round_number": 1,
        "turn_number": 1,
        "orchestration_state": {"scene_state": {"present_characters": ["Alice"]}},
        "actors_failed_this_round": actors_failed,
        "state_manager": None,
        "task_prompt": "system prompt",
        "character_summary_block_audit": {},
        "parse_character_move_fn": parse_fn,
        "get_continuity_manager_fn": get_cm,
        "is_audit_enabled_fn": lambda: False,
        "is_llm_audit_enabled_fn": lambda: False,
        "get_audit_logger_fn": lambda: None,
        "get_audit_context_fn": lambda: ("Alice", 1, 1, 1),
        "get_scene_audit_logging_kwargs_fn": lambda _s: {},
        "get_character_scene_audit_context_fn": lambda _n, _s: {},
        "validate_bot_response_fn": validate_fn,
        "get_model_client_fn": lambda: object(),
        "assess_presence_violation_semantics_fn": lambda **_kw: None,
        "should_override_presence_rejection_fn": lambda *_a, **_k: False,
        "log_turn_failure_fn": lambda **_kw: None,
        "sync_orchestration_state_from_continuity_fn": lambda: None,
        "effective_user_trigger": "hi",
        "max_character_attempts": max_character_attempts,
    }


@pytest.mark.asyncio
async def test_parse_fail_retry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _FakeCM()
    import json

    ok_raw = json.dumps(_v2_move())
    contents = ["badjson", ok_raw]

    def parse_fn(raw: str) -> tuple[Any, str]:
        if raw == "badjson":
            return None, "parse err"
        return json.loads(raw), ""

    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue(contents),
            parse_fn=parse_fn,
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=[],
            get_cm=lambda: cm,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["parse_retry_triggered"] is True
    assert "Retrying Alice after character move parse failure" in "".join(
        st.session_state["selector_decisions"]
    )


@pytest.mark.asyncio
async def test_duplicate_rejection_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _FakeCM()
    n = {"i": 0}

    def validate_fn(*_a, **_k):
        n["i"] += 1
        if n["i"] == 1:
            return False, "[DUPLICATE] repeat"
        return True, ""

    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue(['{"move_schema_version":2,"beats":[{"type":"action","content":"x"}],"motivation":"m"}'] * 2),
            parse_fn=lambda raw: (__import__("json").loads(raw), ""),
            validate_fn=validate_fn,
            actors_failed=[],
            get_cm=lambda: cm,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["duplicate_retry_triggered"] is True


@pytest.mark.asyncio
async def test_binding_rejection_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _FakeCM()
    n = {"i": 0}

    def validate_fn(*_a, **_k):
        n["i"] += 1
        if n["i"] == 1:
            return False, "[BINDING_SLEEPING_SURFACE] nap"
        return True, ""

    raw = __import__("json").dumps(_v2_move())
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([raw, raw]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=validate_fn,
            actors_failed=[],
            get_cm=lambda: cm,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["binding_retry_triggered"] is True


@pytest.mark.asyncio
async def test_investigation_rejection_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _FakeCM()
    n = {"i": 0}

    def validate_fn(*_a, **_k):
        n["i"] += 1
        if n["i"] == 1:
            return False, "[INVESTIGATION_ANCHOR] missing"
        return True, ""

    raw = __import__("json").dumps(_v2_move())
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([raw, raw]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=validate_fn,
            actors_failed=[],
            get_cm=lambda: cm,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["investigation_retry_triggered"] is True


@pytest.mark.asyncio
async def test_scene_presence_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _FakeCM()
    calls: list[Any] = []

    async def assess(**_kw):
        calls.append(1)
        return {"ok": True}

    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([__import__("json").dumps(_v2_move())]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=lambda *_a, **_k: (False, "[SCENE_PRESENCE] absent"),
            actors_failed=[],
            get_cm=lambda: cm,
        )
        | {
            "assess_presence_violation_semantics_fn": assess,
            "should_override_presence_rejection_fn": lambda *_a, **_k: True,
        }
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert calls
    assert any(
        "Semantic validation kept" in x for x in st.session_state["selector_decisions"]
    )


@pytest.mark.asyncio
async def test_progression_retry_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)
    monkeypatch.setattr(tca, "collect_issue_signatures", lambda *_a, **_k: [])
    monkeypatch.setattr(tca, "progression_delta_required", lambda **_kw: True)
    monkeypatch.setattr(tca, "maybe_record_sim_progression_metric", lambda *_a, **_k: None)
    qual_calls = {"n": 0}

    def qualifies(**_kw):
        qual_calls["n"] += 1
        return qual_calls["n"] >= 2

    monkeypatch.setattr(tca, "qualifies_as_progression_delta", qualifies)

    st = _MiniSt()
    cm = _FakeCM()
    raw = __import__("json").dumps(_v2_move())
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([raw, raw]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=[],
            get_cm=lambda: cm,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["progression_retry_triggered"] is True
    assert qual_calls["n"] >= 2


@pytest.mark.asyncio
async def test_progression_fail_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)
    monkeypatch.setattr(tca, "collect_issue_signatures", lambda *_a, **_k: [])
    monkeypatch.setattr(tca, "progression_delta_required", lambda **_kw: True)
    monkeypatch.setattr(tca, "qualifies_as_progression_delta", lambda **_kw: False)
    monkeypatch.setattr(tca, "maybe_record_sim_progression_metric", lambda *_a, **_k: None)

    st = _MiniSt()
    cm = _FakeCM()
    raw = __import__("json").dumps(_v2_move())
    actors: list[str] = []
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([raw]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=actors,
            get_cm=lambda: cm,
            max_character_attempts=1,
        )
    )
    assert out is None
    assert "Alice" in actors


@pytest.mark.asyncio
async def test_continuity_exception_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)
    monkeypatch.setattr(tca, "collect_issue_signatures", lambda *_a, **_k: [])
    monkeypatch.setattr(tca, "progression_delta_required", lambda **_kw: False)
    monkeypatch.setattr(tca, "qualifies_as_progression_delta", lambda **_kw: True)
    monkeypatch.setattr(tca, "maybe_record_sim_progression_metric", lambda *_a, **_k: None)

    st = _MiniSt()
    cm = _FakeCM()
    cm._raise_on_pt = True
    from_dict_mock = MagicMock(side_effect=lambda _d: cm)
    monkeypatch.setattr(tca.ContinuityManager, "from_dict", from_dict_mock)

    sync_calls = {"n": 0}

    def sync():
        sync_calls["n"] += 1

    raw = __import__("json").dumps(_v2_move())
    with pytest.raises(RuntimeError, match="boom_process_turn"):
        await run_character_attempt_phase(
            **_base_kwargs(
                st=st,
                agent=_FakeAgentQueue([raw]),
                parse_fn=lambda r: (__import__("json").loads(r), ""),
                validate_fn=lambda *_a, **_k: (True, ""),
                actors_failed=[],
                get_cm=lambda: cm,
            )
            | {"sync_orchestration_state_from_continuity_fn": sync}
        )
    from_dict_mock.assert_called()
    assert sync_calls["n"] >= 1


@pytest.mark.asyncio
async def test_agent_exception_fail() -> None:
    st = _MiniSt()

    class BoomAgent:
        async def on_messages(self, *_a, **_kw):
            raise ValueError("llm down")

    actors: list[str] = []
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=BoomAgent(),
            parse_fn=lambda _r: (_v2_move(), ""),
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=actors,
            get_cm=lambda: _FakeCM(),
        )
    )
    assert out is None
    assert actors == ["Alice"]


@pytest.mark.asyncio
async def test_continuity_disabled_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    raw = __import__("json").dumps(_v2_move())
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue([raw]),
            parse_fn=lambda r: (__import__("json").loads(r), ""),
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=[],
            get_cm=lambda: _FakeCM(scene_present=False),
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.continuity_applied_in_execute is False


@pytest.mark.asyncio
async def test_parse_terminal_fail_final_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    actors: list[str] = []
    out = await run_character_attempt_phase(
        **_base_kwargs(
            st=st,
            agent=_FakeAgentQueue(["x"]),
            parse_fn=lambda _r: (None, "bad"),
            validate_fn=lambda *_a, **_k: (True, ""),
            actors_failed=actors,
            get_cm=lambda: _FakeCM(),
            max_character_attempts=1,
        )
    )
    assert out is None
    assert actors == ["Alice"]
