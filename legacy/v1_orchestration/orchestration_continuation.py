"""Continuation override actor resolution (Issue #164)."""

from typing import Any

_CONTINUATION_SUPERSEDING_TAGS = {
    "agreement",
    "arrival",
    "commitment",
    "exit",
    "refusal",
    "access_denied",
    "access_granted",
    "revelation",
}


def resolve_continuation_override_actor(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    eligible_participants: list[str] | None,
    actors_used_this_round: list[str],
    offstage_characters: list[str] | None = None,
) -> str | None:
    if eligible_participants is None:
        cm_state = getattr(continuity_manager, "scene_state", None)
        if cm_state is not None:
            eligible_participants = list(
                getattr(cm_state, "present_characters", []) or []
            )
        else:
            return None

    recent_moves = orchestration_state.get("recent_structured_moves", [])
    if not isinstance(recent_moves, list) or not recent_moves:
        return None

    last_move = recent_moves[-1]
    if not isinstance(last_move, dict):
        return None

    actor = str(last_move.get("speaker", "") or "").strip()
    if not actor:
        return None
    if actor not in eligible_participants:
        return None
    if actors_used_this_round.count(actor) != 1:
        return None

    spotlight_history = orchestration_state.get("spotlight_history", [])
    if isinstance(spotlight_history, list) and spotlight_history:
        if str(spotlight_history[-1] or "") != actor:
            return None

    motivation = (
        last_move.get("motivation", {})
        if isinstance(last_move.get("motivation", {}), dict)
        else {}
    )
    if not any(
        str(motivation.get(field, "") or "").strip()
        for field in ("goal", "tactic")
    ):
        return None

    turn_metadata: dict[str, Any] = {}
    if continuity_manager is not None:
        turn_index = int(getattr(continuity_manager, "turn_counter", 0) or 0)
        metadata_by_index = getattr(continuity_manager, "turn_metadata_by_index", {})
        if isinstance(metadata_by_index, dict):
            candidate_metadata = metadata_by_index.get(turn_index, {})
            if isinstance(candidate_metadata, dict):
                turn_metadata = candidate_metadata

    tags = {
        str(item)
        for item in turn_metadata.get("tags", [])
        if str(item or "").strip()
    }
    if tags.intersection(_CONTINUATION_SUPERSEDING_TAGS):
        return None

    off = {
        str(x).strip()
        for x in (offstage_characters or [])
        if str(x or "").strip()
    }
    unheard_other = [
        p
        for p in eligible_participants
        if str(p or "").strip()
        and str(p).strip() not in off
        and str(p).strip() != actor
        and actors_used_this_round.count(str(p).strip()) == 0
    ]
    if unheard_other:
        return None

    return actor
