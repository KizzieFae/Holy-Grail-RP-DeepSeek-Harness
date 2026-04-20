"""Character response checks and ``validate_bot_response`` orchestration.

Conceptual validation tiers (taxonomy):

1. **Structural** — bot must not voice the user or leave unresolved user placeholders.
2. **Scene-truth** — contradictions with scene/template obligations (e.g. ``must_remain``).
3. **Identity / drift** — POV and goal-anchor consistency.
4. **Quality / repetition** — duplicate content and dialogue vs recent assistant turns.

**Pipeline order** (first failure wins; unchanged from historical behavior) runs:
structural → quality/repetition → identity/drift → scene-truth.
That order differs from the numeric tier list above; keep both in mind when extending validation.
"""

import re
from typing import Any

from character_state import CharacterState
from response_validation_drift import detect_character_drift
from response_validation_presence import detect_scene_presence_violation
from response_validation_binding_sleeping_surface import (
    validate_binding_sleeping_surface_contradiction,
)
from progression_simulation_scenarios import load_scenario
from response_validation_investigation_recall import (
    validate_investigation_recall_contract,
)
from continuity_mutation_pipeline import (
    validate_excursion_lifecycle_move_shape,
    validate_spatial_transition_move_shape,
)
from continuity_reintegration import validate_reintegration_move_shape
from response_validation_registry_slots import validate_registry_scene_state_updates

# Fuzzy duplicate detection (prefix / substring only; exact matches always reject).
DUPLICATE_LENGTH_RATIO_MIN = 0.8
DUPLICATE_SUBSTRING_MIN_SHORT_LEN = 40
DUPLICATE_SUBSTRING_MIN_FRACTION = 0.65
DUPLICATE_PREFIX_REMAINDER_MIN_LEN = 25


def _length_ratio(a: str, b: str) -> float:
    la, lb = len(a), len(b)
    mx = max(la, lb)
    if mx == 0:
        return 1.0
    return min(la, lb) / mx


def _fuzzy_prefix_duplicate_long_text(
    s1: str, s2: str, *, prefix_len: int
) -> bool:
    if len(s1) <= prefix_len or len(s2) <= prefix_len:
        return False
    if s1[:prefix_len] != s2[:prefix_len]:
        return False
    if _length_ratio(s1, s2) < DUPLICATE_LENGTH_RATIO_MIN:
        return False
    r1, r2 = s1[prefix_len:], s2[prefix_len:]
    if min(len(r1), len(r2)) < DUPLICATE_PREFIX_REMAINDER_MIN_LEN:
        return False
    return True


def _fuzzy_substring_duplicate(s1: str, s2: str) -> bool:
    if s1 == s2:
        return False
    short, long_s = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
    if len(short) < DUPLICATE_SUBSTRING_MIN_SHORT_LEN:
        return False
    if not long_s:
        return False
    if short not in long_s:
        return False
    if len(short) / len(long_s) < DUPLICATE_SUBSTRING_MIN_FRACTION:
        return False
    return True


def contains_user_speech(content: str, user_name: str) -> tuple[bool, str]:
    content_lower = content.lower()
    user_name_lower = user_name.lower()

    problematic_patterns = [
        rf"^\s*{re.escape(user_name_lower)}\s*[:\-\s]\s*['\"]",
        rf"^\s*['\"]\s*{re.escape(user_name_lower)}\s*[:\-\s]",
        rf"\b{re.escape(user_name_lower)}\s+(?:says?|said|replies?|responded|asks?|asked|exclaims?|exclaimed|mutters?|muttered)",
        rf"\b{re.escape(user_name_lower)}\s+(?:nods?|shrugs?|sighs?|laughs?|smiles?|frowns?|looks?|turns?|walks?|steps?)",
        # Only flag "you say/said" at start or after sentence boundary (user control), not mid-dialogue
        r"(?:^|[.!?]\s+|\n)\s*you\s+(?:says?|said|replies?|responded|asks?|asked)\s*(?:[:\-]|['\"])",
    ]

    for pattern in problematic_patterns:
        match = re.search(pattern, content_lower)
        if match:
            return True, f"Detected user control: '{match.group(0)}'"

    if "{{user}}" in content_lower or "{{user_name}}" in content_lower:
        return True, "Unresolved user placeholder"

    return False, ""


def _normalize_speaker_name(value: str) -> str:
    normalized = re.sub(r"[_\s]+", " ", str(value or "")).strip().lower()
    return normalized


def _normalize_dialogue_text(value: str) -> str:
    normalized = str(value or "")
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip().lower())
    return normalized


def is_duplicate_dialogue(
    *,
    speaker: str,
    dialogue: str,
    chat_history: list[dict],
    window_size: int = 8,
) -> tuple[bool, str]:
    normalized_dialogue = _normalize_dialogue_text(dialogue)
    if len(normalized_dialogue) < 20:
        return False, ""

    speaker_normalized = _normalize_speaker_name(speaker)
    recent_messages = [
        msg for msg in chat_history[-window_size:] if msg.get("role") == "assistant"
    ]

    for msg in recent_messages:
        msg_speaker = _normalize_speaker_name(str(msg.get("speaker", "") or ""))
        if msg_speaker and msg_speaker != speaker_normalized:
            continue

        move = msg.get("move", {})
        if not isinstance(move, dict):
            continue

        prev_dialogue = _normalize_dialogue_text(str(move.get("dialogue", "") or ""))
        if not prev_dialogue:
            continue

        if normalized_dialogue == prev_dialogue:
            return True, "Exact duplicate dialogue detected"

        if len(normalized_dialogue) > 60 and len(prev_dialogue) > 60:
            if _fuzzy_prefix_duplicate_long_text(
                normalized_dialogue, prev_dialogue, prefix_len=60
            ):
                return True, "Substantial dialogue overlap detected"

            if _fuzzy_substring_duplicate(normalized_dialogue, prev_dialogue):
                return True, "Repeated dialogue structure detected"

    return False, ""


def is_duplicate_content(
    content: str, chat_history: list[dict], window_size: int = 5
) -> tuple[bool, str]:
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    if len(normalized) < 10:
        return False, ""

    recent_messages = [
        msg for msg in chat_history[-window_size:] if msg.get("role") == "assistant"
    ]

    for msg in recent_messages:
        prev_content = re.sub(r"\s+", " ", msg.get("content", "").strip().lower())

        if normalized == prev_content:
            return True, "Exact duplicate of previous message"

        if len(normalized) > 50 and len(prev_content) > 50:
            if _fuzzy_prefix_duplicate_long_text(
                normalized, prev_content, prefix_len=50
            ):
                return True, "Substantial content overlap detected"

            if _fuzzy_substring_duplicate(normalized, prev_content):
                return True, "Repeated content structure"

    return False, ""


def _validate_bot_tier_structural(
    content: str, user_name: str
) -> tuple[bool, str]:
    """Tier 1 — structural invalidity."""
    has_user_speech, user_reason = contains_user_speech(content, user_name)
    if has_user_speech:
        return False, f"[USER_SPEECH] {user_reason}"
    return True, ""


def _validate_bot_tier_quality_repetition(
    content: str,
    speaker: str,
    chat_history: list[dict],
    move: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Tier 4 — quality / repetition (runs before identity and scene-truth in the pipeline)."""
    is_dup, dup_reason = is_duplicate_content(content, chat_history)
    if is_dup:
        return False, f"[DUPLICATE] {dup_reason}"

    dialogue = str((move or {}).get("dialogue", "") or "")
    is_dup_dialogue, dup_dialogue_reason = is_duplicate_dialogue(
        speaker=speaker,
        dialogue=dialogue,
        chat_history=chat_history,
    )
    if is_dup_dialogue:
        return False, f"[DUPLICATE] {dup_dialogue_reason}"

    return True, ""


def _validate_bot_tier_identity_drift(
    content: str,
    speaker: str,
    state: CharacterState | None,
    move: dict[str, Any] | None,
    canon_anchors: list[Any] | None,
    scene_state: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Tier 3 — identity / drift."""
    has_drift, drift_reason = detect_character_drift(
        content,
        speaker,
        state,
        move,
        canon_anchors,
        scene_state=scene_state,
    )
    if has_drift:
        return False, f"[CHARACTER_DRIFT] {drift_reason}"
    return True, ""


def _validate_bot_tier_scene_truth(
    content: str,
    speaker: str,
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
    chat_history: list[dict],
) -> tuple[bool, str]:
    """Tier 2 — scene-truth / template obligations (runs last in the pipeline)."""
    has_presence_violation, presence_reason = detect_scene_presence_violation(
        content,
        speaker,
        move,
        scene_state,
        chat_history=chat_history,
    )
    if has_presence_violation:
        if presence_reason.startswith("[PERCEPTION]"):
            return False, presence_reason
        return False, f"[SCENE_PRESENCE] {presence_reason}"
    return True, ""


def validate_bot_response(
    content: str,
    speaker: str,
    user_name: str,
    chat_history: list[dict],
    state: CharacterState | None = None,
    move: dict[str, Any] | None = None,
    canon_anchors: list[Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    continuity_manager: Any | None = None,
    scene_grounding: dict[str, Any] | None = None,
    effective_user_trigger: str = "",
    character_system_prompt: str | None = None,
    simulation_scenario_id: str | None = None,
    orchestration_turn_number: int | None = None,
) -> tuple[bool, str]:
    ok, msg = _validate_bot_tier_structural(content, user_name)
    if not ok:
        return False, msg

    ok, msg = validate_registry_scene_state_updates(
        move,
        scene_state=scene_state,
        _continuity_manager=continuity_manager,
    )
    if not ok:
        return False, msg

    ok, msg = validate_spatial_transition_move_shape(move)
    if not ok:
        return False, msg

    ok, msg = validate_excursion_lifecycle_move_shape(move)
    if not ok:
        return False, msg

    ok, msg = validate_reintegration_move_shape(move)
    if not ok:
        return False, msg

    ok, msg = _validate_bot_tier_quality_repetition(
        content, speaker, chat_history, move
    )
    if not ok:
        return False, msg

    ok, msg = _validate_bot_tier_identity_drift(
        content, speaker, state, move, canon_anchors, scene_state
    )
    if not ok:
        return False, msg

    ok, msg = _validate_bot_tier_scene_truth(
        content, speaker, move, scene_state, chat_history
    )
    if not ok:
        return False, msg

    ok, msg = validate_binding_sleeping_surface_contradiction(
        move=move,
        speaker=speaker,
        scene_grounding=scene_grounding,
        scene_state=scene_state,
        continuity_manager=continuity_manager,
    )
    if not ok:
        return False, msg

    if (
        simulation_scenario_id
        and orchestration_turn_number is not None
        and move is not None
    ):
        try:
            scenario_raw = load_scenario(str(simulation_scenario_id).strip())
        except (OSError, ValueError, KeyError, TypeError):
            scenario_raw = None
        if isinstance(scenario_raw, dict):
            ok, msg = validate_investigation_recall_contract(
                move=move,
                orchestration_turn_number=int(orchestration_turn_number),
                scenario_raw=scenario_raw,
                effective_user_trigger=effective_user_trigger,
                character_system_prompt=character_system_prompt,
            )
            if not ok:
                return False, msg

    return True, ""
