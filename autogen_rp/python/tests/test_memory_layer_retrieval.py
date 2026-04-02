"""Memory Implementation Phase B: episodic retrieval and prompt section formatting."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from memory_layer.retrieval import (
    EpisodicPromptSnapshot,
    build_character_state_context_for_prompt,
    build_episodic_prompt_snapshot,
    format_episodic_prompt_sections,
)


def test_build_episodic_snapshot_empty() -> None:
    state = CharacterState(name="A")
    snap = build_episodic_prompt_snapshot(state=state)
    assert snap.interpretation_lines == ()
    assert snap.self_trace_lines == ()


def test_build_episodic_snapshot_tails_and_order() -> None:
    state = CharacterState(name="A")
    state.character_memory_summary = [f"i{i}" for i in range(8)]
    state.recent_observations = [f"o{i}" for i in range(8)]
    snap = build_episodic_prompt_snapshot(
        state=state, max_interpretation_lines=3, max_self_trace_lines=2
    )
    assert snap.interpretation_lines == ("i5", "i6", "i7")
    assert snap.self_trace_lines == ("o6", "o7")


def test_format_episodic_prompt_sections_matches_legacy_shape() -> None:
    text = format_episodic_prompt_sections(
        EpisodicPromptSnapshot(
            interpretation_lines=("line a",),
            self_trace_lines=("trace b",),
        )
    )
    assert "\nYour private interpretation summary:\n" in text
    assert "  • line a" in text
    assert "\nRecent memories:\n" in text
    assert "  • trace b" in text


def test_format_episodic_empty() -> None:
    assert (
        format_episodic_prompt_sections(
            EpisodicPromptSnapshot(interpretation_lines=(), self_trace_lines=())
        )
        == ""
    )


def test_build_character_state_context_for_prompt_composes_identity_and_episodic() -> None:
    state = CharacterState(name="Z", long_term_goal="goal z")
    state.remember_event("evt", "interp")
    state.recent_observations.append("self trace")
    full = build_character_state_context_for_prompt(state=state)
    assert "Long-term goal: goal z" in full
    assert "private interpretation summary" in full.lower()
    assert "interp" in full
    assert "Recent memories:" in full
    assert "self trace" in full
