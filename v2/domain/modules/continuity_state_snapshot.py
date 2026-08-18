"""Aggregate continuity snapshot for persistence and prompts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from continuity_state_canon import CanonAnchor
from continuity_state_interpretation import CharacterInterpretation
from continuity_state_issue import IssueState
from continuity_state_public_event import PublicEvent
from continuity_state_scene import SceneState
from continuity_state_summary import SummaryBlock


@dataclass
class ContinuitySnapshot:
    """A complete snapshot of durable story state at a point in time.

    Used for persistence and for assembling layered prompts.
    """

    scene_state: SceneState
    active_issues: list[IssueState]
    recent_public_events: list[PublicEvent]
    character_interpretations: dict[str, list[CharacterInterpretation]]  # by character
    canon_anchors: list[CanonAnchor]
    summary_blocks: list[SummaryBlock]
    snapshot_at: datetime

    def to_dict(self) -> dict:
        """Serialize a snapshot for debugging or persistence."""
        return {
            "scene_state": self.scene_state.to_dict(),
            "active_issues": [issue.to_dict() for issue in self.active_issues],
            "recent_public_events": [
                event.to_dict() for event in self.recent_public_events
            ],
            "character_interpretations": {
                name: [item.to_dict() for item in items]
                for name, items in self.character_interpretations.items()
            },
            "canon_anchors": [anchor.to_dict() for anchor in self.canon_anchors],
            "summary_blocks": [summary.to_dict() for summary in self.summary_blocks],
            "snapshot_at": self.snapshot_at.isoformat(),
        }
