from typing import Any

from response_validation_presence import detect_forced_speaker


def validate_turn_selection_decision(
    decision: dict[str, Any],
    participant_names: list[str],
    available_actors: list[str],
    trigger_text: str,
    spotlight_history: list[str],
) -> list[str]:
    issues: list[str] = []
    next_actor = str(decision.get("next_actor", "") or "")
    if next_actor not in participant_names:
        issues.append(f"Selected actor is not a participant: {next_actor}")
        return issues
    if next_actor not in available_actors:
        issues.append(f"Selected actor is not in available_next_actors: {next_actor}")

    return issues


def get_available_actors(
    participant_names: list[str],
    used_actors: list[str] | None = None,
    eligible_participants: list[str] | None = None,
) -> list[str]:
    used = set(used_actors or [])
    available = [name for name in participant_names if name not in used]
    if eligible_participants is None:
        return available
    eligible = set(eligible_participants)
    return [name for name in available if name in eligible]
