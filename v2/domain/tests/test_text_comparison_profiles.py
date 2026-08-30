"""Tests for presentation-verbatim comparison profile (Issue #77)."""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.text_comparison_profiles import (  # noqa: E402
    canonicalize_for_presentation_verbatim,
)


def test_canonicalize_apostrophe_u2019_to_ascii() -> None:
    assert canonicalize_for_presentation_verbatim("I\u2019ve") == "I've"


def test_canonicalize_curly_double_quotes() -> None:
    assert canonicalize_for_presentation_verbatim("\u201chello\u201d") == '"hello"'


def test_canonicalize_nbsp_to_space() -> None:
    assert canonicalize_for_presentation_verbatim("a\u00a0b") == "a b"


def test_canonicalize_nfc_composition() -> None:
    decomposed = "caf\u00e9"
    composed = unicodedata.normalize("NFC", decomposed)
    assert canonicalize_for_presentation_verbatim(decomposed) == composed


def test_canonicalize_preserves_dash_distinctions() -> None:
    hyphen = "re-enter"
    en_dash = "re\u2013enter"
    em_dash = "re\u2014enter"
    assert canonicalize_for_presentation_verbatim(hyphen) == hyphen
    assert canonicalize_for_presentation_verbatim(en_dash) == en_dash
    assert canonicalize_for_presentation_verbatim(em_dash) == em_dash
    assert canonicalize_for_presentation_verbatim(hyphen) != canonicalize_for_presentation_verbatim(
        en_dash
    )


def test_canonicalize_preserves_ellipsis_distinctions() -> None:
    assert canonicalize_for_presentation_verbatim("wait...") != canonicalize_for_presentation_verbatim(
        "wait\u2026"
    )
