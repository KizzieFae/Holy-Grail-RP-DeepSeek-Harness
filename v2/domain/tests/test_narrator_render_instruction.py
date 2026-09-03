"""Focused branch coverage for Narrator render-instruction formatter (#103)."""

from __future__ import annotations

from domain.modules.narrator_render_instruction import build_narrator_render_prompt
from narrative_visibility_prompt import NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION


_V2_MOVE = {
    "move_schema_version": 2,
    "beats": [
        {"type": "action", "action": "She stepped forward."},
        {"type": "speech", "dialogue": "Hello there."},
    ],
    "motivation": "greet",
    "semantic_evaluation": {"decision": "no_covered_change"},
}


def test_v2_branch_includes_beats_verbatim_rules_and_visibility_instruction() -> None:
    prompt = build_narrator_render_prompt(
        char_name="Alice",
        action="",
        dialogue="",
        environment_event="",
        scene_context="Sitting room.",
        structured_move=_V2_MOVE,
    )
    lowered = prompt.lower()
    assert "structured character turn (v2 ``beats[]``)" in prompt
    assert "preserve ``beats[]`` order" in lowered
    assert "verbatim" in lowered
    assert NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION.strip() in prompt


def test_legacy_dialogue_branch_requires_exact_dialogue() -> None:
    prompt = build_narrator_render_prompt(
        char_name="Alice",
        action="She leaned in.",
        dialogue="Who is she?",
        environment_event="",
        scene_context="Bar scene.",
    )
    assert 'DIALOGUE TO INCLUDE: "Who is she?"' in prompt
    assert "include the exact dialogue" in prompt.lower()
    assert "presentation_text" not in prompt


def test_action_only_branch_and_environmental_blocks() -> None:
    prompt = build_narrator_render_prompt(
        char_name="Alice",
        action="She opened the door.",
        dialogue="",
        environment_event="Wind rattles the shutters.",
        scene_context="Entry hall.",
        environmental_baseline="Brass fixtures, dim light.",
        environmental_response_obligations="OBLIGATION: show worn floorboards.",
    )
    lowered = prompt.lower()
    assert "render the following character action into scene narration" in lowered
    assert "established environmental baseline" in lowered
    assert "Brass fixtures, dim light." in prompt
    assert "OBLIGATION: show worn floorboards." in prompt
    assert "immersive environment duty" in lowered
