"""Issue #250 — schema-recoverable parse repair lane (classifier, deterministic repair, runner)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_move_ingress import (  # noqa: E402
    classify_ingress_failure,
    has_meaningful_rp_body,
    ingest_character_move_json_object,
    parse_character_move_content_to_v2,
    parse_character_move_for_attempt,
)
from issue240_semantic_evaluation import (  # noqa: E402
    attempt_deterministic_ingress_repair,
    extract_parse_repair_semantic_snapshot,
)
import turn_runner_character_attempt as tca  # noqa: E402
from turn_runner_character_attempt import (  # noqa: E402
    CharacterAttemptOutcome,
    run_character_attempt_phase,
)


def _motivation() -> dict[str, str]:
    return {
        "goal": "leave",
        "tactic": "exit",
        "emotional_driver": "pressure",
        "risk_level": "medium",
    }


def _move_908_p01_malformed() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "steps into the hall and pulls the door shut"},
        ],
        "motivation": _motivation(),
        "semantic_evaluation": {
            "decision": "covered_change",
            "proposals": [
                {
                    "kind": "off_focal",
                    "reason": "Direct instruction to leave the dorm room",
                }
            ],
        },
    }


def _move_910_r7t3_malformed() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "backs toward the doorway"},
            {"type": "speech", "dialogue": "I'm done here."},
        ],
        "motivation": _motivation(),
        "semantic_evaluation": {
            "decision": "covered_change",
            "proposals": [
                {
                    "kind": "off_focal",
                    "strategy": "Maintain withdrawn position",
                    "rationale": "Already at the margin",
                }
            ],
        },
    }


def test_first_pass_still_rejects_908_p01_malformed() -> None:
    m, err = ingest_character_move_json_object(_move_908_p01_malformed())
    assert m is None
    assert "unknown fields" in (err or "")


def test_classify_schema_recoverable_908_p01() -> None:
    loose = _move_908_p01_malformed()
    _, err = ingest_character_move_json_object(loose)
    assert classify_ingress_failure(err or "", loose) == "schema_recoverable"


def test_classify_unrecoverable_invalid_json() -> None:
    assert (
        classify_ingress_failure("Invalid JSON: expecting value", None)
        == "unrecoverable"
    )


def test_deterministic_repair_908_p01_preserves_semantics() -> None:
    loose = _move_908_p01_malformed()
    snap = extract_parse_repair_semantic_snapshot(loose)
    assert snap["semantic_decision"] == "covered_change"
    assert snap["proposal_kinds"] == ["off_focal"]
    repaired, err = attempt_deterministic_ingress_repair(
        loose, acting_character="willow_reeves"
    )
    assert not err, err
    assert repaired is not None
    ev = repaired.get("semantic_evaluation")
    assert isinstance(ev, dict)
    assert ev.get("decision") == "covered_change"
    props = ev.get("proposals")
    assert isinstance(props, list) and props[0].get("kind") == "off_focal"
    assert props[0].get("character") == "willow_reeves"
    assert repaired["beats"][0]["action"] == loose["beats"][0]["action"]


def test_deterministic_repair_910_r7t3_shape() -> None:
    loose = _move_910_r7t3_malformed()
    repaired, err = attempt_deterministic_ingress_repair(
        loose, acting_character="willow_reeves"
    )
    assert not err, err
    assert repaired is not None
    ev = repaired["semantic_evaluation"]
    assert ev["decision"] == "covered_change"
    assert ev["proposals"][0]["kind"] == "off_focal"
    assert "strategy" not in ev["proposals"][0]


def test_parse_for_attempt_schema_recoverable() -> None:
    raw = json.dumps(_move_908_p01_malformed())
    move, err, fc, loose = parse_character_move_for_attempt(raw)
    assert move is None
    assert fc == "schema_recoverable"
    assert isinstance(loose, dict)


def _move_schema_extra_on_evaluation() -> dict:
    """Schema-only flaw without proposals (avoids legality gate in unit test)."""
    return {
        "move_schema_version": 2,
        "beats": [{"type": "speech", "dialogue": "I'm leaving."}],
        "motivation": _motivation(),
        "semantic_evaluation": {
            "decision": "no_covered_change",
            "operator_note": "forbidden helper",
        },
    }


@pytest.mark.asyncio
async def test_runner_deterministic_repair_skips_second_llm_call() -> None:
    """Schema-recoverable malformed move: one agent call, repair lane accepts."""
    raw = json.dumps(_move_schema_extra_on_evaluation())
    agent_calls = {"n": 0}

    class FakeAgent:
        async def on_messages(self, _messages, _cancellation_token):
            agent_calls["n"] += 1
            return SimpleNamespace(chat_message=SimpleNamespace(content=raw))

    st = SimpleNamespace(session_state={"chat_history": [], "selector_decisions": []})
    audit_meta: dict = {}

    class CapturingLogger:
        def create_entry(self, **kwargs):
            return kwargs

        def log_bot_interaction(self, entry):
            audit_meta.update(entry.get("metadata", {}))

    outcome = await run_character_attempt_phase(
        st_module=st,
        agent=FakeAgent(),
        next_actor="willow_reeves",
        char_names=["willow_reeves"],
        decision={"next_actor": "willow_reeves"},
        trigger_text="t",
        user_name="Alex",
        cancellation_token=object(),
        round_number=1,
        turn_number=3,
        orchestration_state={"scene_state": {}},
        actors_failed_this_round=[],
        state_manager=None,
        task_prompt="base prompt",
        character_summary_block_audit={},
        parse_character_move_fn=tca._default_parse_character_move,
        get_continuity_manager_fn=lambda: None,
        is_audit_enabled_fn=lambda: True,
        is_llm_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: CapturingLogger(),
        get_audit_context_fn=lambda: ("o", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _s: {},
        get_character_scene_audit_context_fn=lambda _n, _s: {},
        validate_bot_response_fn=lambda *_a, **_k: (True, ""),
        get_model_client_fn=lambda: object(),
        assess_presence_violation_semantics_fn=AsyncMock(return_value=None),
        should_override_presence_rejection_fn=lambda *_a, **_k: False,
        log_turn_failure_fn=lambda **_k: None,
        sync_orchestration_state_from_continuity_fn=lambda: None,
        effective_user_trigger="",
        assess_proposal_beat_contradiction_fn=AsyncMock(
            return_value={"status": "aligned", "skipped": True}
        ),
    )
    assert isinstance(outcome, CharacterAttemptOutcome)
    assert agent_calls["n"] == 1
    te = outcome.turn_execution_metadata
    assert te.get("retry_mode") == "deterministic_repair"
    assert te.get("first_attempt_semantic_decision") == "no_covered_change"
    assert te.get("semantic_decision_changed") is False


def test_has_meaningful_rp_body_requires_beats_and_motivation() -> None:
    assert has_meaningful_rp_body(_move_908_p01_malformed()) is True
    bad = dict(_move_908_p01_malformed())
    bad.pop("beats")
    assert has_meaningful_rp_body(bad) is False


def test_unrecoverable_still_uses_legacy_parse_path() -> None:
    move, err = parse_character_move_content_to_v2("not json at all {{{")
    assert move is None
    assert err
    _, err2, fc, _ = parse_character_move_for_attempt("not json at all {{{")
    assert fc == "unrecoverable"
