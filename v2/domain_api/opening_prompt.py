"""Presentation-only opening generation instructions for DSH bootstrap inference."""

from __future__ import annotations

from narrative_visibility_prompt import OPENING_VISIBILITY_OUTPUT_INSTRUCTION


def build_opening_generation_instruction(
    *,
    present_characters: list[str],
    premise: str,
) -> str:
    cast_label = ", ".join(present_characters) if present_characters else "the cast"
    premise_block = premise.strip() or "A roleplay scene is beginning."
    return (
        "Write a single narrator-style scene opening for the player.\n"
        "Rules:\n"
        "- Use only facts already established in the authoritative context below.\n"
        "- Do not invent new canonical world facts, locations, props, or events.\n"
        "- Do not resolve future player choices or speak for the player character.\n"
        "- Present tense, immersive prose, ending on a natural hook for the player's first reply.\n"
        f"\nScene premise (authoritative): {premise_block}\n"
        f"Present characters: {cast_label}\n"
        f"\n{OPENING_VISIBILITY_OUTPUT_INSTRUCTION}\n"
    )
