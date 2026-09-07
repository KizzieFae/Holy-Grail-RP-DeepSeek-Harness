"""Narrator render-instruction text formatting (#103 / audit A3)."""

from __future__ import annotations

import json
from typing import Any

from character_move_adapters import is_canonical_v2_move
from narrative_visibility_prompt import NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION


def build_narrator_render_prompt(
    *,
    char_name: str,
    action: str,
    dialogue: str,
    environment_event: str,
    scene_context: str,
    structured_move: dict[str, Any] | None = None,
    environmental_baseline: str | None = None,
    environmental_response_obligations: str | None = None,
) -> str:
    env_baseline_block = ""
    if environmental_baseline:
        env_baseline_block = f"""
ESTABLISHED ENVIRONMENTAL BASELINE (authoritative — preserve; do not silently redesign):
{environmental_baseline}
"""
    obligation_block = ""
    if environmental_response_obligations:
        obligation_block = f"""
{environmental_response_obligations}
"""
    immersive_rules = """
IMMERSIVE ENVIRONMENT DUTY (#49 / #89):
- Make the physical environment perceptibly present through selective concrete detail (spatial relationships, lighting, sound, texture, temperature, smell, visible wear, motion, atmosphere).
- Respond physically to what the user/character actually did; use immediate_user_turn_context for current-turn player intent and triggering_user_context when authoritative occurrence evidence is present.
- Preserve established environmental facts from the baseline; do not reinvent continuity-bearing properties each turn.
- When environmental response obligations are present, communicate communicate_grounded obligations concretely; do not substitute inferred purpose for requested observable detail.
- Use ephemeral sensory texture for liveliness where appropriate; avoid sterile action-summary narration and generic irrelevant filler.
- Do not invent material facts when baseline or cognition marked bounded_refusal/failure; omit rather than guess.
- When environmental response obligations use sufficiency_undetermined or cognition_unavailable, do not treat baseline as verified sufficient; use only authoritative baseline and immediate/triggering user context.
- Vary focus and phrasing; avoid full re-description every turn unless materially expected.
"""
    if structured_move is not None and is_canonical_v2_move(structured_move):
        sm = json.dumps(structured_move, ensure_ascii=False, indent=2)
        return f"""Render the following structured character turn (v2 ``beats[]``) into third-person past-tense scene narration.

CHARACTER: {char_name}
STRUCTURED MOVE (authoritative; render only this visibility scope; do not invent speech):
{sm}
OPTIONAL ENVIRONMENT EVENT: {environment_event}
{env_baseline_block}{obligation_block}
SCENE CONTEXT:
{scene_context}
{immersive_rules}
RULES:
1. Preserve ``beats[]`` order: do not reorder beats.
2. For each ``type: speech`` beat, the ``dialogue`` string must appear in your output as a contiguous **verbatim** substring, in the same order as in ``beats`` (you may add connective narrator prose between beats; adjacent speech may be merged in prose only if every speech line still appears as an exact, ordered substring).
3. For ``type: action`` beats, you may paraphrase the action text in third person; do not treat action text as a verbatim substring requirement.
4. Do not add new spoken lines or quoted speech that are not substrings of the provided speech lines (narrator connective prose without quotes is allowed between beats).
5. If you include optional environment event material, work it in naturally; do not contradict authoritative scene progression, environmental baseline, or the structured move — omit environment material when it conflicts.
6. Only describe this character for action/speech; no other character dialogue.
7. Be concise but not sterile — roughly 2-8 sentences when environmental response is materially relevant.
8. Write in third person past tense.

{NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION}"""

    if dialogue:
        return f"""Render the following character action and dialogue into scene narration.

CHARACTER: {char_name}
ACTION: {action}
DIALOGUE TO INCLUDE: "{dialogue}"
OPTIONAL ENVIRONMENT EVENT: {environment_event}
{env_baseline_block}{obligation_block}
SCENE CONTEXT:
{scene_context}
{immersive_rules}
RULES:
1. Write in third person past tense.
2. Include the EXACT dialogue in double quotes as provided above.
3. NEVER paraphrase or alter the quoted dialogue.
4. Attribute the dialogue naturally.
5. Describe the action leading up to the dialogue.
6. You may include the optional environment event if it helps pacing; do not contradict authoritative scene progression, environmental baseline, or the committed action and dialogue — omit environment material when it conflicts.
7. Only describe what this character does - no other characters.
8. Preserve the established meaning of ambiguous or figurative language already present in the scene context and provided dialogue; do not literalize rumor, metaphor, hearsay, or uncertainty unless the supplied action or dialogue explicitly does so.
9. Be evocative and physically grounded (2-6 sentences when environment matters).
10. Prioritize body language, spatial positioning, immediate consequence, and selective sensory detail over generic atmosphere.

EXAMPLE OUTPUT FORMAT:
She tapped her fingers on the bar, eyes narrowing. "Who is she?" she asked, her voice low.

OUTPUT ONLY the rendered narration including the quoted dialogue."""

    return f"""Render the following character action into scene narration.

CHARACTER: {char_name}
ACTION: {action}
OPTIONAL ENVIRONMENT EVENT: {environment_event}
{env_baseline_block}{obligation_block}
SCENE CONTEXT:
{scene_context}
{immersive_rules}
RULES:
1. Write in third person past tense.
2. Attribute actions to the character naturally.
3. You may include the optional environment event if it helps pacing; do not contradict authoritative scene progression, environmental baseline, or the committed action — omit environment material when it conflicts.
4. Only describe what this character does.
5. Preserve the established meaning of ambiguous or figurative language already present in the scene context; do not literalize rumor, metaphor, hearsay, or uncertainty unless the supplied action explicitly does so.
6. Be evocative and physically grounded (2-6 sentences when environment matters).
7. Prioritize visible action, body language, immediate consequence, and selective sensory detail.

OUTPUT ONLY the rendered narration."""
