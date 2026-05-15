"""GitHub #214 Tier A — scenario manifest contract (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_simulation_scenarios import (  # noqa: E402
    load_scenario,
    validate_optional_scenario_fields,
)


def test_audit_i191_is_tier_a_perception_smoke() -> None:
    raw = load_scenario("audit_i191_offstage_private_return")
    assert raw.get("audit_validation_tier") == "tier_a_perception_smoke"
    assert raw.get("audit_program_issue") == "214"
    assert raw.get("audit_bounded_token") == "SILVER-QUILL-414"
    assert raw.get("startup_trigger_mode") == "overlay"
    assert int(raw.get("max_turns") or 0) >= 10
    opening = str(raw.get("opening_description") or "")
    assert "directed" in opening and "private" in opening and "audience" in opening
    assert str(raw.get("opening_description") or "").strip() != str(
        raw.get("trigger_text") or ""
    ).strip()
    intent = str(raw.get("intent") or "")
    assert "#214" in intent and "#216" in intent
    assert "Tier A" in intent


def test_audit_validation_tier_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="audit_validation_tier"):
        validate_optional_scenario_fields(
            {"audit_validation_tier": "tier_c_unknown"},
            "fake",
        )
