"""Issue #242 Wave 0 — overlay semantic-engagement classifier detection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _issue240_audit_classifier import _overlay_demands_semantic_engagement


@pytest.mark.parametrize(
    "trigger,expected",
    [
        (
            "Traveler (overlay REINFORCED-1, Celina ONLY): REQUIRED semantic_evaluation "
            "when your beats show off_focal intent.",
            True,
        ),
        (
            "Traveler (overlay REINFORCED-1, Celina ONLY): REQUIRED root semantic_proposals "
            "when your beats show off_focal intent.",
            True,
        ),
        (
            "Traveler (overlay, Celina ONLY): If this beat materially shifts your focal participation, "
            "report via semantic_evaluation with decision covered_change.",
            False,
        ),
        ("Traveler: continue the scene.", False),
    ],
)
def test_overlay_demands_semantic_engagement(trigger: str, expected: bool) -> None:
    data = {"effective_user_trigger": trigger}
    assert _overlay_demands_semantic_engagement(data) is expected
