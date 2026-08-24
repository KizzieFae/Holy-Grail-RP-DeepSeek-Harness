"""Deterministic Narrator presentation validation tests (Issue #24)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.narrator_presentation_validation import (  # noqa: E402
    validate_narrator_presentation,
)


def _speech_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "nods"},
            {"type": "speech", "dialogue": "for everyone"},
            {"type": "speech", "dialogue": "for Bob only"},
        ],
        "motivation": {
            "goal": "share",
            "tactic": "mixed speech",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }


def test_validate_narrator_presentation_accepts_verbatim_ordered_speech() -> None:
    prose = 'Alice nods. "for everyone" she said, then added "for Bob only".'
    result = validate_narrator_presentation(
        structured_move=_speech_move(),
        presentation_text=prose,
    )
    assert result.accepted is True
    assert result.validation_class == "accepted"


def test_validate_narrator_presentation_rejects_missing_speech() -> None:
    result = validate_narrator_presentation(
        structured_move=_speech_move(),
        presentation_text='Alice nods quietly.',
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"
    assert result.retryable is True


def test_validate_narrator_presentation_rejects_out_of_order_speech() -> None:
    prose = 'She said "for Bob only" and then "for everyone".'
    result = validate_narrator_presentation(
        structured_move=_speech_move(),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_order"


def test_validate_narrator_presentation_action_only_move_passes() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "nods thoughtfully"}],
        "motivation": {
            "goal": "ack",
            "tactic": "gesture",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    result = validate_narrator_presentation(
        structured_move=move,
        presentation_text="Alice nodded thoughtfully.",
    )
    assert result.accepted is True
