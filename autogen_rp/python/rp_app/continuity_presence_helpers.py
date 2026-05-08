"""Presence reconciliation helpers for continuity (Issue #149 Slice 4).

Scratch mutations and read-only inputs only. Authoritative ``SceneState`` writes stay
in ``ContinuityManager._synchronize_presence_from_canonical_authority`` (single writer).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Set

from scene_exit_detection import (
    authored_prose_suppresses_physical_departure,
    detect_exit_from_scene,
    has_hard_scene_departure_evidence,
    has_scene_reentry_evidence,
    structured_presence_exit_for_character,
)

from continuity_state import SceneState

@dataclass
class PresenceAuthorityScratch:
    """Mutable staging bundle for presence fields before a single sync to ``SceneState``."""

    present_characters: list[str]
    offstage_characters: list[str]
    character_presence_status: dict[str, str]
    absent_but_relevant: list[str]


def presence_scratch_from_scene_state(ss: SceneState) -> PresenceAuthorityScratch:
    return PresenceAuthorityScratch(
        present_characters=list(ss.present_characters or []),
        offstage_characters=list(ss.offstage_characters or []),
        character_presence_status=dict(ss.character_presence_status or {}),
        absent_but_relevant=list(ss.absent_but_relevant or []),
    )


def strip_active_excursions_from_focal_scratch(
    scratch: PresenceAuthorityScratch, e_active: Set[str]
) -> None:
    """Enforce P_focal ∩ E_active = ∅ before committing presence."""
    if not e_active:
        return
    scratch.present_characters = [
        n for n in scratch.present_characters if str(n).strip() not in e_active
    ]


def purge_excursion_participants_from_offstage_scratch(
    scratch: PresenceAuthorityScratch, e_active: Set[str]
) -> None:
    """Excursion participants must not be soft-offstage (Issue #81 Slice B).

    Clears ``offstage_characters`` and presence-status rows for ``E_active`` in the
    same scratch write as focal stripping — no partial excursion-without-presence-fix.
    """
    if not e_active:
        return
    banned = frozenset(str(x).strip() for x in e_active if str(x).strip())
    scratch.offstage_characters = [
        str(n).strip()
        for n in scratch.offstage_characters
        if str(n).strip() and str(n).strip() not in banned
    ]
    for pid in banned:
        scratch.character_presence_status.pop(pid, None)


def reconcile_presence_lists_scratch(scratch: PresenceAuthorityScratch) -> None:
    seen_present: set[str] = set()
    deduped_present: list[str] = []
    for name in scratch.present_characters:
        n = str(name).strip()
        if not n or n in seen_present:
            continue
        seen_present.add(n)
        deduped_present.append(n)
    scratch.present_characters = deduped_present
    present_set = set(scratch.present_characters)
    filtered_absent = [
        str(n).strip()
        for n in scratch.absent_but_relevant
        if str(n).strip() and str(n).strip() not in present_set
    ]
    seen_absent: set[str] = set()
    deduped_absent: list[str] = []
    for n in filtered_absent:
        if n in seen_absent:
            continue
        seen_absent.add(n)
        deduped_absent.append(n)
    scratch.absent_but_relevant = deduped_absent

    seen_off: set[str] = set()
    deduped_off: list[str] = []
    for n in scratch.offstage_characters:
        n = str(n).strip()
        if not n or n in seen_off:
            continue
        if n in present_set:
            continue
        seen_off.add(n)
        deduped_off.append(n)
    scratch.offstage_characters = deduped_off


def apply_canonical_reentry_scratch(
    scratch: PresenceAuthorityScratch, character_name: str
) -> None:
    name = str(character_name or "").strip()
    if not name:
        return
    scratch.offstage_characters = [n for n in scratch.offstage_characters if n != name]
    if name not in scratch.present_characters:
        scratch.present_characters.append(name)
    scratch.absent_but_relevant = [n for n in scratch.absent_but_relevant if n != name]
    scratch.character_presence_status[name] = "onstage"


def process_structured_reentries_from_move_scratch(
    move: dict[str, Any], scratch: PresenceAuthorityScratch
) -> None:
    seen: set[str] = set()
    reentry_changes = frozenset({"entry", "return", "reenter", "re-entry"})
    for item in move.get("presence_changes") or []:
        if not isinstance(item, dict):
            continue
        ch = str(item.get("character", "") or "").strip()
        chg = str(item.get("change", "") or "").lower().replace("_", "-")
        if not ch or ch in seen or chg not in reentry_changes:
            continue
        seen.add(ch)
        apply_canonical_reentry_scratch(scratch, ch)


def apply_canonical_exit_offstage_transition_scratch(
    acting_character: str,
    move: dict[str, Any],
    *,
    consequence_tags: set[str],
    scene_dict: dict[str, Any],
    scratch: PresenceAuthorityScratch,
    character_presence_constraints: dict[str, Any],
    should_skip_soft_exit_presence_removal: Callable[[str, dict[str, Any]], bool],
) -> None:
    actor = str(acting_character or "").strip()
    if not actor:
        return

    exit_tag = "exit" in consequence_tags
    detect = detect_exit_from_scene(move, scene_dict, actor)
    structured_exit = structured_presence_exit_for_character(move, actor)
    raw_exit = exit_tag or detect or structured_exit
    if not raw_exit:
        return

    if not structured_exit and authored_prose_suppresses_physical_departure(move):
        return

    hard = has_hard_scene_departure_evidence(move, scene_dict)
    lexical_exit = hard or structured_exit
    detect_soft = bool(detect and not lexical_exit)
    tag_only_soft = bool(exit_tag and not detect and not lexical_exit)
    soft_style = detect_soft or tag_only_soft

    must_remain = str(character_presence_constraints.get(actor, "") or "") == "must_remain"

    if must_remain:
        if soft_style:
            return
        if not structured_exit:
            return
        status_kind = "temporary_offstage"
    elif soft_style:
        if should_skip_soft_exit_presence_removal(actor, move):
            return
        status_kind = "temporary_offstage"
    else:
        status_kind = "departed"

    scratch.present_characters = [name for name in scratch.present_characters if name != actor]
    if actor not in scratch.absent_but_relevant:
        scratch.absent_but_relevant.append(actor)
    if actor not in scratch.offstage_characters:
        scratch.offstage_characters.append(actor)
    scratch.character_presence_status[actor] = status_kind


def ensure_at_least_one_present_character_scratch(
    scratch: PresenceAuthorityScratch,
    *,
    cast: list[str],
    e_active: Set[str],
    log: logging.Logger,
) -> None:
    if scratch.present_characters:
        return

    if not cast:
        return

    def eligible_for_focal(n: str) -> bool:
        return str(n).strip() not in e_active

    status_map = scratch.character_presence_status

    def is_departed(n: str) -> bool:
        return str(status_map.get(n, "") or "").strip() == "departed"

    def is_temporary_offstage_equivalent(n: str) -> bool:
        if is_departed(n):
            return False
        st = str(status_map.get(n, "") or "").strip()
        return st == "temporary_offstage" or st == ""

    off = list(scratch.offstage_characters)
    tier1 = [
        n
        for n in off
        if n in cast and is_temporary_offstage_equivalent(n) and eligible_for_focal(n)
    ]
    if tier1:
        apply_canonical_reentry_scratch(scratch, tier1[0])
        return
    tier2 = [
        n for n in off if n in cast and not is_departed(n) and eligible_for_focal(n)
    ]
    if tier2:
        apply_canonical_reentry_scratch(scratch, tier2[0])
        return
    tier3 = [n for n in cast if not is_departed(n) and eligible_for_focal(n)]
    if tier3:
        apply_canonical_reentry_scratch(scratch, tier3[0])
        return
    if not any(not is_departed(n) for n in cast):
        log.critical(
            "presence deadlock guard: present_characters empty and all cast are departed; "
            "skipping re-entry (no implicit resurrection)"
        )


def assert_presence_invariant_after_reconcile_scratch(
    scratch: PresenceAuthorityScratch,
    *,
    log: logging.Logger,
) -> None:
    present = set(scratch.present_characters)
    absent = set(scratch.absent_but_relevant)
    overlap = present & absent
    if not overlap:
        return
    message = (
        "continuity presence invariant failed after reconcile: "
        f"present ∩ absent_but_relevant = {overlap!r}"
    )
    if os.environ.get("RP_CONTINUITY_STRICT_INVARIANTS", "").strip() == "1":
        raise AssertionError(message)
    log.warning(message)


def align_exit_narrative_with_effective_presence(
    *,
    present_characters: list[str],
    acting_character: str,
    turn_consequences: dict[str, Any],
) -> None:
    """If exit was tagged but the actor remains on-stage, soften event-facing lines.

    Avoids authoritative contradiction: ``present_characters`` still includes the
    actor (e.g. ``must_remain`` / soft skip) while ``state_changes`` claimed full
    departure.
    """
    actor = str(acting_character or "").strip()
    if not actor:
        return
    raw_tags = turn_consequences.get("tags", [])
    if not isinstance(raw_tags, list):
        return
    if "exit" not in {str(t).strip().lower() for t in raw_tags}:
        return
    if actor not in present_characters:
        return

    old_change = f"{actor} left the immediate scene."
    new_change = (
        f"{actor} took departure-oriented action; "
        "on-stage presence is retained per scene constraints."
    )
    sc = turn_consequences.get("state_changes")
    if isinstance(sc, list):
        for i, item in enumerate(sc):
            if str(item).strip() == old_change:
                sc[i] = new_change
                break

    summ = turn_consequences.get("summary")
    if str(summ).strip() == old_change:
        turn_consequences["summary"] = new_change

    old_impl = "The remaining cast must proceed without the departed character."
    new_impl = (
        "On-stage roster unchanged; this character remains structurally present."
    )
    im = turn_consequences.get("actionable_implications")
    if isinstance(im, list):
        for i, item in enumerate(im):
            if str(item).strip() == old_impl:
                im[i] = new_impl
                break
