"""Tests for deterministic audibility / perception filtering (``perception_audibility``)."""

import sys
from pathlib import Path

import pytest


from perception_audibility import (
    REDACTED_PLAYER_TEXT_CONTENT,
    REDACTED_SPEECH_STUB,
    build_recent_dialogue_history_for_viewer,
    event_knowledge_recipients,
    filter_structured_move_for_viewer,
    normalize_move_audibility,
    normalize_speech_beat_audibility,
    player_text_for_character_viewer,
    public_safe_event_summary,
    redact_structured_move_for_orchestration,
    speech_beat_viewer_may_perceive,
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


def test_player_text_public_all_viewers_see_full() -> None:
    raw = "Hello everyone, the door is open."
    present = ["Ayame", "Celina", "Hannah Lovelace"]
    for viewer in present:
        out = player_text_for_character_viewer(
            raw_text=raw,
            viewer_character_name=viewer,
            present_characters=present,
            user_display_name="Traveler",
            get_character_display_name_fn=lambda n: n,
        )
        assert out == raw


def test_player_text_whisper_directed_only_addressee_sees_secret() -> None:
    secret = "ZEPHYR-OMEGA-NINE"
    raw = (
        f"Ayame leans in and whispers only to Celina, voice low: "
        f"'Codeword for tonight is {secret}—tell no one else.'"
    )
    present = ["Ayame", "Celina", "Hannah Lovelace"]
    celina = player_text_for_character_viewer(
        raw_text=raw,
        viewer_character_name="Celina",
        present_characters=present,
        user_display_name="Traveler",
        get_character_display_name_fn=lambda n: n,
    )
    assert secret in celina
    hannah = player_text_for_character_viewer(
        raw_text=raw,
        viewer_character_name="Hannah Lovelace",
        present_characters=present,
        user_display_name="Traveler",
        get_character_display_name_fn=lambda n: n,
    )
    assert secret not in hannah
    assert REDACTED_PLAYER_TEXT_CONTENT in hannah


def test_player_text_ambiguous_defaults_to_public() -> None:
    raw = "Someone should check the hallway."
    present = ["A", "B", "C"]
    for viewer in present:
        out = player_text_for_character_viewer(
            raw_text=raw,
            viewer_character_name=viewer,
            present_characters=present,
            user_display_name="Traveler",
            get_character_display_name_fn=lambda n: n,
        )
        assert out == raw


def test_build_recent_dialogue_user_line_filtered_for_character_viewer() -> None:
    def _display(name: str) -> str:
        return name

    secret = "NEVER_LEAK_THIS_USER_SECRET"
    hist = [
        {
            "role": "user",
            "speaker": "Traveler",
            "content": f"Whisper to Bob only: {secret}",
        }
    ]
    bob_out = build_recent_dialogue_history_for_viewer(
        chat_history=hist,
        viewer_character_name="Bob",
        character_names=["Alice", "Bob", "Carol"],
        get_character_display_name_fn=_display,
        limit=8,
    )
    carol_out = build_recent_dialogue_history_for_viewer(
        chat_history=hist,
        viewer_character_name="Carol",
        character_names=["Alice", "Bob", "Carol"],
        get_character_display_name_fn=_display,
        limit=8,
    )
    none_out = build_recent_dialogue_history_for_viewer(
        chat_history=hist,
        viewer_character_name=None,
        character_names=["Alice", "Bob", "Carol"],
        get_character_display_name_fn=_display,
        limit=8,
    )
    assert secret in bob_out[0]["content"]
    assert secret not in carol_out[0]["content"]
    assert REDACTED_PLAYER_TEXT_CONTENT in carol_out[0]["content"]
    assert secret in none_out[0]["content"]


def test_build_recent_dialogue_director_sees_full_rendered() -> None:
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
    assert "classified words here" in out[0]["content"]


@pytest.mark.parametrize(
    "aud,audience,viewer,expected",
    [
        ("public", [], "B", True),
        ("public", [], "C", True),
        ("", [], "C", True),
        ("directed", ["B"], "A", True),
        ("directed", ["B"], "B", True),
        ("directed", ["B"], "C", False),
        ("private", ["B"], "A", True),
        ("private", ["B"], "B", True),
        ("private", ["B"], "C", False),
    ],
)
def test_speech_beat_viewer_may_perceive_matrix(
    aud: str, audience: list[str], viewer: str, expected: bool
) -> None:
    beat = {
        "type": "speech",
        "dialogue": "secret",
        "audibility": aud,
        "audience": audience,
    }
    b = normalize_speech_beat_audibility(beat, "A", ["A", "B", "C"])
    assert (
        speech_beat_viewer_may_perceive(
            b, acting_character="A", viewer_character=viewer
        )
        is expected
    )


def _v2_move_mixed() -> dict:
    return {
        "move_schema_version": 2,
        "motivation": {"goal": "g", "tactic": "t", "emotional_driver": "e", "risk_level": "r"},
        "beats": [
            {"type": "action", "action": "nods"},
            {"type": "speech", "dialogue": "for everyone"},
            {"type": "action", "action": "leans toward B"},
            {
                "type": "speech",
                "dialogue": "for B only",
                "audibility": "directed",
                "audience": ["B"],
            },
        ],
    }


def test_filter_structured_move_v2_redacts_per_beat_order_stable() -> None:
    entry = {"speaker": "A", **_v2_move_mixed()}
    out_c = filter_structured_move_for_viewer(
        entry,
        viewer_character_name="C",
        present_characters=["A", "B", "C"],
    )
    assert out_c["move_schema_version"] == 2
    assert len(out_c["beats"]) == 4
    assert out_c["beats"][0]["action"] == "nods"
    assert out_c["beats"][1]["dialogue"] == "for everyone"
    assert out_c["beats"][3]["dialogue"] == REDACTED_SPEECH_STUB
    assert "for B only" not in out_c["dialogue"]


def test_redact_structured_move_for_orchestration_passes_through() -> None:
    entry = {
        "speaker": "A",
        **_v2_move_mixed(),
    }
    out = redact_structured_move_for_orchestration(
        entry, present_characters=["A", "B", "C"]
    )
    assert out["beats"][3]["dialogue"] == "for B only"


def test_normalize_v2_omitted_audibility_is_public_on_speech() -> None:
    m = normalize_move_audibility(
        {
            "move_schema_version": 2,
            "motivation": {"goal": "g", "tactic": "t", "emotional_driver": "e", "risk_level": "r"},
            "beats": [{"type": "speech", "dialogue": "hi"}],
        },
        "A",
        ["A", "B"],
    )
    assert m["beats"][0]["audibility"] == "public"
    assert m["beats"][0]["audience"] == []


def test_viewer_may_perceive_v2_any_beat() -> None:
    m = normalize_move_audibility(_v2_move_mixed(), "A", ["A", "B", "C"])
    assert viewer_may_perceive_dialogue(m, acting_character="A", viewer_character="B")
    assert viewer_may_perceive_dialogue(m, acting_character="A", viewer_character="C")


def test_event_knowledge_recipients_v2_unions_beats() -> None:
    m = normalize_move_audibility(_v2_move_mixed(), "A", ["A", "B", "C"])
    r = event_knowledge_recipients(m, acting_character="A", present_characters=["A", "B", "C"])
    assert set(r) == {"A", "B", "C"}


def test_public_safe_event_summary_v2_strips_directed() -> None:
    move = {
        "move_schema_version": 2,
        "motivation": {"goal": "g", "tactic": "t", "emotional_driver": "e", "risk_level": "r"},
        "beats": [
            {
                "type": "speech",
                "dialogue": "ZZ_DIRECTED_SECRET_ZZ",
                "audibility": "directed",
                "audience": ["B"],
            },
        ],
    }
    m = normalize_move_audibility(move, "A", ["A", "B", "C"])
    raw = 'A whispered ZZ_DIRECTED_SECRET_ZZ to B'
    safe = public_safe_event_summary(
        acting_character="A", move=m, provisional_summary=raw
    )
    assert "ZZ_DIRECTED_SECRET_ZZ" not in safe
