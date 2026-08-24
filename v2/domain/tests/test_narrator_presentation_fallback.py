"""Tests for deterministic Narrator degraded presentation (#29)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.narrator_presentation_fallback import (  # noqa: E402
    render_degraded_player_presentation,
)


def test_degraded_fallback_preserves_action_and_speech() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "leans closer"},
            {"type": "speech", "dialogue": "We should go now."},
        ],
        "motivation": {
            "goal": "leave",
            "tactic": "speech",
            "emotional_driver": "urgent",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    text = render_degraded_player_presentation(move, character_name="Alice")
    assert "leans closer" in text
    assert "We should go now." in text
    assert text.startswith("Alice")


def test_degraded_fallback_action_only() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "nods thoughtfully"}],
        "motivation": {
            "goal": "acknowledge",
            "tactic": "gesture",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    text = render_degraded_player_presentation(move, character_name="Alice")
    assert "nods thoughtfully" in text
    assert text.endswith(".")
    assert "said" not in text


def test_degraded_fallback_player_path_includes_all_committed_speech_beats() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "nods"},
            {"type": "speech", "dialogue": "for everyone"},
            {
                "type": "speech",
                "dialogue": "for Bob only",
                "audibility": "directed",
                "audience": ["Bob"],
            },
        ],
        "motivation": {
            "goal": "share",
            "tactic": "speech",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    text = render_degraded_player_presentation(move, character_name="Alice")
    assert "for everyone" in text
    assert "for Bob only" in text
    assert "nods" in text
