"""Continuity engine for RP app.

Converts transient dialogue and structured moves into durable narrative state.
Manages scene state, issues/pressures, public events, and per-character interpretations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: object | None) -> datetime:
    if value is None or not str(value).strip():
        return _utc_now()
    parsed = datetime.fromisoformat(str(value))
    return (
        parsed.astimezone(timezone.utc)
        if parsed.tzinfo is not None
        else parsed.replace(tzinfo=timezone.utc)
    )


class IssueStatus(Enum):
    """Lifecycle states for issues and pressures."""

    ACTIVE = "active"
    ESCALATING = "escalating"
    STALLED = "stalled"
    RESOLVED = "resolved"
    DORMANT = "dormant"


class ScenePhase(Enum):
    """Phases of scene progression."""

    OPENING = "opening"
    RISING = "rising"
    CLIMAX = "climax"
    FALLING = "falling"
    RESOLUTION = "resolution"


class ConsequenceCategory(Enum):
    """Semantic consequence types detected from structured move analysis.

    These categories capture the dramatic function of a turn rather than
    its surface phrasing, enabling robust consequence detection across
    varied character voices and scene dynamics.
    """

    # Authority dynamics
    AUTHORITY_ASSERTED = "authority_asserted"
    AUTHORITY_CHALLENGED = "authority_challenged"

    # Agreement/alignment
    REFUSAL = "refusal"
    AGREEMENT = "agreement"
    COMMITMENT = "commitment"

    # Territory/presence
    TERRITORIAL_CLAIM = "territorial_claim"
    TERRITORIAL_DENIAL = "territorial_denial"
    ARRIVAL = "arrival"
    EXIT = "exit"
    REPOSITIONING = "repositioning"

    # Access/control
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Scene mediation
    MEDIATION_ATTEMPTED = "mediation_attempted"
    INTERCEPTION = "interception"

    # Tension trajectory
    ESCALATION = "escalation"
    DEESCALATION = "deescalation"

    # Information state
    REVELATION = "revelation"
    CONCEALMENT = "concealment"

    # Future pressure
    DECISION_MADE = "decision_made"
    PLAN_COMMITTED = "plan_committed"
    DEPENDENCY_ADVANCED = "dependency_advanced"


@dataclass(frozen=True)
class DetectedConsequence:
    """A consequence detected from turn analysis.

    Captures what category was detected, confidence level, which fields
    contributed to the detection, and the specific excerpt that triggered it.
    """

    category: ConsequenceCategory
    confidence: str  # 'strong', 'moderate', 'weak'
    source_fields: list[str]  # Which input fields contributed
    excerpt: str  # Specific text that triggered detection (truncated)


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
        )


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

    def knowledge_level_for(self, character_name: str) -> str | None:
        """Return how the character knows this event, if known."""
        if character_name in self.observed_by or character_name in self.participants:
            return "observed"
        if character_name in self.told_to:
            return "told"
        if character_name in self.inferred_by:
            return "inferred"
        if character_name in self.known_by:
            return "known"
        return None

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
        )


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


@dataclass
class SceneState:
    """The current state of the scene including setting, participants, and active pressures.

    Scene state is shared context that all characters can observe,
    distinct from their private interpretations.
    """

    # Setting
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    environment_description: Optional[str] = None
    scene_template_id: Optional[str] = None
    scene_premise: str = ""
    role_assignments: dict[str, str] = field(default_factory=dict)
    character_presence_constraints: dict[str, str] = field(default_factory=dict)
    character_authority_labels: dict[str, str] = field(default_factory=dict)

    # Participants
    present_characters: list[str] = field(default_factory=list)
    absent_but_relevant: list[str] = field(default_factory=list)
    # Still in cast / present_characters but not in the immediate shared space (hallway, garage, etc.)
    offstage_characters: list[str] = field(default_factory=list)

    # Scene progression
    phase: ScenePhase = field(default=ScenePhase.OPENING)
    opening_description: str = ""
    recent_delta: str = ""  # what just changed in the scene

    # Active state references (IDs into continuity stores)
    active_issue_ids: list[str] = field(default_factory=list)
    recent_event_ids: list[str] = field(default_factory=list)

    # Environment tracking
    current_tension_level: str = "low"  # 'low', 'moderate', 'high', 'extreme'
    recent_environment_events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the scene state for persistence."""
        return {
            "location": self.location,
            "time_of_day": self.time_of_day,
            "environment_description": self.environment_description,
            "scene_template_id": self.scene_template_id,
            "scene_premise": self.scene_premise,
            "role_assignments": self.role_assignments,
            "character_presence_constraints": self.character_presence_constraints,
            "character_authority_labels": self.character_authority_labels,
            "present_characters": self.present_characters,
            "absent_but_relevant": self.absent_but_relevant,
            "offstage_characters": self.offstage_characters,
            "phase": self.phase.value,
            "opening_description": self.opening_description,
            "recent_delta": self.recent_delta,
            "active_issue_ids": self.active_issue_ids,
            "recent_event_ids": self.recent_event_ids,
            "current_tension_level": self.current_tension_level,
            "recent_environment_events": self.recent_environment_events,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SceneState":
        """Restore scene state from persisted data."""
        return cls(
            location=(str(data.get("location")) if data.get("location") else None),
            time_of_day=(
                str(data.get("time_of_day")) if data.get("time_of_day") else None
            ),
            environment_description=(
                str(data.get("environment_description"))
                if data.get("environment_description")
                else None
            ),
            scene_template_id=(
                str(data.get("scene_template_id"))
                if data.get("scene_template_id")
                else None
            ),
            scene_premise=str(data.get("scene_premise", "") or ""),
            role_assignments=(
                {
                    str(key): str(value)
                    for key, value in data.get("role_assignments", {}).items()
                }
                if isinstance(data.get("role_assignments", {}), dict)
                else {}
            ),
            character_presence_constraints=(
                {
                    str(key): str(value)
                    for key, value in data.get(
                        "character_presence_constraints", {}
                    ).items()
                }
                if isinstance(data.get("character_presence_constraints", {}), dict)
                else {}
            ),
            character_authority_labels=(
                {
                    str(key): str(value)
                    for key, value in data.get("character_authority_labels", {}).items()
                }
                if isinstance(data.get("character_authority_labels", {}), dict)
                else {}
            ),
            present_characters=[
                str(item) for item in data.get("present_characters", [])
            ],
            absent_but_relevant=[
                str(item) for item in data.get("absent_but_relevant", [])
            ],
            offstage_characters=[
                str(item) for item in data.get("offstage_characters", [])
            ],
            phase=ScenePhase(str(data.get("phase", ScenePhase.OPENING.value))),
            opening_description=str(data.get("opening_description", "")),
            recent_delta=str(data.get("recent_delta", "")),
            active_issue_ids=[str(item) for item in data.get("active_issue_ids", [])],
            recent_event_ids=[str(item) for item in data.get("recent_event_ids", [])],
            current_tension_level=str(data.get("current_tension_level", "low")),
            recent_environment_events=[
                str(item) for item in data.get("recent_environment_events", [])
            ],
        )


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


def create_fresh_scene_state(
    location: Optional[str] = None,
    opening_description: str = "",
    present_characters: Optional[list[str]] = None,
) -> SceneState:
    """Create initial scene state for a new scene."""
    return SceneState(
        location=location,
        opening_description=opening_description,
        present_characters=present_characters or [],
        phase=ScenePhase.OPENING,
        current_tension_level="low",
    )
