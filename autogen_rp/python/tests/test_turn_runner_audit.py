from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_logger_serialization import entry_to_light_dict

from turn_runner_audit import (
    _merge_character_audit_metadata,
    promote_character_binding_fields_for_audit_metadata,
    split_character_prompt_audit_for_metadata,
)


def test_split_character_prompt_audit_for_metadata() -> None:
    summary, has_bc, section = split_character_prompt_audit_for_metadata(
        {
            "summary_generation_eligible": True,
            "summary_blocks_generated_total": 0,
            "generated_summary_block_ids": [],
            "summary_blocks_available_count": 0,
            "available_summary_block_ids": [],
            "summary_blocks_selected_count": 0,
            "selected_summary_block_ids": [],
            "excluded_summary_block_ids": [],
            "selection_reason": "",
            "skipped_reason": "x",
            "fallback_used": False,
            "summary_limit": None,
            "has_binding_constraints": True,
            "scene_binding_constraints_section": "## BINDING\n- [assignment] a",
        }
    )
    assert "has_binding_constraints" not in summary
    assert "scene_binding_constraints_section" not in summary
    assert has_bc is True
    assert "BINDING" in section


def test_promote_character_binding_fields_for_audit_metadata() -> None:
    out = promote_character_binding_fields_for_audit_metadata(
        {
            "summary_blocks": {
                "selection_reason": "",
                "has_binding_constraints": False,
                "scene_binding_constraints_section": "",
            }
        }
    )
    assert out["has_binding_constraints"] is False
    assert out["scene_binding_constraints_section"] == ""
    assert out["summary_blocks"] == {"selection_reason": ""}


def test_entry_to_light_dict_exposes_binding_observability_for_character() -> None:
    sn = SimpleNamespace(
        timestamp="t",
        session_owner="o",
        session_number=1,
        round_number=1,
        turn_number=1,
        bot_name="Alice",
        bot_type="character",
        input_messages=[
            {"role": "system", "content": "intro\n## **BINDING CONSTRAINTS (HIGH PRIORITY)**\n"}
        ],
        raw_response="{}",
        parsed_output={},
        context_snapshot={},
        metadata={
            "has_binding_constraints": True,
            "scene_binding_constraints_section": "## **BINDING CONSTRAINTS (HIGH PRIORITY)**\n- [assignment] x",
        },
    )
    light = entry_to_light_dict(sn)
    assert light["has_binding_constraints"] is True
    assert "BINDING CONSTRAINTS" in light["scene_binding_constraints_section"]
    assert light["character_system_prompt_contains_binding_header"] is True
    assert light["character_system_prompt_length"] > 0


def test_merge_character_audit_metadata_includes_progression_note() -> None:
    merged = _merge_character_audit_metadata(
        base={},
        progression_advisory={
            "stall_score": 0.8,
            "progression_pressure": "high",
            "recommended_channels": ["physical_action"],
            "note": "Advance through a concrete change in state.",
            "stall_components": {"same_phase": True},
        },
    )

    assert merged["progression_advisory"]["note"] == (
        "Advance through a concrete change in state."
    )
    si = merged["signal_interpretation"]
    assert si["schema_version"] == 1
    assert si["signals"]["progression_advisory"]["role"] == "telemetry"


def test_merge_character_audit_metadata_signal_interpretation_with_grounding() -> None:
    merged = _merge_character_audit_metadata(
        base={},
        progression_advisory=None,
        anti_regression_advisory=None,
        scene_grounding_audit={
            "phase1": {
                "continuity_turn_index": 2,
                "fact_count": 0,
                "binding_fact_count": 0,
                "non_binding_fact_count": 0,
            }
        },
    )
    assert merged["signal_interpretation"]["signals"]["scene_grounding"]["role"] == (
        "telemetry"
    )
