"""Issue #240 experimental one-pass prompt topology (investigation-only).

Gate: ``RP_ISSUE240_PROMPT_TOPOLOGY=v1`` (also ``1``, ``true``, ``yes``, ``on``).
Default / unset: production ``prompt_builders.build_character_turn_prompt``.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable

from prompt_builders import build_character_turn_prompt as _production_build_character_turn_prompt

_ISSUE240_ENV = "RP_ISSUE240_PROMPT_TOPOLOGY"
_V1_TRUTHY = frozenset({"1", "v1", "true", "yes", "on"})

ISSUE240_V1_OPENING_MARKER = "Act primarily as this character"
ISSUE240_SEMANTIC_BLOCK_HEADER = "FOR THIS BEAT — SEMANTIC SELF-REPORT"
ISSUE240_DOCTRINE_PHRASE = "not compliance theater"

_COMPRESSED_PRIORITIES_5_7 = """5. SOCIAL REALISM
- Stay occupied with your own business unless directly addressed, affected, obligated, or strategically choosing to engage. Hierarchy and public tension often suppress speech.

6. KNOWLEDGE AND EVIDENCE DISCIPLINE
- Match reactions to evidence strength; do not upgrade rumor or inference into certainty.

7. CANON AND WORLD CONSISTENCY
- Do not contradict canon anchors or broaden scene ontology beyond established facts."""

_SLIM_OUTPUT_RULES = """OUTPUT RULES:
- Only output a single JSON object: canonical character move v2 (integer ``move_schema_version`` 2, non-empty ``beats[]``, ``motivation``, optional ``scene_state_updates``, optional ``semantic_proposals``).
- Do not emit root-level ``action``, ``dialogue``, ``audibility``, or ``audience``. Put visible action and speech only inside ``beats[]`` as ``type: action`` or ``type: speech`` objects, in true beat order.
- Root ``semantic_proposals`` (when present): self-only semantic commit intent — kinds ``off_focal`` | ``reentry`` | ``excursion_lifecycle``; ``operation`` required only for ``excursion_lifecycle``. Not a commit. Do not emit root ``presence_changes``, ``excursion_lifecycle``, or ``spatial_transition``.
- Each ``type: action`` beat has non-empty ``action`` (visible self-only, third person). Each ``type: speech`` beat has non-empty ``dialogue``. On speech beats, optional ``audibility`` is one of ``public``, ``directed``, ``private``; for ``directed`` or ``private``, include non-empty ``audience``.
- Keep action beats concrete and observable; let speech sound natural and in-character.
- Registry settlements (``scene_state_updates.*``): follow system OUTPUT FORMAT; emit only when this beat explicitly settles a bounded scene fact supported by the beat."""


def issue240_prompt_topology_mode() -> str | None:
    raw = os.environ.get(_ISSUE240_ENV, "").strip().lower()
    if raw in _V1_TRUTHY:
        return "v1"
    return None


def build_character_turn_prompt_issue240_v1_opening(char_name: str) -> str:
    return f"""You are {char_name}, taking your next turn in an ongoing roleplay scene.

Act primarily as this character: voice, pressure, subtext, and in-character judgment come first. While authoring your move, you are also responsible for accurately reporting certain continuity-relevant intent from what you actually write in this beat — when that intent exists.

Your JSON may include root semantic_proposals only as an honest report of covered intent in your authored beats (off_focal, reentry, excursion_lifecycle). semantic_proposals report authored continuity intent — {ISSUE240_DOCTRINE_PHRASE}. They declare what your move means for continuity to evaluate; emission is not proof of commit and must not be cosplayed.

If this beat has no covered intent, omit semantic_proposals entirely. Do not emit semantic_proposals: [] or proposal keys that your beats do not substantiate. Prose implication alone does not substitute for an explicit report."""


def build_character_turn_prompt_issue240_v1_semantic_block() -> str:
    return f"""{ISSUE240_SEMANTIC_BLOCK_HEADER} (same move you are authoring):

When authoring this beat, determine whether your move actually includes:
- off_focal intent (you step out of the immediate focal exchange / go offstage)
- reentry intent (you return to the focal exchange from off-focal)
- excursion lifecycle intent (open, update, or close an excursion — include operation when applicable)

If it does, report that intent honestly in root semantic_proposals aligned with your beats (self-only; kinds off_focal | reentry | excursion_lifecycle).

If it does not, omit semantic_proposals entirely.

Do not explain this analysis in dialogue or action beats."""


def apply_issue240_v1_topology_transform(
    production_prompt: str,
    *,
    char_name: str,
) -> str:
    """Apply #240 V1 framing to a production-shaped character turn prompt."""
    opening = build_character_turn_prompt_issue240_v1_opening(char_name)
    prompt = production_prompt.replace(
        "You are taking your next turn in an ongoing roleplay scene.",
        opening,
        1,
    )

    semantic_block = build_character_turn_prompt_issue240_v1_semantic_block()
    prompt = re.sub(
        r"(TRIGGER FOR THIS BEAT:\n.*?\n)\n(YOUR PRIVATE STATE:)",
        rf"\1\n{semantic_block}\n\n\2",
        prompt,
        count=1,
        flags=re.DOTALL,
    )

    prompt = re.sub(
        r"5\. SOCIAL REALISM\n.*?7\. CANON AND WORLD CONSISTENCY\n.*?\n\n",
        _COMPRESSED_PRIORITIES_5_7 + "\n\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )

    prompt = re.sub(
        r"OUTPUT RULES:.*\Z",
        _SLIM_OUTPUT_RULES + "\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    return prompt


def build_character_turn_prompt_issue240_v1(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_topology_transform(
        base,
        char_name=str(kwargs.get("char_name") or ""),
    )


def resolve_character_turn_prompt_builder() -> Callable[..., str]:
    if issue240_prompt_topology_mode() == "v1":
        return build_character_turn_prompt_issue240_v1
    return _production_build_character_turn_prompt


def build_character_turn_prompt_for_runtime(**kwargs: Any) -> str:
    """Runtime entry: production baseline unless ``RP_ISSUE240_PROMPT_TOPOLOGY=v1``."""
    return resolve_character_turn_prompt_builder()(**kwargs)
