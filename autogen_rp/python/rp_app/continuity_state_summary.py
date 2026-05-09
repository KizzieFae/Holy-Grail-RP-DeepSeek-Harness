"""Rolling summary blocks for continuity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from continuity_state_datetime import _parse_datetime


@dataclass
class SummaryBlock:
    summary_id: str
    turn_range_start: int
    turn_range_end: int
    generated_at: datetime
    location: Optional[str] = None
    scene_phase: str = "opening"
    tension_level: str = "low"
    continuity_facts: list[str] = field(default_factory=list)
    source_event_ids: list[str] = field(default_factory=list)
    key_events: list[str] = field(default_factory=list)
    issue_updates: list[dict[str, str]] = field(default_factory=list)
    interpretation_shifts: list[dict[str, object]] = field(default_factory=list)
    participant_names: list[str] = field(default_factory=list)
    dominant_issue_ids: list[str] = field(default_factory=list)
    significance_counts: dict[str, int] = field(default_factory=dict)
    impact_score: int = 0

    def to_dict(self) -> dict:
        return {
            "summary_id": self.summary_id,
            "turn_range_start": self.turn_range_start,
            "turn_range_end": self.turn_range_end,
            "generated_at": self.generated_at.isoformat(),
            "location": self.location,
            "scene_phase": self.scene_phase,
            "tension_level": self.tension_level,
            "continuity_facts": self.continuity_facts,
            "source_event_ids": self.source_event_ids,
            "key_events": self.key_events,
            "issue_updates": self.issue_updates,
            "interpretation_shifts": self.interpretation_shifts,
            "participant_names": self.participant_names,
            "dominant_issue_ids": self.dominant_issue_ids,
            "significance_counts": self.significance_counts,
            "impact_score": self.impact_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryBlock":
        return cls(
            summary_id=str(data.get("summary_id", "")),
            turn_range_start=int(data.get("turn_range_start", 0)),
            turn_range_end=int(data.get("turn_range_end", 0)),
            generated_at=_parse_datetime(data.get("generated_at")),
            location=(str(data.get("location")) if data.get("location") else None),
            scene_phase=str(data.get("scene_phase", "opening")),
            tension_level=str(data.get("tension_level", "low")),
            continuity_facts=[str(item) for item in data.get("continuity_facts", [])],
            source_event_ids=[str(item) for item in data.get("source_event_ids", [])],
            key_events=[str(item) for item in data.get("key_events", [])],
            issue_updates=[
                {
                    str(key): str(value) if value is not None else ""
                    for key, value in item.items()
                }
                for item in data.get("issue_updates", [])
                if isinstance(item, dict)
            ],
            interpretation_shifts=[
                {
                    str(key): (
                        [str(entry) for entry in value]
                        if isinstance(value, list)
                        else str(value) if value is not None else ""
                    )
                    for key, value in item.items()
                }
                for item in data.get("interpretation_shifts", [])
                if isinstance(item, dict)
            ],
            participant_names=[str(item) for item in data.get("participant_names", [])],
            dominant_issue_ids=[
                str(item) for item in data.get("dominant_issue_ids", [])
            ],
            significance_counts=(
                {
                    str(key): int(value)
                    for key, value in data.get("significance_counts", {}).items()
                }
                if isinstance(data.get("significance_counts", {}), dict)
                else {}
            ),
            impact_score=int(data.get("impact_score", 0)),
        )
