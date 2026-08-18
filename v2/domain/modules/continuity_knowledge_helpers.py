import re
from datetime import datetime
from typing import Any

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)
from continuity_state import CharacterInterpretation
from perception_audibility import (
    normalize_move_audibility,
    observer_may_quote_dialogue_in_interpretation,
    speech_beat_viewer_may_perceive,
    viewer_may_perceive_dialogue,
)


def share_event_knowledge(
    *, manager: Any, event_id: str, character_name: str, knowledge_type: str
) -> None:
    event = next(
        (item for item in manager.public_events if item.event_id == event_id), None
    )
    if event is None:
        return

    if character_name not in event.known_by:
        event.known_by.append(character_name)

    if knowledge_type == "observed" and character_name not in event.observed_by:
        event.observed_by.append(character_name)
    elif knowledge_type == "told" and character_name not in event.told_to:
        event.told_to.append(character_name)
    elif knowledge_type == "inferred" and character_name not in event.inferred_by:
        event.inferred_by.append(character_name)


def perceivable_dialogue_excerpt_for_interpretation(
    *,
    norm_move: dict[str, Any],
    acting_character: str,
    observer_character: str,
    max_chars: int = 50,
) -> str:
    """Verbatim speech snippet for interpretation text — only speech beats the observer may perceive (Issue #140)."""
    if is_canonical_v2_move(norm_move):
        parts: list[str] = []
        beats = norm_move.get("beats")
        if not isinstance(beats, list):
            return ""
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            if not speech_beat_viewer_may_perceive(
                b,
                acting_character=acting_character,
                viewer_character=observer_character,
            ):
                continue
            seg = str(b.get("dialogue", "") or "").strip()
            if seg:
                parts.append(seg)
        return " ".join(parts).strip()[:max_chars]
    if not observer_may_quote_dialogue_in_interpretation(
        norm_move,
        acting_character=acting_character,
        observer_character=observer_character,
    ):
        return ""
    return str(norm_move.get("dialogue", "") or "").strip()[:max_chars]


def mentioned_participants(*, text: str, participants: list[str]) -> list[str]:
    text_lower = text.lower()
    mentioned: list[str] = []
    for participant in participants:
        if re.search(rf"\b{re.escape(participant.lower())}(?:'s)?\b", text_lower):
            mentioned.append(participant)
    return mentioned


def propagate_knowledge_from_turn(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    other_characters: list[str],
    knowledge_share_min_overlap: int,
    turn_tokens_fn,
    event_tokens_fn,
    mentioned_participants_fn,
    share_event_knowledge_fn,
) -> None:
    if is_canonical_v2_move(move):
        dialogue = legacy_flat_dialogue_text(move)
    else:
        dialogue = str(move.get("dialogue", "") or "")
    if not str(dialogue).strip():
        return
    present = list(dict.fromkeys([acting_character, *other_characters]))
    move = normalize_move_audibility(dict(move), acting_character, present)
    move_tokens = turn_tokens_fn(move)
    if not move_tokens:
        return
    direct_targets = mentioned_participants_fn(dialogue, other_characters)
    candidate_targets = direct_targets or other_characters
    for event in manager.public_events:
        if event.knowledge_level_for(acting_character) is None:
            continue
        overlap = move_tokens.intersection(event_tokens_fn(event))
        if len(overlap) < knowledge_share_min_overlap:
            continue
        for target in candidate_targets:
            if event.knowledge_level_for(target) is not None:
                continue
            if not viewer_may_perceive_dialogue(
                move, acting_character=acting_character, viewer_character=target
            ):
                continue
            knowledge_type = "told" if target in direct_targets else "inferred"
            share_event_knowledge_fn(event.event_id, target, knowledge_type)


def update_interpretations(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    other_characters: list[str],
    timestamp: datetime,
) -> None:
    motivation = move.get("motivation", {})
    present = list(dict.fromkeys([acting_character, *other_characters]))
    norm_move = normalize_move_audibility(dict(move), acting_character, present)
    if is_canonical_v2_move(norm_move):
        action = legacy_flat_action_text(norm_move)
        flat_dialogue = legacy_flat_dialogue_text(norm_move)
    else:
        action = str(move.get("action", "") or "")
        flat_dialogue = str(move.get("dialogue", "") or "")

    for observer in other_characters:
        if observer not in manager.interpretations:
            manager.interpretations[observer] = []

        observed = f"Saw {acting_character} {action}"
        heard_excerpt = perceivable_dialogue_excerpt_for_interpretation(
            norm_move=norm_move,
            acting_character=acting_character,
            observer_character=observer,
            max_chars=50,
        )
        if heard_excerpt:
            observed += f' and heard: "{heard_excerpt}"'
        elif flat_dialogue:
            observed += " (speech not audible to you; only observable behavior)"

        reaction = "observing neutrally"
        if "angry" in str(motivation).lower() or "accus" in flat_dialogue.lower():
            reaction = "defensive or concerned"
        elif "question" in str(motivation).lower() or "?" in flat_dialogue:
            reaction = "curious or guarded"

        interpretation = CharacterInterpretation(
            interpretation_id=f"int_{timestamp.isoformat()}_{observer}_{acting_character}",
            character_name=observer,
            subject_type="event",
            subject_id=f"{acting_character}_turn_{timestamp.isoformat()}",
            interpretation=observed,
            emotional_reaction=reaction,
            formed_at=timestamp,
            confidence="tentative",
        )
        manager.interpretations[observer].append(interpretation)
        manager.interpretations[observer] = manager.interpretations[observer][-20:]
