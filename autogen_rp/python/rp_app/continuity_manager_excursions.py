"""Excursion lifecycle surface for ContinuityManager (mechanical extraction)."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from continuity_audit_origin import (
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
    manager_record_continuity_audit_event,
    manager_suppress_direct_excursion_bypass_audit,
)
from continuity_state import ExcursionRecord, ExcursionStatus

from continuity_manager_presence_surface import resync_presence_through_authority


def open_excursion(
    manager: Any,
    *,
    participant_character_ids: list[str],
    excursion_id: Optional[str] = None,
    opened_at_turn: Optional[int] = None,
) -> str:
    participants = [
        str(x).strip()
        for x in participant_character_ids
        if str(x or "").strip()
    ]
    if not participants:
        raise ValueError("open_excursion requires at least one participant")
    eid = (str(excursion_id).strip() if excursion_id else "") or str(uuid.uuid4())
    if eid in manager.excursions:
        raise ValueError(f"excursion_id already exists: {eid!r}")
    opened_turn = (
        int(opened_at_turn)
        if opened_at_turn is not None
        else int(manager.turn_counter)
    )
    manager.excursions[eid] = ExcursionRecord(
        excursion_id=eid,
        participant_character_ids=participants,
        status=ExcursionStatus.ACTIVE,
        opened_at_turn=opened_turn,
        closed_at_turn=None,
    )
    resync_presence_through_authority(manager)
    if not manager_suppress_direct_excursion_bypass_audit(manager):
        manager_record_continuity_audit_event(
            manager,
            CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
            opened_turn,
        )
    return eid


def update_excursion(
    manager: Any,
    excursion_id: str,
    *,
    participant_character_ids: Optional[list[str]] = None,
) -> None:
    eid = str(excursion_id or "").strip()
    rec = manager.excursions.get(eid)
    if rec is None:
        raise KeyError(excursion_id)
    if rec.status != ExcursionStatus.ACTIVE:
        raise ValueError("cannot update a closed excursion")
    if participant_character_ids is not None:
        participants = [
            str(x).strip()
            for x in participant_character_ids
            if str(x or "").strip()
        ]
        if not participants:
            raise ValueError(
                "participant_character_ids must be non-empty when provided"
            )
        prior_ids = frozenset(rec.participant_character_ids)
        rec.participant_character_ids = participants
        if frozenset(participants) != prior_ids:
            resync_presence_through_authority(manager)
    if not manager_suppress_direct_excursion_bypass_audit(manager):
        manager_record_continuity_audit_event(
            manager,
            CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
            int(manager.turn_counter),
        )


def close_excursion(
    manager: Any,
    excursion_id: str,
    *,
    closed_at_turn: Optional[int] = None,
) -> None:
    eid = str(excursion_id or "").strip()
    rec = manager.excursions.get(eid)
    if rec is None:
        raise KeyError(excursion_id)
    if rec.status == ExcursionStatus.CLOSED:
        return
    rec.status = ExcursionStatus.CLOSED
    rec.closed_at_turn = (
        int(closed_at_turn)
        if closed_at_turn is not None
        else int(manager.turn_counter)
    )
    resync_presence_through_authority(manager)
    closed_idx = int(rec.closed_at_turn or manager.turn_counter)
    if not manager_suppress_direct_excursion_bypass_audit(manager):
        manager_record_continuity_audit_event(
            manager,
            CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
            closed_idx,
        )


def active_excursion_character_ids(manager: Any) -> set[str]:
    out: set[str] = set()
    for rec in manager.excursions.values():
        if rec.status != ExcursionStatus.ACTIVE:
            continue
        for pid in rec.participant_character_ids:
            n = str(pid).strip()
            if n:
                out.add(n)
    return out
