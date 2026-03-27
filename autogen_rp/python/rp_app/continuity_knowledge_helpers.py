import re
from datetime import datetime
from typing import Any

from continuity_state import CharacterInterpretation


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
    dialogue = str(move.get("dialogue", "") or "")
    if not dialogue:
        return
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
    dialogue = move.get("dialogue", "")
    action = move.get("action", "")
    motivation = move.get("motivation", {})

    for observer in other_characters:
        if observer not in manager.interpretations:
            manager.interpretations[observer] = []

        observed = f"Saw {acting_character} {action}"
        if dialogue:
            observed += f' and say: "{dialogue[:50]}"'

        reaction = "observing neutrally"
        if "angry" in str(motivation).lower() or "accus" in dialogue.lower():
            reaction = "defensive or concerned"
        elif "question" in str(motivation).lower() or "?" in dialogue:
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
