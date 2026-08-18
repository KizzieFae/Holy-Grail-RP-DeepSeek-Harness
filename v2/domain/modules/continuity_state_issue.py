"""Issue pressure domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from continuity_state_datetime import _parse_datetime


class IssueStatus(Enum):
    """Lifecycle states for issues and pressures."""

    ACTIVE = "active"
    ESCALATING = "escalating"
    STALLED = "stalled"
    RESOLVED = "resolved"
    DORMANT = "dormant"


@dataclass
class IssueState:
    """A pressure or tension in the scene with lifecycle tracking.

    Issues track what would count as escalation or resolution,
    allowing the continuity manager to monitor dramatic progress.
    """

    issue_id: str
    description: str
    participants: list[str]
    status: IssueStatus
    created_at: datetime
    escalation_signals: list[str] = field(default_factory=list)
    resolution_signals: list[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_turn_index: Optional[int] = None
    status_reason: str = ""
    matched_terms: list[str] = field(default_factory=list)
    related_event_ids: list[str] = field(default_factory=list)
    interaction_issue_ids: list[str] = field(default_factory=list)
    pressure_kind: str = ""
    blocked_what: str = ""
    blocked_characters: list[str] = field(default_factory=list)
    last_change: str = ""
    required_next_step: str = ""
    required_next_step_plateau_streak: int = 0
    required_next_step_plateau_last_norm: str = ""
    required_next_step_plateau_last_turn_index: int | None = None
    required_next_step_plateau_has_advanced: bool = False

    def to_dict(self) -> dict:
        """Serialize the issue for persistence."""
        return {
            "issue_id": self.issue_id,
            "description": self.description,
            "participants": self.participants,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "escalation_signals": self.escalation_signals,
            "resolution_signals": self.resolution_signals,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "last_turn_index": self.last_turn_index,
            "status_reason": self.status_reason,
            "matched_terms": self.matched_terms,
            "related_event_ids": self.related_event_ids,
            "interaction_issue_ids": self.interaction_issue_ids,
            "pressure_kind": self.pressure_kind,
            "blocked_what": self.blocked_what,
            "blocked_characters": self.blocked_characters,
            "last_change": self.last_change,
            "required_next_step": self.required_next_step,
            "required_next_step_plateau_streak": self.required_next_step_plateau_streak,
            "required_next_step_plateau_last_norm": self.required_next_step_plateau_last_norm,
            "required_next_step_plateau_last_turn_index": self.required_next_step_plateau_last_turn_index,
            "required_next_step_plateau_has_advanced": self.required_next_step_plateau_has_advanced,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IssueState":
        """Restore an issue from persisted data."""
        last_updated = data.get("last_updated")
        resolved_at = data.get("resolved_at")
        return cls(
            issue_id=str(data.get("issue_id", "")),
            description=str(data.get("description", "")),
            participants=[str(item) for item in data.get("participants", [])],
            status=IssueStatus(str(data.get("status", IssueStatus.ACTIVE.value))),
            created_at=_parse_datetime(data.get("created_at")),
            escalation_signals=[
                str(item) for item in data.get("escalation_signals", [])
            ],
            resolution_signals=[
                str(item) for item in data.get("resolution_signals", [])
            ],
            last_updated=(_parse_datetime(last_updated) if last_updated else None),
            resolved_at=(_parse_datetime(resolved_at) if resolved_at else None),
            last_turn_index=(
                int(data.get("last_turn_index"))
                if data.get("last_turn_index") is not None
                else None
            ),
            status_reason=str(data.get("status_reason", "") or ""),
            matched_terms=[str(item) for item in data.get("matched_terms", [])],
            related_event_ids=[str(item) for item in data.get("related_event_ids", [])],
            interaction_issue_ids=[
                str(item) for item in data.get("interaction_issue_ids", [])
            ],
            pressure_kind=str(data.get("pressure_kind", "") or ""),
            blocked_what=str(data.get("blocked_what", "") or ""),
            blocked_characters=[
                str(item) for item in data.get("blocked_characters", [])
            ],
            last_change=str(data.get("last_change", "") or ""),
            required_next_step=str(data.get("required_next_step", "") or ""),
            required_next_step_plateau_streak=int(
                data.get("required_next_step_plateau_streak", 0) or 0
            ),
            required_next_step_plateau_last_norm=str(
                data.get("required_next_step_plateau_last_norm", "") or ""
            ),
            required_next_step_plateau_last_turn_index=(
                int(data["required_next_step_plateau_last_turn_index"])
                if data.get("required_next_step_plateau_last_turn_index") is not None
                else None
            ),
            required_next_step_plateau_has_advanced=bool(
                data.get("required_next_step_plateau_has_advanced", False)
            ),
        )
