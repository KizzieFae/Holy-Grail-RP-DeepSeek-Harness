"""Tests for deterministic audibility / perception filtering (``perception_audibility``)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from perception_audibility import (
    build_recent_dialogue_history_for_viewer,
    event_knowledge_recipients,
    filter_structured_move_for_viewer,
    normalize_move_audibility,
    public_safe_event_summary,
    viewer_may_perceive_dialogue,
)


def test_normalize_defaults_to_public() -> None:
    m = normalize_move_audibility(
        {"action": "nods", "dialogue": "Hello everyone."},
        "A",
        ["A", "B"],
    )
    assert m["audibility"] == "public"
    assert m["audience"] == []


def test_directed_explicit_audience() -> None:
    m = normalize_move_audibility(
        {
            "action": "leans in",
            "dialogue": "Secret",
            "audibility": "directed",
            "audience": ["B"],
        },
        "A",
        ["A", "B", "C"],
    )
    assert m["audibility"] == "directed"
    assert m["audience"] == ["B"]


def test_whisper_heuristic_marks_directed() -> None:
    m = normalize_move_audibility(
        {
            "action": "whispers to Bob",
            "dialogue": "run",
        },
        "A",
        ["A", "Bob", "C"],
    )
    assert m["audibility"] == "directed"
    assert "Bob" in m["audience"]


def test_viewer_may_perceive_directed() -> None:
    m = normalize_move_audibility(
        {
            "action": "whispers to Marlene",
            "dialogue": "help",
            "audibility": "directed",
            "audience": ["Marlene"],
        },
        "Kizzie",
        ["Kizzie", "Marlene", "Willow"],
    )
    assert viewer_may_perceive_dialogue(m, acting_character="Kizzie", viewer_character="Kizzie")
    assert viewer_may_perceive_dialogue(
        m, acting_character="Kizzie", viewer_character="Marlene"
    )
    assert not viewer_may_perceive_dialogue(
        m, acting_character="Kizzie", viewer_character="Willow"
    )


def test_event_knowledge_recipients_restricted() -> None:
    m = normalize_move_audibility(
        {
            "action": "whispers to B",
            "dialogue": "x",
            "audibility": "directed",
            "audience": ["B"],
        },
        "A",
        ["A", "B", "C"],
    )
    r = event_knowledge_recipients(
        m, acting_character="A", present_characters=["A", "B", "C"]
    )
    assert set(r) == {"A", "B"}


def test_public_safe_event_summary_strips_dialogue() -> None:
    m = normalize_move_audibility(
        {
            "action": "whispers",
            "dialogue": "top secret phrase",
            "audibility": "directed",
            "audience": ["B"],
        },
        "A",
        ["A", "B"],
    )
    raw = 'A whispers; said: "top secret phrase"'
    safe = public_safe_event_summary(
        acting_character="A", move=m, provisional_summary=raw
    )
    assert "top secret phrase" not in safe.lower()


def test_filter_structured_move_redacts_for_non_audience() -> None:
    entry = {
        "speaker": "A",
        "action": "whispers to B",
        "dialogue": "secret",
        "audibility": "directed",
        "audience": ["B"],
    }
    out = filter_structured_move_for_viewer(
        entry,
        viewer_character_name="C",
        present_characters=["A", "B", "C"],
    )
    assert out["dialogue"] == ""


def test_build_recent_dialogue_orchestration_omits_private_rendered() -> None:
    def _display(name: str) -> str:
        return name

    hist = [
        {
            "role": "assistant",
            "speaker": "A",
            "actor": "A",
            "content": 'A leaned in. "classified words here"',
            "move": {
                "action": "leans in, whispering to B",
                "dialogue": "classified words here",
                "audibility": "directed",
                "audience": ["B"],
            },
        }
    ]
    out = build_recent_dialogue_history_for_viewer(
        chat_history=hist,
        viewer_character_name=None,
        character_names=["A", "B"],
        get_character_display_name_fn=_display,
        limit=8,
    )
    assert len(out) == 1
    assert "classified words here" not in out[0]["content"]
