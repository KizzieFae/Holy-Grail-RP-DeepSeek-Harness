"""Commit-time memory write policy (deterministic; no validation coupling).

Observer recipient checks accept optional ``display_name_for_key`` so episodic
writes align with orchestration when ``present_characters`` uses display labels
and ``character_names`` uses agent keys (GitHub #99).
"""

from __future__ import annotations

from typing import Any, Callable

from perception_audibility import (
    event_knowledge_recipients,
    normalize_move_audibility,
)
from perceptual_visibility_projection import assemble_perceptual_visibility_for_viewer
from response_validation_selection import eligible_agent_keys_for_present_characters

from . import storage


def _episodic_interpretation_from_director_decision(
    director_decision: dict[str, Any],
    motivation: Any,
) -> str:
    """Episodic interpretation string for the acting character (GitHub #208).

    Tier 1: ``director_model_reason`` when the key exists and is non-empty after ``strip``.
    Verbatim semantics — no display-name normalization.

    Tier 2: merged operator ``reason`` when tier 1 does not apply.

    Tier 3: ``goal`` / ``tactic`` motivation join matching prior ``writes`` behavior.
    """
    if "director_model_reason" in director_decision:
        raw_mr = director_decision.get("director_model_reason")
        tier1 = str(raw_mr or "").strip()
        if tier1:
            return tier1
    tier2 = str(director_decision.get("reason", "") or "").strip()
    if tier2:
        return tier2
    if isinstance(motivation, dict):
        goal = str(motivation.get("goal", "") or "").strip()
        tactic = str(motivation.get("tactic", "") or "").strip()
        return "; ".join(
            part
            for part in [
                f"goal={goal}" if goal else "",
                f"tactic={tactic}" if tactic else "",
            ]
            if part
        )
    return ""


def resolve_present_characters(
    *,
    continuity_manager: Any | None,
    char_names: list[str],
) -> list[str]:
    """Canonical present list for perception: scene_state.present_characters if non-empty, else char_names."""
    if continuity_manager is not None:
        scene_state = getattr(continuity_manager, "scene_state", None)
        if scene_state is not None:
            raw = getattr(scene_state, "present_characters", None)
            if isinstance(raw, list):
                out = [str(x).strip() for x in raw if str(x or "").strip()]
                if out:
                    return out
    return list(char_names)


def _observer_recipient_agent_keys(
    recipients: set[str],
    character_names: list[str],
    *,
    display_name_for_key: Callable[[str], str] | None,
) -> set[str]:
    """Map recipient labels (display or key) to participant agent keys for membership checks."""
    if not display_name_for_key:
        return set(recipients)
    return set(
        eligible_agent_keys_for_present_characters(
            list(recipients),
            character_names,
            display_name_for_key=display_name_for_key,
        )
    )


def commit_character_turn_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    present_characters: list[str],
    build_memory_fact_summary_fn: Callable[[str, dict[str, Any]], str],
    display_name_for_key: Callable[[str], str] | None = None,
    perceptual_record: Any | None = None,
) -> None:
    if not state_manager or not acting_character:
        return

    move_norm = normalize_move_audibility(
        dict(move), acting_character, present_characters
    )
    motivation = move_norm.get("motivation", {})
    event_summary = build_memory_fact_summary_fn(acting_character, move_norm)

    interpretation = _episodic_interpretation_from_director_decision(
        director_decision, motivation
    )

    storage.append_actor_episodic(
        state_manager,
        acting_character,
        event_summary=event_summary,
        interpretation=interpretation,
    )

    if perceptual_record is not None:
        for name in character_names:
            if not name or name == acting_character:
                continue
            assembly = assemble_perceptual_visibility_for_viewer(
                perceptual_record,
                viewer_character=name,
                present_characters=present_characters,
                acting_character=acting_character,
            )
            perceived = str(assembly.content or "").strip()
            if not perceived:
                continue
            storage.append_observer_episodic(
                state_manager,
                name,
                observed_line=f"Observed: {perceived}",
            )
        return

    recipients_raw = set(
        event_knowledge_recipients(
            move_norm,
            acting_character=acting_character,
            present_characters=present_characters,
        )
    )
    recipient_keys = _observer_recipient_agent_keys(
        recipients_raw,
        character_names,
        display_name_for_key=display_name_for_key,
    )
    observed_line = f"Observed: {event_summary}"
    for name in character_names:
        if not name or name == acting_character:
            continue
        if name not in recipient_keys:
            continue
        storage.append_observer_episodic(
            state_manager, name, observed_line=observed_line
        )


def commit_user_message_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    user_name: str,
    user_input: str,
    summarize_user_message_fn: Callable[[str, str], str],
) -> None:
    if not state_manager or not user_name:
        return
    summary = summarize_user_message_fn(user_name, user_input)
    for name in character_names:
        state = state_manager.get_state(name)
        if state is None:
            continue
        state.remember_user_interaction(user_name, summary)
