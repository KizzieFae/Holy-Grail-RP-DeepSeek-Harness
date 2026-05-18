"""Presence scratch pipeline orchestration for ContinuityManager (Issue #155 Slice C).

Canonical sequence matches pre-extraction ContinuityManager:

1. Build scratch from SceneState
2. Reconcile presence lists on scratch
3. (Full resync path) assert invariant → ensure at least one present → sync to SceneState
4. Sync applies excursion strip/purge then copies lists into SceneState

Pre-turn and must_remain paths use the same primitives in the same order as before.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from continuity_presence_helpers import (
    PresenceAuthorityScratch,
    apply_canonical_exit_offstage_transition_scratch,
    apply_canonical_reentry_scratch,
    assert_presence_invariant_after_reconcile_scratch,
    ensure_at_least_one_present_character_scratch,
    presence_scratch_from_scene_state,
    process_structured_reentries_from_move_scratch,
    purge_excursion_participants_from_offstage_scratch,
    reconcile_presence_lists_scratch,
    strip_active_excursions_from_focal_scratch,
)

from user_presence_signals import (
    apply_user_trigger_to_offstage_on_scratch,
    release_pending_forced_speaker_on_scratch,
)

logger = logging.getLogger(__name__)


def manager_presence_scratch_from_scene_state(manager: Any) -> PresenceAuthorityScratch:
    assert manager.scene_state is not None
    return presence_scratch_from_scene_state(manager.scene_state)


def manager_strip_active_excursions_from_focal_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    strip_active_excursions_from_focal_scratch(
        scratch, manager.active_excursion_character_ids()
    )


def manager_purge_excursion_participants_from_offstage_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    purge_excursion_participants_from_offstage_scratch(
        scratch, manager.active_excursion_character_ids()
    )


def manager_synchronize_presence_from_canonical_authority(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    if manager.scene_state is None:
        return
    manager_strip_active_excursions_from_focal_scratch(manager, scratch)
    manager_purge_excursion_participants_from_offstage_scratch(manager, scratch)
    manager.scene_state.present_characters = list(scratch.present_characters)
    manager.scene_state.offstage_characters = list(scratch.offstage_characters)
    manager.scene_state.character_presence_status = dict(
        scratch.character_presence_status
    )
    manager.scene_state.absent_but_relevant = list(scratch.absent_but_relevant)


def manager_reconcile_presence_lists_scratch(
    manager: Any, scratch: PresenceAuthorityScratch
) -> None:
    reconcile_presence_lists_scratch(scratch)


def manager_process_structured_reentries_from_move_scratch(
    manager: Any, move: dict[str, Any], scratch: PresenceAuthorityScratch
) -> None:
    process_structured_reentries_from_move_scratch(move, scratch)


def manager_apply_canonical_reentry_scratch(
    manager: Any, scratch: PresenceAuthorityScratch, character_name: str
) -> None:
    apply_canonical_reentry_scratch(scratch, character_name)


def manager_apply_canonical_exit_offstage_transition_scratch(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    *,
    consequence_tags: set[str],
    scene_dict: dict[str, Any],
    scratch: PresenceAuthorityScratch,
    should_skip_soft_exit_presence_removal: Callable[[str, dict[str, Any]], bool],
) -> None:
    if manager.scene_state is None:
        return
    apply_canonical_exit_offstage_transition_scratch(
        acting_character,
        move,
        consequence_tags=consequence_tags,
        scene_dict=scene_dict,
        scratch=scratch,
        character_presence_constraints=dict(
            manager.scene_state.character_presence_constraints or {}
        ),
        should_skip_soft_exit_presence_removal=should_skip_soft_exit_presence_removal,
    )


def manager_ensure_at_least_one_present_character_scratch(
    manager: Any,
    scratch: PresenceAuthorityScratch,
    *,
    exclude_same_beat_reentry_for: str | None = None,
) -> None:
    if manager.scene_state is None:
        return
    cast = [
        str(k).strip()
        for k in manager.scene_state.role_assignments.keys()
        if str(k).strip()
    ]
    ensure_at_least_one_present_character_scratch(
        scratch,
        cast=cast,
        e_active=manager.active_excursion_character_ids(),
        log=logger,
        exclude_same_beat_reentry_for=exclude_same_beat_reentry_for,
    )


def manager_assert_presence_invariant_after_reconcile_scratch(
    scratch: PresenceAuthorityScratch,
) -> None:
    assert_presence_invariant_after_reconcile_scratch(scratch, log=logger)


def manager_resync_presence_through_authority(manager: Any) -> None:
    """Full presence pipeline: reconcile → invariant → ensure-one → sync (single writer)."""
    if manager.scene_state is None:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_assert_presence_invariant_after_reconcile_scratch(scratch)
    manager_ensure_at_least_one_present_character_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_restore_excursion_participants_to_focal_after_close(
    manager: Any, participant_character_ids: list[str]
) -> None:
    """Re-commit excursion participants to focal presence after their excursion closes.

    While an excursion is active, ``E_active`` participants are stripped from
    ``present_characters``; a plain resync after close does not re-append them if
    other focal characters remained present (the deadlock guard only runs when
    ``present_characters`` is empty). This path applies the same canonical reentry
    scratch updates used for structured ``presence_changes`` / entry tags so close
    restores participation without narrator or perception inference (GitHub #214 Tier B).
    """
    if manager.scene_state is None:
        return
    e_active = manager.active_excursion_character_ids()
    scratch = manager_presence_scratch_from_scene_state(manager)
    for raw in participant_character_ids:
        pid = str(raw or "").strip()
        if not pid or pid in e_active:
            continue
        manager_apply_canonical_reentry_scratch(manager, scratch, pid)
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_assert_presence_invariant_after_reconcile_scratch(scratch)
    manager_ensure_at_least_one_present_character_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_apply_pre_turn_user_presence_routing(
    manager: Any,
    *,
    trigger_text: str,
    participant_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
    pending_forced_speaker: Optional[str],
) -> None:
    """Apply Traveler offstage hints through the single presence sync path."""
    if manager.scene_state is None:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    apply_user_trigger_to_offstage_on_scratch(
        scratch=scratch,
        trigger_text=trigger_text,
        participant_names=participant_names,
        get_character_display_name_fn=get_character_display_name_fn,
    )
    release_pending_forced_speaker_on_scratch(
        scratch=scratch,
        pending_forced_speaker=pending_forced_speaker,
        participant_names=participant_names,
    )
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_apply_must_remain_presence_from_fn(
    manager: Any, get_must_remain_characters_fn: Callable[[dict[str, Any]], Any]
) -> None:
    if manager.scene_state is None:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    scene_dict = manager.scene_state.to_dict()
    scene_dict["present_characters"] = list(scratch.present_characters)
    scene_dict["offstage_characters"] = list(scratch.offstage_characters)
    scene_dict["character_presence_status"] = dict(scratch.character_presence_status)
    scene_dict["absent_but_relevant"] = list(scratch.absent_but_relevant)
    must_remain = get_must_remain_characters_fn(scene_dict)
    for character_name in must_remain:
        ch = str(character_name or "").strip()
        if not ch:
            continue
        st = str(scratch.character_presence_status.get(ch, "") or "").strip()
        if st == "temporary_offstage":
            continue
        manager_apply_canonical_reentry_scratch(manager, scratch, ch)
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_assert_presence_invariant_after_reconcile_scratch(scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_bootstrap_present_characters_from_cast(
    manager: Any, character_names: list[str]
) -> None:
    """If on-stage roster is empty, seed it from the cast list (restore / init guard)."""
    if manager.scene_state is None:
        return
    if manager.scene_state.present_characters:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    scratch.present_characters = [
        str(x).strip() for x in character_names if str(x or "").strip()
    ]
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_reconcile_presence_lists(manager: Any) -> None:
    """Drop absent entries that are still present; dedupe both lists (synced write path)."""
    if manager.scene_state is None:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)


def manager_ensure_at_least_one_present_character(manager: Any) -> None:
    """Deadlock guard vis scratch + single sync (see scratch helper for tier rules)."""
    if manager.scene_state is None:
        return
    scratch = manager_presence_scratch_from_scene_state(manager)
    manager_ensure_at_least_one_present_character_scratch(manager, scratch)
    manager_synchronize_presence_from_canonical_authority(manager, scratch)
