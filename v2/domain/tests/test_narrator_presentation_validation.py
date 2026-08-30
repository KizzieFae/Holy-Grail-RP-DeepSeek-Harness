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


def _single_speech_move(dialogue: str) -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "speech", "dialogue": dialogue}],
        "motivation": {
            "goal": "greet",
            "tactic": "speak",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }


def test_validate_narrator_presentation_accepts_typographic_apostrophe_in_move() -> None:
    """#73 regression: committed U+2019, narrator ASCII apostrophe."""
    dialogue = "I\u2019ve been expecting you."
    prose = 'Ayame said, "I\'ve been expecting you."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is True
    assert result.validation_class == "accepted"


def test_validate_narrator_presentation_accepts_curly_quotes_in_move() -> None:
    dialogue = "\u201cPlease come in.\u201d"
    prose = 'She said, "Please come in."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is True


def test_validate_narrator_presentation_accepts_nfc_equivalent_dialogue() -> None:
    import unicodedata

    dialogue = unicodedata.normalize("NFD", "caf\u00e9")
    prose = f'Aroma of {unicodedata.normalize("NFC", "caf\u00e9")} filled the room.'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is True


def test_validate_narrator_presentation_accepts_nbsp_in_prose() -> None:
    dialogue = "step inside"
    prose = "She gestured. \u201cstep\u00a0inside\u201d"
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is True


def test_validate_narrator_presentation_rejects_changed_word() -> None:
    dialogue = "I've been expecting you."
    prose = 'Ayame said, "I\'ve been waiting for you."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_missing_word() -> None:
    dialogue = "I've been expecting you."
    prose = 'Ayame said, "I\'ve been you."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_added_word_in_dialogue() -> None:
    dialogue = "Please come in."
    prose = 'She said, "Please quietly come in."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_changed_proper_name() -> None:
    dialogue = "Welcome, Kizzie."
    prose = 'Ayame said, "Welcome, Ayame."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_hyphen_vs_en_dash() -> None:
    dialogue = "re-enter now"
    prose = "She said, \u201cre\u2013enter now\u201d"
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_ellipsis_form_change() -> None:
    dialogue = "wait..."
    prose = "She said, \u201cwait\u2026\u201d"
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"


def test_validate_narrator_presentation_rejects_question_mark_change() -> None:
    dialogue = "Are you ready?"
    prose = 'She asked, "Are you ready."'
    result = validate_narrator_presentation(
        structured_move=_single_speech_move(dialogue),
        presentation_text=prose,
    )
    assert result.accepted is False
    assert result.validation_class == "speech_verbatim"
