from typing import Any, Callable, Literal

from beat_shift_state import default_pending_beat_shift, ensure_beat_shift_fields
from summary_audit_helpers import build_summary_block_audit_metadata

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


def build_default_orchestration_state() -> dict[str, Any]:
    return {
        "scene_state": {
            "opening_description": "",
            "present_characters": [],
            "scene_phase": "",
            "current_tension_level": "",
            "recent_delta": "",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "location": "",
            "time_of_day": "",
            "environment_description": "",
            "scene_template_id": "",
            "scene_premise": "",
            "role_assignments": {},
            "character_presence_constraints": {},
            "character_authority_labels": {},
            "location_entry_slots": [],
            "offstage_characters": [],
        },
        "spotlight_history": [],
        "recent_structured_moves": [],
        "director_decisions": [],
        "pending_beat_shift": default_pending_beat_shift(),
        "beat_shift_scene_snapshots": [],
    }


def ensure_orchestration_state(team_state: dict[str, Any] | None) -> dict[str, Any]:
    state = (
        team_state
        if isinstance(team_state, dict)
        else build_default_orchestration_state()
    )
    state.setdefault("spotlight_history", [])
    state.setdefault("recent_structured_moves", [])
    state.setdefault("director_decisions", [])
    state.setdefault("scene_state", build_default_orchestration_state()["scene_state"])
    ensure_beat_shift_fields(state)
    return state


def sync_orchestration_state_from_continuity(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    enforce_must_remain_presence_fn: Callable[[], None],
) -> dict[str, Any]:
    if (
        continuity_manager is None
        or getattr(continuity_manager, "scene_state", None) is None
    ):
        return orchestration_state

    enforce_must_remain_presence_fn()

    continuity_context = continuity_manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=6,
        summary_limit=3,
    )
    scene_state = continuity_manager.scene_state
    orchestration_scene = orchestration_state.setdefault("scene_state", {})
    orchestration_scene["location"] = scene_state.location or ""
    orchestration_scene["time_of_day"] = scene_state.time_of_day or ""
    orchestration_scene["environment_description"] = (
        scene_state.environment_description or ""
    )
    orchestration_scene["scene_template_id"] = scene_state.scene_template_id or ""
    orchestration_scene["scene_premise"] = scene_state.scene_premise or ""
    orchestration_scene["role_assignments"] = scene_state.role_assignments.copy()
    orchestration_scene["character_presence_constraints"] = (
        scene_state.character_presence_constraints.copy()
    )
    orchestration_scene["character_authority_labels"] = (
        scene_state.character_authority_labels.copy()
    )
    orchestration_scene["location_entry_slots"] = list(
        getattr(scene_state, "location_entry_slots", []) or []
    )
    orchestration_scene["present_characters"] = scene_state.present_characters[:]
    orchestration_scene["offstage_characters"] = list(
        getattr(scene_state, "offstage_characters", []) or []
    )
    orchestration_scene["scene_phase"] = getattr(
        scene_state.phase, "value", str(scene_state.phase)
    )
    orchestration_scene["current_tension_level"] = scene_state.current_tension_level
    orchestration_scene["recent_delta"] = scene_state.recent_delta
    orchestration_scene["opening_description"] = scene_state.opening_description
    orchestration_scene["recent_environment_events"] = (
        scene_state.recent_environment_events[-8:]
    )
    tension_history = orchestration_scene.setdefault("tension_history", [])
    current_tension = str(scene_state.current_tension_level or "")
    if current_tension and (
        not tension_history or tension_history[-1] != current_tension
    ):
        tension_history.append(current_tension)
    orchestration_scene["tension_history"] = tension_history[-8:]
    orchestration_scene["resolved_events"] = continuity_context.get(
        "resolved_events", []
    )[-8:]
    orchestration_state["continuity_active_issues"] = [
        issue.to_dict() for issue in continuity_context.get("active_issues", [])
    ]
    orchestration_state["continuity_recent_public_events"] = [
        event.to_dict() for event in continuity_context.get("recent_public_events", [])
    ]
    orchestration_state["continuity_summary_blocks"] = [
        summary.to_dict() for summary in continuity_context.get("summary_blocks", [])
    ]
    return orchestration_state


def choose_fallback_actor(
    available_actors: list[str],
    forced_speaker: str | None,
    spotlight_history: list[str],
    *,
    prefer_continuing_spotlight: bool = False,
) -> str | None:
    if forced_speaker in available_actors:
        return str(forced_speaker)

    if not available_actors:
        return None

    if prefer_continuing_spotlight and spotlight_history:
        last = str(spotlight_history[-1] or "")
        if last in available_actors:
            return last

    last_actor = spotlight_history[-1] if spotlight_history else None
    for participant in available_actors:
        if participant != last_actor:
            return participant
    return available_actors[0]


def first_unheard_available_actor_this_round(
    *,
    participant_names: list[str],
    available_actors: list[str],
    actors_used_this_round: list[str],
) -> str | None:
    """First cast member in *participant_names* who may act but has not this round."""
    avail = {str(a) for a in available_actors if str(a or "").strip()}
    for name in participant_names:
        key = str(name or "").strip()
        if key in avail and actors_used_this_round.count(key) == 0:
            return key
    return None


def apply_participation_fairness_to_decision(
    decision: dict[str, Any],
    *,
    participant_names: list[str],
    available_actors: list[str],
    actors_used_this_round: list[str],
) -> None:
    """If the chosen actor already spoke this round while another available actor has not, rotate.

    Mutates *decision* in place. Skips when ending the round or when no unheard actor exists.
    """
    if bool(decision.get("end_round")):
        return
    na = str(decision.get("next_actor") or "").strip()
    if not na or not available_actors:
        return
    unheard = first_unheard_available_actor_this_round(
        participant_names=participant_names,
        available_actors=available_actors,
        actors_used_this_round=actors_used_this_round,
    )
    if not unheard or actors_used_this_round.count(na) == 0 or na == unheard:
        return
    decision["next_actor"] = unheard
    prev = str(decision.get("reason", "") or "").strip()
    note = (
        f"Spotlight fairness: rotate to {unheard} "
        "(present participant not yet heard this response cycle)"
    )
    decision["reason"] = f"{prev} | {note}".strip(" |") if prev else note


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


def _coerce_issue_dict(issue: object) -> dict[str, Any]:
    if isinstance(issue, dict):
        return issue
    if hasattr(issue, "to_dict"):
        try:
            payload = issue.to_dict()
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
    return {}


def _is_actionable_issue_status(status: str) -> bool:
    status_clean = str(status or "").strip().lower()
    return status_clean in {"active", "escalating"}


def _get_actor_issue_statuses(
    *, actor: str, active_issues: list[dict[str, Any]]
) -> set[str]:
    statuses: set[str] = set()
    for issue in active_issues:
        participants = issue.get("participants", [])
        if not isinstance(participants, list) or actor not in participants:
            continue
        statuses.add(str(issue.get("status", "") or "").strip().lower())
    return statuses


def _actor_has_interaction_density(
    *, actor: str, active_issues: list[dict[str, Any]], available_actors: list[str]
) -> bool:
    available_set = set(available_actors)
    for issue in active_issues:
        status = str(issue.get("status", "") or "").strip().lower()
        if not _is_actionable_issue_status(status):
            continue
        participants = issue.get("participants", [])
        if not isinstance(participants, list) or actor not in participants:
            continue
        overlap = [name for name in participants if name in available_set]
        if len(overlap) >= 2:
            return True
    return False


def _find_last_move_for_actor(
    *, recent_structured_moves: list[dict[str, Any]], actor: str
) -> dict[str, Any] | None:
    for item in reversed(recent_structured_moves):
        if not isinstance(item, dict):
            continue
        if str(item.get("speaker", "") or "").strip() == actor:
            return item
    return None


def _extract_outcome_list(
    *, last_move: dict[str, Any] | None, field: str
) -> list[Any] | None:
    if last_move is None or field not in last_move:
        return None
    value = last_move.get(field)
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    return value


def _has_momentum_signal(
    *, last_move: dict[str, Any] | None
) -> bool | None:
    """Return True/False when outcome data is present; None when unknown.

    Required safeguard: if fields are missing, treat momentum as neutral.
    """

    consequences = _extract_outcome_list(last_move=last_move, field="consequences")
    issue_updates = _extract_outcome_list(last_move=last_move, field="issue_updates")
    presence_changes = _extract_outcome_list(last_move=last_move, field="presence_changes")
    if consequences is None and issue_updates is None and presence_changes is None:
        return None
    return bool(consequences or issue_updates or presence_changes)


def _has_weak_repetition_signal(
    *, last_move: dict[str, Any] | None
) -> bool | None:
    """Return True/False when outcome data is complete; None when unknown.

    Weak repetition signal requires all three fields present and empty.
    Missing fields must be treated as neutral.
    """

    consequences = _extract_outcome_list(last_move=last_move, field="consequences")
    issue_updates = _extract_outcome_list(last_move=last_move, field="issue_updates")
    presence_changes = _extract_outcome_list(last_move=last_move, field="presence_changes")
    if consequences is None or issue_updates is None or presence_changes is None:
        return None
    return not consequences and not issue_updates and not presence_changes


def assign_progression_band_for_actor(
    *,
    actor: str,
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
    recent_structured_moves: list[dict[str, Any]],
) -> Literal["high", "med", "low"]:
    """Assign HIGH/MED/LOW using only approved structural signals.

    Momentum and weak repetition signals must be neutral when outcome fields are missing.
    """

    actor = str(actor or "").strip()
    if not actor:
        return "med"

    statuses = _get_actor_issue_statuses(actor=actor, active_issues=active_issues)
    in_escalating = "escalating" in statuses
    in_active = "active" in statuses
    in_actionable = in_escalating or in_active

    last_move = _find_last_move_for_actor(
        recent_structured_moves=recent_structured_moves,
        actor=actor,
    )
    momentum_signal = _has_momentum_signal(last_move=last_move)
    repetition_signal = _has_weak_repetition_signal(last_move=last_move)

    has_interaction_density = _actor_has_interaction_density(
        actor=actor,
        active_issues=active_issues,
        available_actors=available_actors,
    )

    has_momentum = bool(momentum_signal) and in_actionable

    if in_escalating or (in_active and has_interaction_density) or (in_active and has_momentum):
        return "high"

    if not in_actionable and repetition_signal is True:
        return "low"

    return "med"


def _escalating_issue_participants(active_issues: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        if str(issue.get("status", "") or "").strip().lower() != "escalating":
            continue
        participants = issue.get("participants", [])
        if isinstance(participants, list):
            out.update(str(item) for item in participants if str(item).strip())
    return out


def _restrict_high_to_escalating_subset_if_any(
    *,
    high_actors: list[str],
    active_issues: list[dict[str, Any]],
) -> list[str]:
    """Option 1: if any HIGH participates in escalating issues, narrow to that subset."""
    escalating = _escalating_issue_participants(active_issues)
    restricted = [a for a in high_actors if a in escalating]
    return restricted if restricted else list(high_actors)


def _prev_spotlight_expel_proxy(
    *,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
) -> str | None:
    """Speaker to deprioritize for 'not previous speaker' tie-break (Stage A)."""
    if spotlight_history:
        s = str(spotlight_history[-1] or "").strip()
        return s or None
    if recent_structured_moves:
        last = recent_structured_moves[-1]
        if isinstance(last, dict):
            sp = str(last.get("speaker", "") or "").strip()
            return sp or None
    return None


def _last_spotlight_index(actor: str, spotlight_history: list[str]) -> int | None:
    for i in range(len(spotlight_history) - 1, -1, -1):
        if spotlight_history[i] == actor:
            return i
    return None


def _least_recent_spotlight_actor(
    candidates: list[str],
    *,
    spotlight_history: list[str],
    available_actors: list[str],
) -> str:
    """Prefer never spotlighted, then smallest last index in history, then list order."""

    def sort_key(name: str) -> tuple[int, int, int]:
        li = _last_spotlight_index(name, spotlight_history)
        try:
            av_idx = available_actors.index(name)
        except ValueError:
            av_idx = len(available_actors)
        if li is None:
            return (0, 0, av_idx)
        return (1, li, av_idx)

    return min(candidates, key=sort_key)


def _pick_high_progression_actor_once(
    *,
    candidate_high_list: list[str],
    director_selected_actor: str,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
    available_actors: list[str],
) -> str:
    """Single pass: director preference, expel proxy, least-recent spotlight, list order."""
    if not candidate_high_list:
        return ""

    if director_selected_actor in candidate_high_list:
        return director_selected_actor

    expel = _prev_spotlight_expel_proxy(
        spotlight_history=spotlight_history,
        recent_structured_moves=recent_structured_moves,
    )
    pool = candidate_high_list
    if expel:
        without = [a for a in candidate_high_list if a != expel]
        if without:
            pool = without

    return _least_recent_spotlight_actor(
        pool,
        spotlight_history=spotlight_history,
        available_actors=available_actors,
    )


def _pick_high_progression_actor(
    *,
    full_high_list: list[str],
    director_selected_actor: str,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
) -> str:
    """Escalating subset first, then tie-break policy and narrow anti-loop guard."""
    working = _restrict_high_to_escalating_subset_if_any(
        high_actors=full_high_list,
        active_issues=active_issues,
    )
    chosen = _pick_high_progression_actor_once(
        candidate_high_list=working,
        director_selected_actor=director_selected_actor,
        spotlight_history=spotlight_history,
        recent_structured_moves=recent_structured_moves,
        available_actors=available_actors,
    )

    prev_spot = (
        str(spotlight_history[-1] or "").strip()
        if spotlight_history
        else ""
    )
    if (
        prev_spot
        and chosen == prev_spot
        and len(full_high_list) >= 2
    ):
        rerun_high = [a for a in full_high_list if a != prev_spot]
        if len(rerun_high) >= 1:
            working2 = _restrict_high_to_escalating_subset_if_any(
                high_actors=rerun_high,
                active_issues=active_issues,
            )
            if working2:
                chosen = _pick_high_progression_actor_once(
                    candidate_high_list=working2,
                    director_selected_actor=director_selected_actor,
                    spotlight_history=spotlight_history,
                    recent_structured_moves=recent_structured_moves,
                    available_actors=available_actors,
                )

    return chosen


def resolve_progression_override_actor(
    *,
    director_selected_actor: str,
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
    recent_structured_moves: list[dict[str, Any]],
    spotlight_history: list[str] | None = None,
    progression_enforcement_gate: bool = False,
) -> str | None:
    """Apply band-based progression override for Director selection.

    When ``progression_enforcement_gate`` is False (default):
    - Override ONLY if Director pick is LOW, another actor is HIGH, and an
      actionable issue exists.

    When gate is True (beat-shift pending or high progression pressure):
    - Preserve the explicit MED branch, but return no override for MED picks.
    """

    director_selected_actor = str(director_selected_actor or "").strip()
    if not director_selected_actor or director_selected_actor not in available_actors:
        return None

    sh = [str(x or "").strip() for x in (spotlight_history or []) if str(x or "").strip()]

    unresolved_actionable_issue_exists = any(
        _is_actionable_issue_status(str(issue.get("status", "") or ""))
        for issue in active_issues
        if isinstance(issue, dict)
    )
    if not unresolved_actionable_issue_exists:
        return None

    bands: dict[str, Literal["high", "med", "low"]] = {}
    for actor in available_actors:
        bands[actor] = assign_progression_band_for_actor(
            actor=actor,
            available_actors=available_actors,
            active_issues=active_issues,
            recent_structured_moves=recent_structured_moves,
        )

    director_band = bands.get(director_selected_actor)
    high_actors = [actor for actor in available_actors if bands.get(actor) == "high"]
    if not high_actors:
        return None

    if director_band == "low":
        return _pick_high_progression_actor(
            full_high_list=high_actors,
            director_selected_actor=director_selected_actor,
            spotlight_history=sh,
            recent_structured_moves=recent_structured_moves,
            available_actors=available_actors,
            active_issues=active_issues,
        )

    if progression_enforcement_gate and director_band == "med":
        return None

    return None


def append_turn_to_orchestration_state(
    *,
    orchestration_state: dict[str, Any],
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    consequences: list[str] | None = None,
    issue_updates: list[dict[str, Any]] | None = None,
    presence_changes: list[dict[str, Any]] | None = None,
    spotlight_history_limit: int,
    structured_move_history_limit: int,
    director_decision_history_limit: int,
    environment_history_limit: int,
    tension_history_limit: int,
) -> dict[str, Any]:
    orchestration_state.setdefault("spotlight_history", []).append(next_actor)
    orchestration_state["spotlight_history"] = orchestration_state["spotlight_history"][
        -spotlight_history_limit:
    ]
    move_entry: dict[str, Any] = {
        "speaker": next_actor,
        "action": move.get("action", ""),
        "dialogue": move.get("dialogue", ""),
        "motivation": move.get("motivation", {}),
        "environment_event": decision.get("environment_event", ""),
        "tension_shift": decision.get("tension_shift", ""),
        "audibility": str(move.get("audibility", "public") or "public"),
        "audience": list(move.get("audience") or []),
    }
    try:
        msv = int(str(move.get("move_schema_version", 0) or 0) or 0)
    except (TypeError, ValueError):
        msv = 0
    if msv == 2:
        move_entry["move_schema_version"] = 2
        raw_beats = move.get("beats")
        if isinstance(raw_beats, list):
            move_entry["beats"] = [
                dict(b) if isinstance(b, dict) else b for b in raw_beats
            ]
    # Persist existing computed outcome signals when available (no new logic).
    if consequences is not None:
        move_entry["consequences"] = list(consequences)
    if issue_updates is not None:
        move_entry["issue_updates"] = list(issue_updates)
    if presence_changes is not None:
        move_entry["presence_changes"] = list(presence_changes)

    orchestration_state.setdefault("recent_structured_moves", []).append(move_entry)
    orchestration_state["recent_structured_moves"] = orchestration_state[
        "recent_structured_moves"
    ][-structured_move_history_limit:]
    orchestration_state.setdefault("director_decisions", []).append(decision)
    orchestration_state["director_decisions"] = orchestration_state[
        "director_decisions"
    ][-director_decision_history_limit:]

    scene_state = orchestration_state.setdefault("scene_state", {})
    scene_state.setdefault("recent_environment_events", [])
    scene_state.setdefault("tension_history", [])
    if decision.get("environment_event"):
        scene_state["recent_environment_events"].append(decision["environment_event"])
        scene_state["recent_environment_events"] = scene_state[
            "recent_environment_events"
        ][-environment_history_limit:]
    if decision.get("tension_shift"):
        scene_state["tension_history"].append(decision["tension_shift"])
        scene_state["tension_history"] = scene_state["tension_history"][
            -tension_history_limit:
        ]
    return orchestration_state


def build_recent_scene_context(
    *,
    chat_history: list[dict[str, Any]],
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    build_recent_dialogue_history_fn: Callable[
        [list[dict[str, Any]], int], list[dict[str, str]]
    ],
    limit: int = 6,
) -> tuple[str, dict[str, Any]]:
    continuity_snapshot = (
        continuity_manager.get_snapshot() if continuity_manager is not None else None
    )
    orchestration_continuity_context = (
        continuity_manager.get_orchestration_context(
            active_issue_limit=3,
            recent_event_limit=3,
            summary_limit=2,
        )
        if continuity_manager is not None
        else None
    )
    generated_summary_blocks = (
        continuity_manager.summary_blocks[:] if continuity_manager is not None else []
    )
    available_summary_blocks = (
        continuity_manager.retrieve_summary_blocks(limit=0)
        if continuity_manager is not None
        else []
    )
    selected_summary_blocks = (
        orchestration_continuity_context.get("summary_blocks", [])
        if orchestration_continuity_context is not None
        else []
    )
    summary_block_audit = build_summary_block_audit_metadata(
        generated_blocks=generated_summary_blocks,
        available_blocks=available_summary_blocks,
        selected_blocks=selected_summary_blocks,
        selection_reason=(
            "ranked deterministic retrieval for narrator scene context"
            if selected_summary_blocks
            else ""
        ),
        skipped_reason=(
            "Continuity manager unavailable"
            if continuity_manager is None
            else (
                "No summary blocks generated yet"
                if not generated_summary_blocks
                else (
                    "No narrator summary blocks available after retrieval"
                    if not selected_summary_blocks
                    else ""
                )
            )
        ),
        summary_generation_eligible=(
            continuity_manager is not None
            and continuity_manager.summary_interval > 0
            and continuity_manager.turn_counter >= continuity_manager.summary_interval
        ),
        summary_limit=2,
    )
    scene_state = (
        continuity_snapshot.scene_state.to_dict()
        if continuity_snapshot is not None
        else orchestration_state.get("scene_state", {})
    )
    parts: list[str] = []

    opening_description = str(scene_state.get("opening_description", "") or "").strip()
    if opening_description:
        parts.append(f"OPENING DESCRIPTION:\n{opening_description}")

    location = str(scene_state.get("location", "") or "").strip()
    if location:
        parts.append(f"LOCATION:\n{location}")

    environment_description = str(
        scene_state.get("environment_description", "") or ""
    ).strip()
    if environment_description:
        parts.append(f"CURRENT ENVIRONMENT:\n{environment_description}")

    recent_environment_events = scene_state.get("recent_environment_events", [])[-3:]
    if recent_environment_events:
        parts.append(
            "RECENT ENVIRONMENT EVENTS:\n"
            + "\n".join(str(item) for item in recent_environment_events)
        )

    recent_tension = scene_state.get("tension_history", [])[-3:]
    if not recent_tension:
        current_tension_level = str(
            scene_state.get("current_tension_level", "") or ""
        ).strip()
        if current_tension_level:
            recent_tension = [current_tension_level]
    if recent_tension:
        parts.append(
            "RECENT TENSION SHIFTS:\n" + "\n".join(str(item) for item in recent_tension)
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("active_issues")
    ):
        parts.append(
            "ACTIVE ISSUES:\n"
            + "\n".join(
                issue.description
                for issue in orchestration_continuity_context.get("active_issues", [])
            )
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("recent_public_events")
    ):
        parts.append(
            "RECENT PUBLIC EVENTS:\n"
            + "\n".join(
                event.summary
                for event in orchestration_continuity_context.get(
                    "recent_public_events", []
                )
            )
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("summary_blocks")
    ):
        parts.append(
            "OLDER CONTINUITY SUMMARY BLOCKS:\n"
            + "\n".join(
                "; ".join(summary.key_events)
                for summary in orchestration_continuity_context.get(
                    "summary_blocks", []
                )
            )
        )

    if orchestration_continuity_context is not None:
        scene_canon_anchors = orchestration_continuity_context.get(
            "scene_canon_anchors", []
        )[:4]
        if scene_canon_anchors:
            parts.append(
                "SCENE CANON:\n"
                + "\n".join(anchor.statement for anchor in scene_canon_anchors)
            )

    recent_dialogue = build_recent_dialogue_history_fn(chat_history, limit)
    if recent_dialogue:
        transcript = "\n".join(
            f"{item['speaker']}: {item['content']}" for item in recent_dialogue
        )
        parts.append(f"RECENT TRANSCRIPT:\n{transcript}")

    return "\n\n".join(parts), summary_block_audit
