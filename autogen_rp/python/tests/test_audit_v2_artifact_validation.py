"""Validation tests: V2 artifacts, LLM input boundaries, serialization (locked model checks)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_v2_deterministic import (
    assemble_audit_v2_layer_block,
    build_character_audit_v2_deterministic,
    format_move_for_llm_closed,
)
from audit_v2_llm import (
    build_character_llm_prompt,
    build_narrator_llm_prompt,
    build_prose_llm_prompt,
    build_llm_skipped_payload,
)


def test_audit_v2_character_layer_shape() -> None:
    det = build_character_audit_v2_deterministic(
        move={"action": "nods", "dialogue": "Hi."},
        next_actor="X",
        orchestration_state={},
    )
    llm = build_llm_skipped_payload(
        llm_audit_enabled=False,
        escalation_qualified=True,
        escalation_reasons=[{"code": "border_band", "layer": "character_decision"}],
    )
    block = assemble_audit_v2_layer_block(deterministic=det, llm=llm)
    assert set(block.keys()) == {"deterministic", "escalation", "llm"}
    assert block["deterministic"]["layer"] == "character_decision"
    assert block["deterministic"]["schema_version"] == 2
    assert "intra_move_summary" in block["deterministic"]
    assert "qualified" in block["escalation"]
    assert block["llm"]["status"] == "skipped"
    meta = {"schema_version": 1, "character_decision": block}
    json.dumps(meta)  # serializable


def test_audit_v2_llm_states_roundtrip_json() -> None:
    skipped = build_llm_skipped_payload(
        llm_audit_enabled=False,
        escalation_qualified=True,
        escalation_reasons=[{"code": "x"}],
    )
    completed = {
        "status": "completed",
        "findings": [],
        "confidence": 0.5,
        "confidence_bucket": "medium",
        "uncertainty": "none",
        "model_meta": {"model_id": "m", "timestamp": "t"},
    }
    err = {
        "status": "error",
        "skip_reason": "llm_parse_or_call_failed",
        "error": "bad",
        "raw_response_excerpt": "",
    }
    for obj in (skipped, completed, err):
        json.loads(json.dumps(obj))


def test_character_llm_prompt_no_external_context_keys() -> None:
    """Prompt must not embed scene, issues, continuity, or full director decision."""
    move = {
        "action": "looks around",
        "dialogue": "Hello.",
        "motivation": {"goal": "g", "tactic": "t", "emotional_driver": "e", "risk_level": "low"},
    }
    reasons = [{"code": "border_band", "dimension_id": "character_intra_move_coherence"}]
    prompt = build_character_llm_prompt(
        move_json=format_move_for_llm_closed(move),
        escalation_reasons=reasons,
    )
    lower = prompt.lower()
    assert "scene_state" not in lower
    assert "scene_state_after" not in lower
    assert "issue_updates" not in lower
    assert "continuity_event" not in lower
    assert "director_decision" not in lower
    assert "STRUCTURED_MOVE_JSON:" in prompt
    assert "DETERMINISTIC_ESCALATION_REASONS:" in prompt


def test_narrator_llm_prompt_includes_only_allowed_inputs() -> None:
    move = {"action": "walks", "dialogue": "Hi"}
    prompt = build_narrator_llm_prompt(
        move_json=format_move_for_llm_closed(move),
        rendered_final="She walked. \"Hi\"",
        environment_event="Thunder rolls.",
        allowed_expansion_policy="POLICY_STUB",
        escalation_reasons=[],
    )
    assert "Thunder rolls." in prompt
    assert "POLICY_STUB" in prompt
    assert "She walked." in prompt
    lower = prompt.lower()
    assert "spotlight_history" not in lower
    assert "continuity_event" not in lower
    assert "scene_state" not in lower
    assert "director_decision" not in lower
    assert '"reason"' not in prompt


def test_prose_llm_prompt_surface_only() -> None:
    prompt = build_prose_llm_prompt(
        move_dialogue="Yes.",
        move_action_excerpt="nods",
        rendered_final="He nodded. \"Yes.\"",
        prior_assistant_excerpt="Earlier line.",
        acting_label="Bob",
        escalation_reasons=[],
    )
    assert "Earlier line." in prompt
    assert "Bob" in prompt
    low = prompt.lower()
    assert "scene_state" not in low
    assert "scene_state_after" not in low
    assert "issue_updates" not in low
    assert "director_decision" not in low


def test_log_narrator_render_audit_merges_audit_v2_metadata() -> None:
    from turn_runner_audit import log_narrator_render_audit

    captured: list[dict] = []

    class _Logger:
        def create_entry(self, **kwargs):
            captured.append(kwargs)
            return kwargs

        def log_bot_interaction(self, _entry) -> None:
            pass

    audit_v2 = {
        "schema_version": 1,
        "narrator_output": {"deterministic": {}, "escalation": {}, "llm": {}},
        "prose_dialogue": {"deterministic": {}, "escalation": {}, "llm": {}},
    }

    log_narrator_render_audit(
        continuity_manager=None,
        next_actor="A",
        move={"action": "x", "dialogue": ""},
        decision={"environment_event": "", "reason": "r"},
        rendered="out",
        narrator_raw="raw",
        narrator_prompt="p",
        narrator_summary_block_audit={},
        narrator_semantic_assessment=None,
        narrator_output_audit_v1={"schema_version": 1},
        narrator_validation_audit_v1={},
        prose_dialogue_audit_v1={},
        round_number=1,
        turn_number=1,
        audit_v2=audit_v2,
        effective_user_trigger="",
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _s: {},
        get_character_scene_audit_context_fn=lambda _n, _k: {},
    )

    assert len(captured) == 1
    meta = captured[0]["metadata"]
    assert meta.get("narrator_output_audit_v1") == {"schema_version": 1}
    assert meta.get("audit_v2") == audit_v2


def test_log_narrator_render_audit_parsed_output_rendered_is_full_prose() -> None:
    """Issue #65: narrator parsed_output.rendered must not be capped (~500 + ...)."""
    from turn_runner_audit import log_narrator_render_audit

    captured: list[dict] = []

    class _Logger:
        def create_entry(self, **kwargs):
            captured.append(kwargs)
            return kwargs

        def log_bot_interaction(self, _entry) -> None:
            pass

    long_rendered = "word " * 200  # 1000+ chars, well above former cap
    assert len(long_rendered) > 500

    nv1 = {
        "schema_version": 1,
        "observed": {"rendered_final": long_rendered},
    }

    log_narrator_render_audit(
        continuity_manager=None,
        next_actor="A",
        move={"action": "x", "dialogue": ""},
        decision={"environment_event": "", "reason": "r"},
        rendered=long_rendered,
        narrator_raw="raw",
        narrator_prompt="p",
        narrator_summary_block_audit={},
        narrator_semantic_assessment=None,
        narrator_output_audit_v1={"schema_version": 1},
        narrator_validation_audit_v1=nv1,
        prose_dialogue_audit_v1={},
        round_number=1,
        turn_number=1,
        audit_v2=None,
        effective_user_trigger="",
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 1, 1),
        get_scene_audit_logging_kwargs_fn=lambda _s: {},
        get_character_scene_audit_context_fn=lambda _n, _k: {},
    )

    assert len(captured) == 1
    po = captured[0]["parsed_output"]
    assert po["rendered"] == long_rendered
    assert not po["rendered"].endswith("...")
    meta = captured[0]["metadata"]
    assert meta["rendered_length"] == len(long_rendered)
    assert meta["narrator_validation_audit_v1"]["observed"]["rendered_final"] == (
        long_rendered
    )


def test_ca7_check_is_declared_fields_payload_only() -> None:
    move = {
        "action": "confronts",
        "dialogue": "",
        "tension_shift": "escalate",
        "consequences": ["threat"],
    }
    det = build_character_audit_v2_deterministic(
        move=move,
        next_actor="A",
        orchestration_state={"recent_structured_moves": []},
    )
    ca7 = next(c for c in det["checks"] if c["check_id"] == "char_ca7_declared_fields")
    lim = str(ca7["payload"].get("limitations", ""))
    assert "Move-emitted" in lim or "move" in lim.lower()
    assert "fields_present" in ca7["payload"] or "classification" in ca7["payload"]
    surf = det.get("ca7_surface")
    assert isinstance(surf, dict) and surf.get("active") is True
    assert surf.get("fields_present")
    block = assemble_audit_v2_layer_block(
        deterministic=det,
        llm=build_llm_skipped_payload(
            llm_audit_enabled=False,
            escalation_qualified=False,
            escalation_reasons=[],
        ),
    )
    assert "ca7_surface" in block["deterministic"]
