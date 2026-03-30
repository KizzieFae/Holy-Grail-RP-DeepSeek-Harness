from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from turn_runner_audit import _merge_character_audit_metadata


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
