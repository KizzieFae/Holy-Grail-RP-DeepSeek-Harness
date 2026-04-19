"""Tests for Audit V2 deterministic envelope, escalation policy, and LLM skip payloads."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_v2_deterministic import (
    build_character_audit_v2_deterministic,
    build_narrator_audit_v2_deterministic,
    build_prose_audit_v2_deterministic,
    count_quoted_segments,
)
from audit_v2_escalation_policy import (
    DIMENSION_AGGREGATE_NOT_APPLICABLE,
    compute_escalation_for_layer,
)
from audit_v2_llm import build_llm_skipped_payload, run_audit_v2_llm


def test_character_v2_deterministic_has_checks_and_escalation() -> None:
    move = {
        "action": "nods",
        "dialogue": "Yes.",
        "motivation": {
            "goal": "agree",
            "tactic": "nod",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }
    orch = {"recent_structured_moves": []}
    det = build_character_audit_v2_deterministic(
        move=move,
        next_actor="A",
        orchestration_state=orch,
    )
    assert det["schema_version"] == 2
    assert det["layer"] == "character_decision"
    assert len(det["checks"]) == 3
    check_ids = {c["check_id"] for c in det["checks"]}
    assert "char_ca1_motivation_action" not in check_ids
    assert "char_ca2_dialogue_action" not in check_ids
    mp = next(
        c for c in det["checks"] if c["check_id"] == "char_masked_progression_strict"
    )
    assert mp["result"] == "pass"
    assert mp["payload"].get("observation") == "skipped"
    assert all("result" in c for c in det["checks"])
    assert "intra_move_summary" in det
    summary = det["intra_move_summary"]
    assert summary["intra_move_aggregate"] == det["escalation"]["dimension_aggregate"][
        "character_intra_move_coherence"
    ]
    assert summary["intra_move_aggregate"] == DIMENSION_AGGREGATE_NOT_APPLICABLE
    assert summary["pattern"] == "intra_move_not_applicable"
    esc = det["escalation"]
    assert "qualified" in esc
    assert "reasons" in esc
    assert "dimension_aggregate" in esc


def test_llm_skipped_when_disabled_carries_would_escalate() -> None:
    reasons = [{"code": "border_band", "dimension_id": "x", "layer": "l"}]
    p = build_llm_skipped_payload(
        llm_audit_enabled=False,
        escalation_qualified=True,
        escalation_reasons=reasons,
    )
    assert p["status"] == "skipped"
    assert p["skip_reason"] == "llm_disabled"
    assert p["would_escalate"] is True
    assert p["escalation_reasons_if_enabled"] == reasons


def test_llm_skipped_when_no_escalation() -> None:
    p = build_llm_skipped_payload(
        llm_audit_enabled=True,
        escalation_qualified=False,
        escalation_reasons=[],
    )
    assert p["status"] == "skipped"
    assert p["skip_reason"] == "no_escalation_required"
    assert p["would_escalate"] is False


def test_same_dimension_conflict_triggers_escalation() -> None:
    """Fail from strict overlap + pass from an unregistered check_id (defaults to pass)."""
    checks = [
        {
            "check_id": "nar_strict_action_overlap",
            "dimension_id": "narrator_action_grounding",
            "payload": {"action_token_overlap_ratio": 0.01, "action_empty": False},
        },
        {
            "check_id": "synthetic_grounding_pass_stub",
            "dimension_id": "narrator_action_grounding",
            "payload": {},
        },
    ]
    scored, esc, _ = compute_escalation_for_layer(layer="narrator_output", checks=checks)
    assert esc["qualified"] is True
    codes = {r["code"] for r in esc["reasons"]}
    assert "same_dimension_conflict" in codes
    assert any(r["dimension_id"] == "narrator_action_grounding" for r in esc["reasons"])


def test_compound_intra_move_ambiguity_when_repetition_border() -> None:
    checks = [
        {
            "check_id": "char_ca4_repetition",
            "dimension_id": "character_structural_repetition",
            "payload": {"band": "moderate", "prior_turns_compared": 1},
        },
        {
            "check_id": "char_ca7_declared_fields",
            "dimension_id": "character_declared_pressure_fields",
            "payload": {"classification": "none", "fields_present": []},
        },
    ]
    _, esc, extras = compute_escalation_for_layer(
        layer="character_decision", checks=checks
    )
    codes = [r["code"] for r in esc["reasons"]]
    # CA1/CA2 no longer drive intra-move fail; compound cannot qualify (#42).
    assert "compound_intra_move_ambiguity" not in codes
    assert "border_band" in codes
    assert esc["qualified"] is True
    assert "intra_move_summary" in extras
    assert (
        esc["dimension_aggregate"]["character_intra_move_coherence"]
        == DIMENSION_AGGREGATE_NOT_APPLICABLE
    )


def test_compound_blocked_when_repetition_fail_only() -> None:
    checks = [
        {
            "check_id": "char_ca4_repetition",
            "dimension_id": "character_structural_repetition",
            "payload": {"band": "high", "prior_turns_compared": 2},
        },
        {
            "check_id": "char_ca7_declared_fields",
            "dimension_id": "character_declared_pressure_fields",
            "payload": {"classification": "none", "fields_present": []},
        },
    ]
    _, esc, _ = compute_escalation_for_layer(layer="character_decision", checks=checks)
    assert not any(
        r.get("code") == "compound_intra_move_ambiguity" for r in esc["reasons"]
    )


def test_count_quoted_segments_regex() -> None:
    assert count_quoted_segments('Say "a" and "b" now') == 2
    assert count_quoted_segments('Say "a" now') == 1
    assert count_quoted_segments("no ascii dquotes") == 0


def test_char_ca1_ca2_never_emitted_in_character_deterministic() -> None:
    """Issue #44: removed CA1/CA2 checks must not appear in current deterministic output."""
    det = build_character_audit_v2_deterministic(
        move={"action": "nods", "dialogue": "Yes.", "motivation": {"goal": "agree"}},
        next_actor="A",
        orchestration_state={"recent_structured_moves": []},
    )
    ids = {c["check_id"] for c in det["checks"]}
    assert "char_ca1_motivation_action" not in ids
    assert "char_ca2_dialogue_action" not in ids


def test_nar_scope_proxy_deprecated_does_not_border_escalate() -> None:
    """GitHub #9: scope proxy metrics may show passes_bar false; tri-state must not gate."""
    scored, esc, _ = compute_escalation_for_layer(
        layer="narrator_output",
        checks=[
            {
                "check_id": "nar_strict_action_overlap",
                "dimension_id": "narrator_action_grounding",
                "payload": {"action_token_overlap_ratio": 0.2, "action_empty": False},
            },
            {
                "check_id": "nar_environment_cue",
                "dimension_id": "narrator_environment_cue",
                "payload": {
                    "environment_event_present": False,
                    "token_hits_in_render": 0,
                },
            },
            {
                "check_id": "nar_scope_proxy",
                "dimension_id": "narrator_scope_proxy",
                "payload": {
                    "passes_bar": False,
                    "other_cast_names_found": ["OtherCast"],
                },
            },
        ],
    )
    scope_rows = [r for r in scored if r.get("check_id") == "nar_scope_proxy"]
    assert len(scope_rows) == 1
    assert scope_rows[0]["result"] == "pass"
    assert esc["qualified"] is False
    assert not any(
        r.get("code") == "border_band" and r.get("check_id") == "nar_scope_proxy"
        for r in esc["reasons"]
    )


def test_scope_proxy_context_previous_turn() -> None:
    det1 = build_narrator_audit_v2_deterministic(
        next_actor="A",
        move={"action": "nods", "dialogue": "Hi"},
        decision={"environment_event": ""},
        rendered_final="A looked at B.",
        char_names=["A", "B"],
        acting_display_name="A",
        previous_narrator_other_cast_names=None,
    )
    assert det1["scope_proxy_context"]["same_other_cast_set_as_previous_narrator_turn"] is None
    prev = frozenset(["B"])
    det2 = build_narrator_audit_v2_deterministic(
        next_actor="A",
        move={"action": "nods", "dialogue": "Hi"},
        decision={"environment_event": ""},
        rendered_final="A looked at B again.",
        char_names=["A", "B"],
        acting_display_name="A",
        previous_narrator_other_cast_names=prev,
    )
    assert det2["scope_proxy_context"]["same_other_cast_set_as_previous_narrator_turn"] is True


def test_prose_attribution_ambiguity_hint_active() -> None:
    # First-quote window must omit acting_display_name tokens; exact dialogue substring.
    det = build_prose_audit_v2_deterministic(
        next_actor="ZebraActor",
        move={"action": "nods", "dialogue": "One."},
        rendered_final=(
            "The room was quiet before anyone spoke. Then suddenly \"One.\" "
            'A moment later "Two."'
        ),
        prior_assistant_content=None,
        acting_display_name="ZebraActor",
    )
    hint = det["attribution_ambiguity_hint"]
    assert hint["active"] is True
    assert hint["signals"]["quoted_segment_count"] >= 2
    assert hint["level"] == "possible_speaker_ambiguity"


@pytest.mark.asyncio
async def test_run_audit_v2_llm_completed_with_mock_agent() -> None:
    payload = (
        '{"findings":[],"confidence":1.0,"confidence_bucket":"high","uncertainty":"none",'
        '"verdict_vs_deterministic":null}'
    )
    fake_result = SimpleNamespace(
        chat_message=SimpleNamespace(content=payload),
    )
    mock_agent = MagicMock()
    mock_agent.on_messages = AsyncMock(return_value=fake_result)

    with patch("audit_v2_llm.AssistantAgent", return_value=mock_agent):
        out = await run_audit_v2_llm(
            layer="character_decision",
            model_client=object(),
            cancellation_token=object(),
            user_prompt="test",
        )
    assert out["status"] == "completed"
    assert out["confidence"] == 1.0
    assert "model_meta" in out
