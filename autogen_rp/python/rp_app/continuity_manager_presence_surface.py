"""Presence routing and scratch pipeline surface for ContinuityManager (mechanical extraction)."""

from __future__ import annotations

import re
from typing import Any, Callable

from continuity_presence_helpers import PresenceAuthorityScratch
from continuity_presence_pipeline import (
    manager_apply_pre_turn_user_presence_routing as pre_turn_presence_routing_impl,
    manager_apply_must_remain_presence_from_fn as apply_must_remain_presence_impl,
    manager_bootstrap_present_characters_from_cast as bootstrap_present_from_cast_impl,
    manager_ensure_at_least_one_present_character as ensure_one_present_impl,
    manager_reconcile_presence_lists as reconcile_presence_lists_impl,
    manager_resync_presence_through_authority as resync_presence_impl,
    manager_presence_scratch_from_scene_state as presence_scratch_impl,
    manager_purge_excursion_participants_from_offstage_scratch as purge_excursion_offstage_impl,
    manager_strip_active_excursions_from_focal_scratch as strip_excursions_focal_impl,
    manager_synchronize_presence_from_canonical_authority as synchronize_presence_impl,
    manager_reconcile_presence_lists_scratch as reconcile_presence_scratch_impl,
    manager_process_structured_reentries_from_move_scratch as process_reentries_impl,
    manager_apply_canonical_reentry_scratch as apply_canonical_reentry_impl,
    manager_apply_canonical_exit_offstage_transition_scratch as apply_exit_offstage_impl,
    manager_ensure_at_least_one_present_character_scratch as ensure_one_present_scratch_impl,
    manager_assert_presence_invariant_after_reconcile_scratch as assert_invariant_scratch_impl,
)

from continuity_manager_issue_surface import (
    acting_character_required_by_active_confrontation,
)


def acting_character_named_in_current_move(
    acting_character: str, move: dict[str, Any]
) -> bool:
    tokens: list[str] = []
    for segment in acting_character.replace("_", " ").split():
        s = segment.strip()
        if len(s) >= 3:
            tokens.append(s.lower())
    if not tokens:
        return False
    motivation = move.get("motivation", {})
    if not isinstance(motivation, dict):
        motivation = {}
    chunks = [
        str(move.get("action", "") or ""),
        str(move.get("dialogue", "") or ""),
        str(motivation.get("goal", "") or ""),
        str(motivation.get("tactic", "") or ""),
    ]
    text = " ".join(chunks).lower()
    for token in tokens:
        if re.search(rf"\b{re.escape(token)}\b", text):
            return True
    return False


def should_skip_soft_exit_presence_removal(
    manager: Any, acting_character: str, move: dict[str, Any]
) -> bool:
    if acting_character_named_in_current_move(acting_character, move):
        return True
    if acting_character_required_by_active_confrontation(manager, acting_character):
        return True
    return False


def resync_presence_through_authority(manager: Any) -> None:
    resync_presence_impl(manager)


def presence_scratch_from_scene_state(manager: Any) -> PresenceAuthorityScratch:
    return presence_scratch_impl(manager)


def strip_active_excursions_from_focal_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    strip_excursions_focal_impl(manager, scratch)


def purge_excursion_participants_from_offstage_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    purge_excursion_offstage_impl(manager, scratch)


def synchronize_presence_from_canonical_authority(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    synchronize_presence_impl(manager, scratch)


def reconcile_presence_lists_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    reconcile_presence_scratch_impl(manager, scratch)


def process_structured_reentries_from_move_scratch(
    manager: Any, move: dict[str, Any], scratch: PresenceAuthorityScratch
) -> None:
    process_reentries_impl(manager, move, scratch)


def apply_canonical_reentry_scratch(
    manager: Any, scratch: PresenceAuthorityScratch, character_name: str
) -> None:
    apply_canonical_reentry_impl(manager, scratch, character_name)


def apply_canonical_exit_offstage_transition_scratch(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    *,
    consequence_tags: set[str],
    scene_dict: dict[str, Any],
    scratch: PresenceAuthorityScratch,
) -> None:
    apply_exit_offstage_impl(
        manager,
        acting_character,
        move,
        consequence_tags=consequence_tags,
        scene_dict=scene_dict,
        scratch=scratch,
        should_skip_soft_exit_presence_removal=lambda a, m: should_skip_soft_exit_presence_removal(
            manager, a, m
        ),
    )


def ensure_at_least_one_present_character_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    ensure_one_present_scratch_impl(manager, scratch)


def assert_presence_invariant_after_reconcile_scratch(
    scratch: PresenceAuthorityScratch,
) -> None:
    assert_invariant_scratch_impl(scratch)


def reconcile_presence_lists(manager: Any) -> None:
    reconcile_presence_lists_impl(manager)


def ensure_at_least_one_present_character(manager: Any) -> None:
    ensure_one_present_impl(manager)


def apply_pre_turn_user_presence_routing(
    manager: Any,
    *,
    trigger_text: str,
    participant_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
    pending_forced_speaker: str | None,
) -> None:
    pre_turn_presence_routing_impl(
        manager,
        trigger_text=trigger_text,
        participant_names=participant_names,
        get_character_display_name_fn=get_character_display_name_fn,
        pending_forced_speaker=pending_forced_speaker,
    )


def apply_must_remain_presence_from_fn(
    manager: Any, get_must_remain_characters_fn: Callable[[dict[str, Any]], Any]
) -> None:
    apply_must_remain_presence_impl(manager, get_must_remain_characters_fn)


def bootstrap_present_characters_from_cast(
    manager: Any, character_names: list[str]
) -> None:
    bootstrap_present_from_cast_impl(manager, character_names)
