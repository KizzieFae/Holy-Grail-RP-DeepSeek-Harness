"""Issue #139 — v2 narrator rendering, ordered substring checks, and fallbacks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_rendering import (
    fallback_render_move,
    rendered_includes_ordered_speech_substrings,
    speech_dialogue_substrings_in_order,
)
from perception_audibility import (
    filter_structured_move_for_viewer,
    normalize_move_audibility,
)


def _v2_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "She straightened her jacket."},
            {"type": "speech", "dialogue": "First line."},
            {"type": "speech", "dialogue": "Second line."},
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "r",
        },
    }


def test_speech_dialogue_substrings_in_order_v2() -> None:
    m = _v2_move()
    assert speech_dialogue_substrings_in_order(m) == ["First line.", "Second line."]


def test_rendered_includes_ordered_speech_substrings_ok() -> None:
    s = ["First", "Second"]
    text = 'Intro "First" then "Second" tail.'
    assert rendered_includes_ordered_speech_substrings(text, s) is True


def test_rendered_includes_ordered_speech_substrings_order_fail() -> None:
    s = ["Second", "First"]
    text = 'Intro "First" then "Second" tail.'
    assert rendered_includes_ordered_speech_substrings(text, s) is False


def test_fallback_render_v2_composes_from_beats_only() -> None:
    m = _v2_move()
    d = _dec()
    out = fallback_render_move("Celina", m, d)
    assert "First line." in out
    assert "Second line." in out
    # v2: no flat join pretended as a single line from root; root dialogue absent
    assert out.count('"') >= 2


def test_v1_fallback_regressions_use_root_fields() -> None:
    m = {
        "action": "looked up",
        "dialogue": "Old style.",
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "r",
        },
    }
    d = _dec()
    out = fallback_render_move("Ava", m, d)
    assert 'Old style.' in out


def test_projected_narrate_move_stubs_speech() -> None:
    from perception_audibility import REDACTED_SPEECH_STUB

    present = ["alice", "bob"]
    raw = {
        "move_schema_version": 2,
        "speaker": "alice",
        "beats": [
            {"type": "speech", "dialogue": "Secret", "audibility": "private", "audience": []},
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "r",
        },
    }
    norm = normalize_move_audibility(dict(raw), "alice", present)
    proj = filter_structured_move_for_viewer(
        {**norm, "speaker": "alice"},
        viewer_character_name="bob",
        present_characters=present,
    )
    subs = speech_dialogue_substrings_in_order(proj)
    assert subs
    assert subs[0] == REDACTED_SPEECH_STUB
    ex = f'Narration text with {repr(subs[0])} in the middle and end.'
    assert rendered_includes_ordered_speech_substrings(ex, subs) is True


def _dec() -> dict:
    return {"environment_event": "Thunder rolled.", "tension_shift": "none"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
