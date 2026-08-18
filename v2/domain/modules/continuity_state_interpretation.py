"""Per-character interpretations of events and situations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from continuity_state_datetime import _parse_datetime


@dataclass
class CharacterInterpretation:
    """How a specific character understands an event or situation.

    Characters keep separate interpretations to preserve viewpoint diversity
    and reduce voice convergence over long sessions.
    """

    interpretation_id: str
    character_name: str
    subject_type: str  # 'event', 'character', 'issue', 'relationship'
    subject_id: str  # what is being interpreted
    interpretation: str  # the character's private understanding
    emotional_reaction: str
    formed_at: datetime
    last_reinforced: Optional[datetime] = None
    confidence: str = "tentative"  # 'tentative', 'confident', 'certain'

    def to_dict(self) -> dict:
        """Serialize the interpretation for persistence."""
        return {
            "interpretation_id": self.interpretation_id,
            "character_name": self.character_name,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "interpretation": self.interpretation,
            "emotional_reaction": self.emotional_reaction,
            "formed_at": self.formed_at.isoformat(),
            "last_reinforced": (
                self.last_reinforced.isoformat() if self.last_reinforced else None
            ),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterInterpretation":
        """Restore an interpretation from persisted data."""
        last_reinforced = data.get("last_reinforced")
        return cls(
            interpretation_id=str(data.get("interpretation_id", "")),
            character_name=str(data.get("character_name", "")),
            subject_type=str(data.get("subject_type", "event")),
            subject_id=str(data.get("subject_id", "")),
            interpretation=str(data.get("interpretation", "")),
            emotional_reaction=str(
                data.get("emotional_reaction", "observing neutrally")
            ),
            formed_at=_parse_datetime(data.get("formed_at")),
            last_reinforced=(
                _parse_datetime(last_reinforced) if last_reinforced else None
            ),
            confidence=str(data.get("confidence", "tentative")),
        )
