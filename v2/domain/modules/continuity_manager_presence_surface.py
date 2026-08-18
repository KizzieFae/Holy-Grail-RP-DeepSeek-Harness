"""Presence routing and scratch pipeline surface for ContinuityManager (mechanical extraction)."""

from __future__ import annotations

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
    manager_apply_canonical_reentry_scratch as apply_canonical_reentry_impl,
    manager_ensure_at_least_one_present_character_scratch as ensure_one_present_scratch_impl,
    manager_assert_presence_invariant_after_reconcile_scratch as assert_invariant_scratch_impl,
)


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


def apply_canonical_reentry_scratch(
    manager: Any, scratch: PresenceAuthorityScratch, character_name: str
) -> None:
    apply_canonical_reentry_impl(manager, scratch, character_name)


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
