from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from narrator_audits_v1 import (
    build_narrator_output_audit_v1,
    build_narrator_validation_audit_v1,
    build_prose_dialogue_audit_v1,
)


def test_validation_audit_derived_both_fallbacks() -> None:
    out = build_narrator_validation_audit_v1(
        narrator_raw='She said "hello"',
        rendered_after_render_call="fallback text",
        rendered_final="fallback final",
        deterministic_dialogue_fallback_applied=True,
        narrator_semantic_assessment={"should_use_fallback": True},
        semantic_fallback_effective=True,
        semantic_fallback_llm_requested=True,
        semantic_fallback_deterministic_critical=False,
    )
    assert out["derived"]["fallback_types_ordered"] == [
        "dialogue_missing",
        "semantic_failure",
    ]
    assert out["derived"]["fallback_type"] == "dialogue_missing"
    assert out["derived"]["output_replaced"] is True
    assert out["derived"]["original_vs_final_changed"] is True
    assert out["derived"]["semantic_fallback_effective"] is True
    assert out["derived"]["semantic_fallback_llm_requested"] is True
    assert out["derived"]["semantic_fallback_deterministic_critical"] is False


def test_validation_audit_semantic_only() -> None:
    out = build_narrator_validation_audit_v1(
        narrator_raw="model",
        rendered_after_render_call="model",
        rendered_final="fallback",
        deterministic_dialogue_fallback_applied=False,
        narrator_semantic_assessment={"should_use_fallback": True},
        semantic_fallback_effective=True,
        semantic_fallback_llm_requested=True,
        semantic_fallback_deterministic_critical=False,
    )
    assert out["derived"]["fallback_types_ordered"] == ["semantic_failure"]
    assert out["derived"]["fallback_type"] == "semantic_failure"


def test_validation_audit_deterministic_semantic_effective_without_llm_flag() -> None:
    out = build_narrator_validation_audit_v1(
        narrator_raw="x",
        rendered_after_render_call="x",
        rendered_final="y",
        deterministic_dialogue_fallback_applied=False,
        narrator_semantic_assessment={
            "valid": False,
            "should_use_fallback": False,
        },
        semantic_fallback_effective=True,
        semantic_fallback_llm_requested=False,
        semantic_fallback_deterministic_critical=True,
    )
    assert out["derived"]["fallback_types_ordered"] == ["semantic_failure"]
    assert out["derived"]["semantic_fallback_effective"] is True
    assert out["derived"]["semantic_fallback_llm_requested"] is False
    assert out["derived"]["semantic_fallback_deterministic_critical"] is True


def test_output_audit_empty_environment_passes() -> None:
    out = build_narrator_output_audit_v1(
        next_actor="A",
        move={"action": "nods", "dialogue": ""},
        decision={"environment_event": ""},
        rendered_final="A nodded.",
        char_names=["A", "B"],
        acting_display_name="A",
    )
    assert (
        out["checks"]["environment_event_heuristic"]["status"] == "cue_empty"
    )
    assert out["checks"]["environment_event_heuristic"]["passes_bar"] is True


def test_prose_exact_quote_detection() -> None:
    out = build_prose_dialogue_audit_v1(
        next_actor="Celina",
        move={"action": "spoke", "dialogue": "Hi."},
        rendered_final='Celina smiled. "Hi."',
        prior_assistant_content=None,
        acting_display_name="Celina",
    )
    assert (
        out["checks"]["dialogue_integration_proxy"]["exact_dialogue_quoted_in_render"]
        is True
    )
