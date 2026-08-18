"""Canon anchor facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from continuity_state_datetime import _parse_datetime


@dataclass
class CanonAnchor:
    """A protected truth that should resist casual drift.

    Canon anchors are stable facts about characters, world, or relationships
    that should not be altered by temporary scene dynamics.
    """

    anchor_id: str
    category: str  # 'character_trait', 'world_fact', 'relationship', 'event'
    subject: str  # who/what this anchor applies to
    statement: str  # the protected truth
    source: str  # how this was established
    established_at: datetime
    protected: bool = True  # if True, requires explicit override to change

    def to_dict(self) -> dict:
        """Serialize the anchor for persistence."""
        return {
            "anchor_id": self.anchor_id,
            "category": self.category,
            "subject": self.subject,
            "statement": self.statement,
            "source": self.source,
            "established_at": self.established_at.isoformat(),
            "protected": self.protected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CanonAnchor":
        """Restore an anchor from persisted data."""
        return cls(
            anchor_id=str(data.get("anchor_id", "")),
            category=str(data.get("category", "")),
            subject=str(data.get("subject", "")),
            statement=str(data.get("statement", "")),
            source=str(data.get("source", "")),
            established_at=_parse_datetime(data.get("established_at")),
            protected=bool(data.get("protected", True)),
        )
