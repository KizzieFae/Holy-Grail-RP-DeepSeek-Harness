"""GitHub #234 — proposal-path certification (Execution Group 1: D1–D5)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import turn_runner_character_attempt as tca
from audit_semantic_proposal_decision import (
    ACCEPTED_PROPOSAL_BATCH_NOTE,
    build_semantic_proposal_decision,
)
from continuity_manager import ContinuityManager
from continuity_semantic_proposals import (
    REASON_MUST_REMAIN_OFF_FOCAL,
    ContinuityProposalLegalityError,
    ProposalAuthorityOutcome,
    evaluate_proposal_legality,
)
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from response_validation_proposal_legality import PROPOSAL_LEGALITY_TAG
from turn_runner_character_attempt import CharacterAttemptOutcome, run_character_attempt_phase


def _minimal_v2(**extra: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "steps toward the kitchen doorway"}],
        "motivation": {
            "goal": "step off-focal briefly",
            "tactic": "withdraw",
            "emotional_driver": "guarded",
            "risk_level": "low",
        },
    }
    base.update(extra)
    return base


# --- D1 Accept ---


def test_d1_accept_legal_off_focal_commits_scene_state() -> None:
    actor = "Celina"
    other = "Ayame"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="apartment_entry",
        opening_description="Cert.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    move = _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": actor}],
    )
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert actor not in mgr.scene_state.present_characters
    assert actor in mgr.scene_state.offstage_characters


def test_d1_accept_legality_eval_before_commit() -> None:
    actor = "Alice"
    ctx = evaluate_proposal_legality(
        _minimal_v2(semantic_proposals=[{"kind": "off_focal", "character": actor}]),
        acting_character=actor,
        scene_state={"present_characters": [actor, "Bob"]},
    )
    assert ctx.outcome == ProposalAuthorityOutcome.ACCEPT
    assert ctx.accepted_proposals


# --- D2 Reject ---


def test_d2_reject_must_remain_no_covered_commit() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    mgr.scene_state.character_presence_constraints = {actor: "must_remain"}
    complete_setup_seam_for_test_manager(mgr)
    before = list(mgr.scene_state.present_characters)
    with pytest.raises(ContinuityProposalLegalityError):
        mgr.process_turn(
            acting_character=actor,
            move=_minimal_v2(
                semantic_proposals=[{"kind": "off_focal", "character": actor}],
            ),
            director_decision={"next_actor": other},
            other_characters=[other],
        )
    assert list(mgr.scene_state.present_characters) == before


def test_d2_reject_reason_must_remain_off_focal() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
        ),
        acting_character="Alice",
        scene_state={
            "present_characters": ["Alice"],
            "character_presence_constraints": {"Alice": "must_remain"},
        },
    )
    assert ctx.outcome == ProposalAuthorityOutcome.REJECT
    assert ctx.reason_code == REASON_MUST_REMAIN_OFF_FOCAL


# --- D3 No proposal + suppression ---


def test_d3_no_proposal_allows_process_turn_without_covered_commit() -> None:
    actor = "Ayame"
    other = "Celina"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    before_present = list(mgr.scene_state.present_characters)
    with patch(
        "continuity_scene_state_update.manager_apply_canonical_exit_offstage_transition_scratch"
    ) as mock_exit:
        mgr.process_turn(
            acting_character=actor,
            move=_minimal_v2(),
            director_decision={"next_actor": other, "tags": ["exit"]},
            other_characters=[other],
        )
        mock_exit.assert_not_called()
    assert list(mgr.scene_state.present_characters) == before_present


def test_d3_no_proposal_authority_outcome() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(),
        acting_character="Alice",
        scene_state={"present_characters": ["Alice"]},
    )
    assert ctx.outcome == ProposalAuthorityOutcome.NO_PROPOSAL


# --- D4 Attempt envelope ---


class _FakeSceneState:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class _TrackingCM:
    def __init__(self, scene: dict[str, Any]) -> None:
        self.scene_state = _FakeSceneState(scene)
        self.turn_counter = 0
        self.turn_metadata_by_index: dict[int, dict[str, Any]] = {0: {}}
        self.process_turn_calls = 0

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

    def active_excursion_character_ids(self) -> list[str]:
        return []

    def process_turn(self, **_kwargs: Any) -> None:
        self.process_turn_calls += 1
        self.turn_counter += 1


class _FakeAgentQueue:
    def __init__(self, contents: list[str]) -> None:
        self._q = list(contents)

    async def on_messages(self, _messages: Any, _cancellation_token: Any) -> Any:
        return SimpleNamespace(chat_message=SimpleNamespace(content=self._q.pop(0)))


class _MiniSt:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {
            "chat_history": [],
            "selector_decisions": [],
            "scene_grounding": None,
            "simulation_scenario_id": "cert_i234_proposal_accept_off_focal",
            "progression_enforcement_disabled": True,
        }


def _illegal_must_remain_move() -> dict[str, Any]:
    return _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
    )


def _attempt_kwargs(
    *,
    st: _MiniSt,
    agent: _FakeAgentQueue,
    cm: _TrackingCM,
    moves: list[dict[str, Any]],
    actors_failed: list[str],
    max_attempts: int = 2,
    log_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    raw_queue = [json.dumps(m) for m in moves]
    idx = {"i": 0}

    def parse_fn(_raw: str) -> tuple[dict[str, Any], str]:
        move = moves[idx["i"]]
        idx["i"] += 1
        return move, ""

    def log_failure(**kw: Any) -> None:
        if log_failures is not None:
            log_failures.append(kw)

    return {
        "st_module": st,
        "agent": _FakeAgentQueue(raw_queue),
        "next_actor": "Alice",
        "char_names": ["Alice"],
        "decision": {"next_actor": "Alice"},
        "trigger_text": "hi",
        "user_name": "User",
        "cancellation_token": object(),
        "round_number": 1,
        "turn_number": 1,
        "orchestration_state": {"scene_state": cm.scene_state.to_dict()},
        "actors_failed_this_round": actors_failed,
        "state_manager": None,
        "task_prompt": "prompt",
        "character_summary_block_audit": {},
        "parse_character_move_fn": parse_fn,
        "get_continuity_manager_fn": lambda: cm,
        "is_audit_enabled_fn": lambda: False,
        "is_llm_audit_enabled_fn": lambda: False,
        "get_audit_logger_fn": lambda: None,
        "get_audit_context_fn": lambda: ("Alice", 1, 1, 1),
        "get_scene_audit_logging_kwargs_fn": lambda _s: {},
        "get_character_scene_audit_context_fn": lambda _n, _s: {},
        "validate_bot_response_fn": lambda *_a, **_k: (True, ""),
        "get_model_client_fn": lambda: object(),
        "assess_presence_violation_semantics_fn": AsyncMock(return_value=None),
        "should_override_presence_rejection_fn": lambda *_a, **_k: False,
        "assess_proposal_beat_contradiction_fn": AsyncMock(
            return_value={"status": "aligned", "reason_code": ""}
        ),
        "log_turn_failure_fn": log_failure,
        "sync_orchestration_state_from_continuity_fn": lambda: None,
        "effective_user_trigger": "hi",
        "max_character_attempts": max_attempts,
    }


@pytest.mark.asyncio
async def test_d4_legality_retry_then_forfeit_no_process_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _TrackingCM(
        {
            "present_characters": ["Alice"],
            "character_presence_constraints": {"Alice": "must_remain"},
        }
    )
    actors: list[str] = []
    failures: list[dict[str, Any]] = []
    illegal = _illegal_must_remain_move()

    out = await run_character_attempt_phase(
        **_attempt_kwargs(
            st=st,
            agent=_FakeAgentQueue([json.dumps(illegal), json.dumps(illegal)]),
            cm=cm,
            moves=[illegal, illegal],
            actors_failed=actors,
            max_attempts=2,
            log_failures=failures,
        )
    )
    assert out is None
    assert "Alice" in actors
    assert cm.process_turn_calls == 0
    assert any(
        PROPOSAL_LEGALITY_TAG in str(f.get("reason", "")) for f in failures
    )
    retry_stages = [f.get("stage") for f in failures]
    assert "validation_proposal_legality_retry" in retry_stages
    assert any(
        "proposal legality" in d.lower()
        for d in st.session_state["selector_decisions"]
    )


@pytest.mark.asyncio
async def test_d4_legality_retry_then_no_proposal_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _TrackingCM(
        {
            "present_characters": ["Alice", "Bob"],
            "character_presence_constraints": {"Alice": "must_remain"},
        }
    )
    illegal = _illegal_must_remain_move()
    legal_no_proposal = _minimal_v2()

    out = await run_character_attempt_phase(
        **_attempt_kwargs(
            st=st,
            agent=_FakeAgentQueue([json.dumps(illegal), json.dumps(legal_no_proposal)]),
            cm=cm,
            moves=[illegal, legal_no_proposal],
            actors_failed=[],
            max_attempts=3,
        )
    )
    assert isinstance(out, CharacterAttemptOutcome)
    assert out.turn_execution_metadata["proposal_legality_retry_triggered"] is True
    assert cm.process_turn_calls == 1
    assert out.continuity_applied_in_execute is True


@pytest.mark.asyncio
async def test_d4_forfeit_audit_reject_omits_commit_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tca, "build_character_audit_v1", lambda **kw: {"v1": True})
    monkeypatch.setattr(tca, "log_character_turn_audit", lambda **kw: None)

    st = _MiniSt()
    cm = _TrackingCM(
        {
            "present_characters": ["Alice"],
            "character_presence_constraints": {"Alice": "must_remain"},
        }
    )
    failures: list[dict[str, Any]] = []
    illegal = _illegal_must_remain_move()

    await run_character_attempt_phase(
        **_attempt_kwargs(
            st=st,
            agent=_FakeAgentQueue([json.dumps(illegal)]),
            cm=cm,
            moves=[illegal],
            actors_failed=[],
            max_attempts=1,
            log_failures=failures,
        )
    )
    terminal = [
        f
        for f in failures
        if f.get("stage") == "validation" or f.get("metadata", {}).get("semantic_proposal_decision", {}).get("attempt", {}).get("terminal")
    ]
    assert failures
    meta = failures[-1].get("metadata") or {}
    decision = meta.get("semantic_proposal_decision") or {}
    if decision:
        assert decision["batch"]["authority_outcome"] == "reject"
        assert "commit_proof_pointer" not in decision
        assert decision.get("lifecycle_phase") in ("failed_attempt", "pre_commit")


# --- D5 Audit alignment ---


def test_d5_accept_audit_matches_runtime_authority() -> None:
    actor = "Celina"
    proposal = {"kind": "off_focal", "character": actor}
    from continuity_semantic_proposals import ProposalAuthorityContext

    ctx = ProposalAuthorityContext(
        outcome=ProposalAuthorityOutcome.ACCEPT,
        accepted_proposals=(proposal,),
    )
    move = _minimal_v2(semantic_proposals=[proposal])
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=ctx,
        lifecycle_phase="committed_attempt",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        continuity_turn_index=2,
        include_commit_proof_pointer=True,
        process_turn_ran=True,
    )
    assert record["batch"]["authority_outcome"] == "accept"
    assert record["accepted_proposal_batch"] == [proposal]
    assert record["accepted_proposal_batch_note"] == ACCEPTED_PROPOSAL_BATCH_NOTE
    assert record["commit_proof_pointer"]["scene_state_field"] == (
        "context_snapshot.scene_state_after"
    )
    assert record["doctrine"]["reconstruction_suppressed"] is True


def test_d5_reject_forfeit_audit_no_commit_proof() -> None:
    from continuity_semantic_proposals import ProposalAuthorityContext

    ctx = ProposalAuthorityContext(
        outcome=ProposalAuthorityOutcome.REJECT,
        reason_code=REASON_MUST_REMAIN_OFF_FOCAL,
        reason_detail="must_remain",
    )
    move = _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
    )
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=ctx,
        lifecycle_phase="failed_attempt",
        attempt_index=1,
        terminal=True,
        retry_class="proposal_legality",
        legality_evaluated=True,
        process_turn_ran=False,
    )
    assert record["batch"]["authority_outcome"] == "reject"
    assert record["batch"]["covered_compile_authorized"] is False
    assert "accepted_proposal_batch" not in record
    assert "commit_proof_pointer" not in record


def test_d5_no_proposal_audit_shape() -> None:
    from continuity_semantic_proposals import ProposalAuthorityContext

    record = build_semantic_proposal_decision(
        move=_minimal_v2(),
        proposal_authority_context=ProposalAuthorityContext(
            outcome=ProposalAuthorityOutcome.NO_PROPOSAL
        ),
        lifecycle_phase="committed_attempt",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        process_turn_ran=True,
    )
    assert record["batch"]["authority_outcome"] == "no_proposal"
    assert "accepted_proposal_batch" not in record
