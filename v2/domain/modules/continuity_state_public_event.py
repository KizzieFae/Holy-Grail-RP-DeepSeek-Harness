"""Public (scene-visible) events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from continuity_state_datetime import _parse_datetime
from continuity_state_occurrence_evidence import OccurrenceEvidence, parse_occurrence_evidence


@dataclass
class PublicEvent:
    """A durable story development that characters can reference.

    Public events represent facts that occurred in the scene.
    They are separate from character interpretations of those facts.
    """

    event_id: str
    timestamp: datetime
    event_type: str  # 'dialogue', 'action', 'environment', 'revelation', 'decision'
    participants: list[str]
    summary: str
    turn_index: Optional[int] = None
    location: Optional[str] = None
    significance: str = "minor"  # 'minor', 'major', 'pivotal'
    observed_by: list[str] = field(default_factory=list)
    told_to: list[str] = field(default_factory=list)
    inferred_by: list[str] = field(default_factory=list)
    known_by: list[str] = field(default_factory=list)
    related_issue_ids: list[str] = field(default_factory=list)
    canon_impact: list[str] = field(default_factory=list)  # anchor_ids affected
    state_changes: list[str] = field(default_factory=list)
    actionable_implications: list[str] = field(default_factory=list)
    # Deterministic scene-grounding markers (category:key|k=v|...); PRD §5.8
    grounding_markers: list[str] = field(default_factory=list)
    # S4b per-character semantic annotations — separate from deterministic promotion-policy significance.
    revelation_significance_by_character: dict[str, dict] | None = None
    # Bounded semantic/causal evidence companion (Issue #51); optional for backward compatibility.
    occurrence_evidence: OccurrenceEvidence | None = None

    def knowledge_level_for(self, character_name: str) -> str | None:
        """Return how the character knows this event, if known.

        ``known_by`` is authoritative: characters not listed do not retrieve this
        event, even if legacy data lists them under ``observed_by`` only.
        """
        if character_name not in self.known_by:
            return None
        if character_name in self.participants:
            return "observed"
        if character_name in self.observed_by:
            return "observed"
        if character_name in self.told_to:
            return "told"
        if character_name in self.inferred_by:
            return "inferred"
        return "known"

    def to_dict(self) -> dict:
        """Serialize the event for persistence."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "turn_index": self.turn_index,
            "event_type": self.event_type,
            "participants": self.participants,
            "summary": self.summary,
            "location": self.location,
            "significance": self.significance,
            "observed_by": self.observed_by,
            "told_to": self.told_to,
            "inferred_by": self.inferred_by,
            "known_by": self.known_by,
            "related_issue_ids": self.related_issue_ids,
            "canon_impact": self.canon_impact,
            "state_changes": self.state_changes,
            "actionable_implications": self.actionable_implications,
            "grounding_markers": list(self.grounding_markers),
            "revelation_significance_by_character": (
                {
                    str(key): dict(value)
                    for key, value in self.revelation_significance_by_character.items()
                    if str(key).strip() and isinstance(value, dict)
                }
                if isinstance(self.revelation_significance_by_character, dict)
                else None
            ),
            "occurrence_evidence": (
                self.occurrence_evidence.to_dict()
                if self.occurrence_evidence is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PublicEvent":
        """Restore an event from persisted data."""
        return cls(
            event_id=str(data.get("event_id", "")),
            timestamp=_parse_datetime(data.get("timestamp")),
            turn_index=(
                int(data.get("turn_index"))
                if data.get("turn_index") is not None
                else None
            ),
            event_type=str(data.get("event_type", "action")),
            participants=[str(item) for item in data.get("participants", [])],
            summary=str(data.get("summary", "")),
            location=(str(data.get("location")) if data.get("location") else None),
            significance=str(data.get("significance", "minor")),
            observed_by=[str(item) for item in data.get("observed_by", [])],
            told_to=[str(item) for item in data.get("told_to", [])],
            inferred_by=[str(item) for item in data.get("inferred_by", [])],
            known_by=[str(item) for item in data.get("known_by", [])],
            related_issue_ids=[str(item) for item in data.get("related_issue_ids", [])],
            canon_impact=[str(item) for item in data.get("canon_impact", [])],
            state_changes=[str(item) for item in data.get("state_changes", [])],
            actionable_implications=[
                str(item) for item in data.get("actionable_implications", [])
            ],
            grounding_markers=[
                str(item)
                for item in data.get("grounding_markers", [])
                if str(item).strip()
            ],
            revelation_significance_by_character=_parse_revelation_significance_by_character(data),
            occurrence_evidence=parse_occurrence_evidence(
                data.get("occurrence_evidence")
                if isinstance(data.get("occurrence_evidence"), dict)
                else None
            ),
        )


def _parse_revelation_significance_by_character(data: dict) -> dict[str, dict] | None:
    raw = data.get("revelation_significance_by_character")
    if isinstance(raw, dict):
        parsed = {
            str(key): dict(value)
            for key, value in raw.items()
            if str(key).strip() and isinstance(value, dict)
        }
        return parsed or None
    legacy = data.get("revelation_significance_annotation")
    if isinstance(legacy, dict):
        subject = str(legacy.get("subject_character", "") or "").strip()
        if subject:
            return {subject: dict(legacy)}
    return None
