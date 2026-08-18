"""Excursion thread types (Issue #77)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExcursionStatus(str, Enum):
    """Excursion lifecycle (Issue #77 excursion authority scaffolding)."""

    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class ExcursionRecord:
    """Canonical excursion thread (Issue #77); does not duplicate focal presence."""

    excursion_id: str
    participant_character_ids: list[str]
    status: ExcursionStatus
    opened_at_turn: int
    closed_at_turn: Optional[int] = None
    """Set when Slice C reintegration merge succeeds; enforces idempotency per commit id."""
    reintegration_commit_id_applied: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "excursion_id": self.excursion_id,
            "participant_character_ids": list(self.participant_character_ids),
            "status": self.status.value,
            "opened_at_turn": int(self.opened_at_turn),
            "closed_at_turn": (
                int(self.closed_at_turn)
                if self.closed_at_turn is not None
                else None
            ),
            "reintegration_commit_id_applied": (
                str(self.reintegration_commit_id_applied)
                if self.reintegration_commit_id_applied is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExcursionRecord":
        st = str(data.get("status", "") or "").strip().lower()
        status = (
            ExcursionStatus.ACTIVE
            if st == ExcursionStatus.ACTIVE.value
            else ExcursionStatus.CLOSED
        )
        raw_closed = data.get("closed_at_turn")
        closed: Optional[int]
        if raw_closed is None or raw_closed == "":
            closed = None
        else:
            closed = int(raw_closed)
        raw_rc = data.get("reintegration_commit_id_applied")
        rc_applied: Optional[str]
        if raw_rc is None or raw_rc == "":
            rc_applied = None
        else:
            rc_applied = str(raw_rc).strip() or None
        return cls(
            excursion_id=str(data.get("excursion_id", "") or ""),
            participant_character_ids=[
                str(x).strip()
                for x in (data.get("participant_character_ids") or [])
                if str(x or "").strip()
            ],
            status=status,
            opened_at_turn=int(data.get("opened_at_turn", 0)),
            closed_at_turn=closed,
            reintegration_commit_id_applied=rc_applied,
        )
