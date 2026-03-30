"""Continuity manager for RP app.

Runs between turns to convert transient dialogue into durable narrative state.
Responsible for: promoting moves to events, updating issue state,
updating scene state, managing character interpretations, enforcing knowledge boundaries.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from scene_exit_detection import (
    detect_exit_from_scene,
    has_hard_scene_departure_evidence,
    has_scene_reentry_evidence,
)

from continuity_issue_helpers import (
    event_tokens,
    find_matching_issue,
    get_active_issues as get_active_issues_helper,
    get_resolved_issue_descriptions as get_resolved_issue_descriptions_helper,
    issue_tokens,
    link_issue_interactions,
    maybe_create_issue,
    merge_issue_terms,
    retrieve_public_events as retrieve_public_events_helper,
    retrieve_summary_blocks as retrieve_summary_blocks_helper,
    turn_tokens,
    update_issues,
)
from continuity_summary_helpers import (
    build_summary_block as build_summary_block_helper,
    collect_interpretation_shifts as collect_interpretation_shifts_helper,
    collect_issue_updates as collect_issue_updates_helper,
    get_summary_blocks as get_summary_blocks_helper,
    maybe_generate_summary_block as maybe_generate_summary_block_helper,
)
from continuity_knowledge_helpers import (
    mentioned_participants as mentioned_participants_helper,
    propagate_knowledge_from_turn as propagate_knowledge_from_turn_helper,
    share_event_knowledge as share_event_knowledge_helper,
    update_interpretations as update_interpretations_helper,
)
from continuity_resolved_outcomes import (
    apply_registered_resolved_outcome_updates,
    build_housing_call_state_change,
    build_location_entry_state_change,
    build_sleeping_surface_state_change,
    build_suppressant_formulation_state_change,
)
from continuity_scene_helpers import (
    build_character_context,
    build_orchestration_context,
    build_snapshot,
    initialize_scene_state,
    restore_manager_state,
    serialize_manager_state,
)
from scene_grounding import compute_grounding_markers, grounding_markers_event_summary

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    ConsequenceCategory,
    ContinuitySnapshot,
    DetectedConsequence,
    IssueState,
    IssueStatus,
    PublicEvent,
    ScenePhase,
    SceneState,
    SummaryBlock,
)

from continuity_consequence_classifier import ConsequenceClassifier

MAX_ACTIVE_ISSUES = 3
DEFAULT_SUMMARY_INTERVAL = 12
DEFAULT_RECENT_EVENT_WINDOW = 8
DEFAULT_SUMMARY_PROMPT_LIMIT = 3
DEFAULT_ACTIVE_ISSUE_LIMIT = 4
DEFAULT_RECENT_EVENT_PROMPT_LIMIT = 6
ISSUE_STALL_TURN_THRESHOLD = 3
KNOWLEDGE_SHARE_MIN_OVERLAP = 2
ISSUE_TOKEN_STOPWORDS = {
    "about",
    "after",
    "because",
    "before",
    "could",
    "did",
    "from",
    "have",
    "into",
    "just",
    "much",
    "should",
    "that",
    "their",
    "them",
    "they",
    "this",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}

logger = logging.getLogger(__name__)


class ContinuityManager:
    """Manages conversion of transient scene activity into durable continuity.

    The continuity manager runs between turns to:
    1. Assess significance of recent dialogue/structured moves
    2. Promote significant developments to public event objects
    3. Update issue/pressure lifecycles
    4. Update scene state (location, tension, phase)
    5. Update per-character interpretation memories
    6. Enforce knowledge boundaries
    """

    def __init__(
        self,
        summary_interval: int = DEFAULT_SUMMARY_INTERVAL,
        recent_event_window: int = DEFAULT_RECENT_EVENT_WINDOW,
    ) -> None:
        """Initialize the continuity manager with empty stores."""
        self.scene_state: Optional[SceneState] = None
        self.issues: dict[str, IssueState] = {}
        self.public_events: list[PublicEvent] = []
        self.resolved_outcomes: list[Any] = []
        self.interpretations: dict[str, list[CharacterInterpretation]] = {}
        self.canon_anchors: list[CanonAnchor] = []
        self.summary_blocks: list[SummaryBlock] = []
        self.event_counter: int = 0
        self.summary_counter: int = 0
        self.turn_counter: int = 0
        self.last_summarized_event_index: int = 0
        self.summary_interval: int = max(1, summary_interval)
        self.recent_event_window: int = max(1, recent_event_window)
        self._consequence_classifier = ConsequenceClassifier()
        self.turn_metadata_by_index: dict[int, dict[str, Any]] = (
            {}
        )  # turn_index -> full consequences

    def _normalize_timestamp(self, timestamp: Optional[datetime] = None) -> datetime:
        if timestamp is None:
            return datetime.now(timezone.utc)
        return (
            timestamp.astimezone(timezone.utc)
            if timestamp.tzinfo is not None
            else timestamp.replace(tzinfo=timezone.utc)
        )

    def _classify_turn_consequences(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify turn consequences using structured pattern detection.

        Uses ConsequenceClassifier to detect semantic categories from
        intent (goal/tactic) + behavior (action/dialogue) patterns.
        Multi-label: accumulates all applicable categories.
        """
        # Use new consequence classifier
        scene_state = self.scene_state.to_dict() if self.scene_state is not None else None
        detected = self._consequence_classifier.classify_turn(
            acting_character, move, director_decision, scene_state
        )

        # Map detected categories to state_changes and actionable_implications
        state_changes: list[str] = []
        actionable_implications: list[str] = []
        tags: set[str] = set()

        # Category to state change mapping
        category_state_change = {
            ConsequenceCategory.AUTHORITY_ASSERTED: f"{acting_character} asserted authority or control.",
            ConsequenceCategory.AUTHORITY_CHALLENGED: f"{acting_character} challenged existing authority.",
            ConsequenceCategory.TERRITORIAL_CLAIM: f"{acting_character} claimed presence in contested space.",
            ConsequenceCategory.TERRITORIAL_DENIAL: f"{acting_character} denied another's right to remain.",
            ConsequenceCategory.MEDIATION_ATTEMPTED: f"{acting_character} attempted to mediate the conflict.",
            ConsequenceCategory.INTERCEPTION: f"{acting_character} rejected mediation and reasserted control.",
            ConsequenceCategory.ARRIVAL: f"{acting_character} arrived in the scene.",
            ConsequenceCategory.EXIT: f"{acting_character} left the immediate scene.",
            ConsequenceCategory.REPOSITIONING: f"{acting_character} repositioned physically in contested space.",
            ConsequenceCategory.REFUSAL: f"{acting_character} refused the current demand, request, or proposed course of action.",
            ConsequenceCategory.AGREEMENT: f"{acting_character} agreed or accepted a proposal.",
            ConsequenceCategory.COMMITMENT: f"{acting_character} committed to a future action.",
            ConsequenceCategory.ACCESS_GRANTED: f"{acting_character} granted access or permission.",
            ConsequenceCategory.ACCESS_DENIED: f"{acting_character} denied access or blocked entry.",
            ConsequenceCategory.REVELATION: f"{acting_character} revealed significant information.",
            ConsequenceCategory.CONCEALMENT: f"{acting_character} concealed or hid information.",
            ConsequenceCategory.PHYSICAL_STATE_SET: f"{acting_character} established or changed a concrete physical detail in the scene.",
            ConsequenceCategory.MEDICAL_STATE_SET: f"{acting_character} applied or confirmed a hands-on medical or first-aid detail.",
        }

        # Category to actionable implication mapping
        category_implication = {
            ConsequenceCategory.AUTHORITY_ASSERTED: "Authority dynamics are now contested and must be resolved.",
            ConsequenceCategory.AUTHORITY_CHALLENGED: "The challenged party must respond or cede control.",
            ConsequenceCategory.TERRITORIAL_CLAIM: "Territorial boundaries are now disputed.",
            ConsequenceCategory.TERRITORIAL_DENIAL: "The targeted character must exit, challenge back, or submit.",
            ConsequenceCategory.MEDIATION_ATTEMPTED: "The mediator temporarily controls the interaction flow.",
            ConsequenceCategory.INTERCEPTION: "Mediation failed; direct confrontation is resuming.",
            ConsequenceCategory.ARRIVAL: "Others must account for the new arrival's presence.",
            ConsequenceCategory.EXIT: "The remaining cast must proceed without the departed character.",
            ConsequenceCategory.ESCALATION: "Tension is increasing; pressure mounts on all parties.",
            ConsequenceCategory.DEESCALATION: "Tension is reducing; opportunity for resolution or rest.",
            ConsequenceCategory.REFUSAL: "The cast must respond to the refusal or choose a different course.",
            ConsequenceCategory.AGREEMENT: "The agreed course can now move from debate to execution.",
            ConsequenceCategory.COMMITMENT: "The committed action creates future obligation and pressure.",
            ConsequenceCategory.ACCESS_GRANTED: "The granted access can be used immediately by the recipient.",
            ConsequenceCategory.ACCESS_DENIED: "The denied party must find leverage or alternate route.",
            ConsequenceCategory.REVELATION: "Others can now act on the newly revealed information.",
            ConsequenceCategory.PHYSICAL_STATE_SET: "A physical object or placement detail is now part of shared scene reality.",
            ConsequenceCategory.MEDICAL_STATE_SET: "A medical or stabilization detail is now part of shared scene reality.",
        }

        for consequence in detected:
            tags.add(consequence.category.value)

            state_change = category_state_change.get(consequence.category)
            if state_change and state_change not in state_changes:
                state_changes.append(state_change)

            implication = category_implication.get(consequence.category)
            if implication and implication not in actionable_implications:
                actionable_implications.append(implication)

        sleeping_assignment_state_change = build_sleeping_surface_state_change(
            move, self.scene_state
        )
        if (
            sleeping_assignment_state_change
            and sleeping_assignment_state_change not in state_changes
        ):
            state_changes.append(sleeping_assignment_state_change)
            actionable_implications.append(
                "Sleeping arrangement state may now be ready for continuity settlement."
            )
        housing_call_state_change = build_housing_call_state_change(move, self.scene_state)
        if housing_call_state_change and housing_call_state_change not in state_changes:
            state_changes.append(housing_call_state_change)
            actionable_implications.append(
                "Housing call outcome may now be ready for continuity settlement."
            )
        suppressant_formulation_state_change = (
            build_suppressant_formulation_state_change(move, self.scene_state)
        )
        if (
            suppressant_formulation_state_change
            and suppressant_formulation_state_change not in state_changes
        ):
            state_changes.append(suppressant_formulation_state_change)
            actionable_implications.append(
                "Suppressant formulation state may now be ready for continuity settlement."
            )
        location_entry_state_change = build_location_entry_state_change(
            move, self.scene_state
        )
        if location_entry_state_change and location_entry_state_change not in state_changes:
            state_changes.append(location_entry_state_change)
            actionable_implications.append(
                "Location entry permission may now be ready for continuity settlement."
            )

        # Extract additional fields from move for significance calculation
        motivation = move.get("motivation", {})
        if not isinstance(motivation, dict):
            motivation = {}
        risk_level = str(motivation.get("risk_level", "medium") or "medium").lower()
        dialogue = str(move.get("dialogue", "") or "").lower()
        action = str(move.get("action", "") or "").lower()
        environment_event = str(
            director_decision.get("environment_event", "") or ""
        ).lower()
        tension_shift = str(director_decision.get("tension_shift", "") or "").lower()

        # Determine event type from detected categories
        event_type = self._determine_event_type(
            detected, dialogue, action, environment_event
        )

        # Determine significance
        significance = self._determine_significance(
            detected, risk_level, tension_shift, dialogue, environment_event
        )

        # Build summary
        if state_changes:
            summary = state_changes[0]
        elif action and dialogue:
            summary = f'{acting_character} {action}; said: "{dialogue}"'
        elif action:
            summary = f"{acting_character} {action}"
        elif dialogue:
            summary = f'{acting_character} said: "{dialogue}"'
        elif environment_event:
            summary = environment_event
        else:
            summary = f"{acting_character} took action"

        # Determine if event should be created
        # Only create events for durable changes or significant scene shifts
        # Pure dialogue without consequences or state changes should not create events
        has_durable_change = bool(detected or state_changes or actionable_implications)
        has_scene_shift = bool(
            environment_event
            or risk_level in ["high", "extreme"]
            or tension_shift in ["escalate", "unsettle"]
        )
        base_promotion = has_durable_change or has_scene_shift

        grounding_markers = compute_grounding_markers(
            acting_character, move, detected
        )
        should_create_event = base_promotion or bool(grounding_markers)

        # Markers must persist on a PublicEvent; when they are the only promotion driver,
        # use a compact deterministic summary and a stable event_type (PRD §5.8).
        if should_create_event and not base_promotion and grounding_markers:
            summary = grounding_markers_event_summary(grounding_markers)
            event_type = "state"
            significance = "minor"

        return {
            "should_create_event": should_create_event,
            "event_type": event_type,
            "summary": summary,
            "significance": significance,
            "state_changes": state_changes,
            "actionable_implications": actionable_implications,
            "tags": sorted(tags),
            "consequences": [c.category.value for c in detected],  # For audit/debug
            "grounding_markers": grounding_markers,
        }

    def _determine_event_type(
        self,
        detected: list,
        dialogue: str,
        action: str,
        environment_event: str,
    ) -> str:
        """Determine event type from detected consequence categories."""
        categories = {c.category for c in detected}

        if ConsequenceCategory.PHYSICAL_STATE_SET in categories:
            return "state"
        if ConsequenceCategory.MEDICAL_STATE_SET in categories:
            return "state"
        if ConsequenceCategory.REVELATION in categories:
            return "revelation"
        if {
            ConsequenceCategory.REFUSAL,
            ConsequenceCategory.AGREEMENT,
            ConsequenceCategory.COMMITMENT,
            ConsequenceCategory.ACCESS_GRANTED,
            ConsequenceCategory.ACCESS_DENIED,
        }.intersection(categories):
            return "decision"
        if environment_event and not (dialogue or action or categories):
            return "environment"
        if dialogue and not categories:
            return "dialogue"
        return "action"

    def _determine_significance(
        self,
        detected: list,
        risk_level: str,
        tension_shift: str,
        dialogue: str,
        environment_event: str,
    ) -> str:
        """Determine event significance from consequences and metadata."""
        categories = {c.category for c in detected}

        # Pivotal: key consequence categories
        pivotal_categories = {
            ConsequenceCategory.AUTHORITY_ASSERTED,
            ConsequenceCategory.AUTHORITY_CHALLENGED,
            ConsequenceCategory.TERRITORIAL_CLAIM,
            ConsequenceCategory.TERRITORIAL_DENIAL,
            ConsequenceCategory.REVELATION,
            ConsequenceCategory.COMMITMENT,
        }
        if categories.intersection(pivotal_categories):
            return "pivotal"

        # Major: tension shift, environment, or high risk
        if risk_level in ["high", "extreme"] or tension_shift in [
            "escalate",
            "unsettle",
        ]:
            return "major"
        if dialogue and any(marker in dialogue for marker in ["?", "you", "why"]):
            return "major"
        if environment_event or categories:
            return "major"

        return "minor"

    def _upsert_canon_anchor(self, anchor: CanonAnchor) -> None:
        """Insert or replace a canon anchor by ID."""
        for index, existing in enumerate(self.canon_anchors):
            if existing.anchor_id == anchor.anchor_id:
                self.canon_anchors[index] = anchor
                return
        self.canon_anchors.append(anchor)

    def seed_character_canon_anchors(self, character_states: dict[str, Any]) -> None:
        """Seed protected canon anchors from current character state data."""
        timestamp = datetime.now(timezone.utc)
        for name, state in character_states.items():
            core_goals = list(getattr(state, "core_goals", []) or [])
            long_term_goal = str(getattr(state, "long_term_goal", "") or "").strip()
            if not core_goals and long_term_goal:
                core_goals = [long_term_goal]
            if core_goals:
                self._upsert_canon_anchor(
                    CanonAnchor(
                        anchor_id=f"canon_{name.lower()}_goals",
                        category="character_trait",
                        subject=name,
                        statement=f"{name} consistently pursues: {', '.join(core_goals)}.",
                        source="character_state.core_goals",
                        established_at=timestamp,
                    )
                )

            voice_profile = getattr(state, "voice_profile", {}) or {}
            speech_fingerprint = getattr(state, "speech_fingerprint", {}) or {}
            voice_parts: list[str] = []
            if voice_profile:
                voice_parts.append(
                    "voice profile: "
                    + ", ".join(
                        f"{key}={value}" for key, value in voice_profile.items()
                    )
                )
            if speech_fingerprint:
                voice_parts.append(
                    "speech fingerprint: "
                    + ", ".join(
                        f"{key}={value}" for key, value in speech_fingerprint.items()
                    )
                )
            if voice_parts:
                self._upsert_canon_anchor(
                    CanonAnchor(
                        anchor_id=f"canon_{name.lower()}_voice",
                        category="character_voice",
                        subject=name,
                        statement=f"{name}'s expression remains distinct: {'; '.join(voice_parts)}.",
                        source="character_state.voice_profile",
                        established_at=timestamp,
                    )
                )

            reaction_profile = getattr(state, "reaction_profile", {}) or {}
            if reaction_profile:
                self._upsert_canon_anchor(
                    CanonAnchor(
                        anchor_id=f"canon_{name.lower()}_reaction",
                        category="character_trait",
                        subject=name,
                        statement=(
                            f"{name} tends to react in consistent ways: "
                            + ", ".join(
                                f"{key}={value}"
                                for key, value in reaction_profile.items()
                            )
                            + "."
                        ),
                        source="character_state.reaction_profile",
                        established_at=timestamp,
                    )
                )

    def get_relevant_canon_anchors(
        self,
        character_name: str,
        participants: Optional[list[str]] = None,
        limit: int = 6,
    ) -> list[CanonAnchor]:
        """Return canon anchors most relevant to the named character in this scene."""
        participant_set = set(
            participants
            or (self.scene_state.present_characters if self.scene_state else [])
        )
        relevant: list[CanonAnchor] = []
        for anchor in self.canon_anchors:
            if anchor.subject == character_name:
                relevant.append(anchor)
                continue
            if anchor.category == "world_fact":
                relevant.append(anchor)
                continue
            if (
                participant_set
                and anchor.subject in participant_set
                and anchor.category == "relationship"
            ):
                relevant.append(anchor)
        return relevant[:limit]

    def get_scene_canon_anchors(self, limit: int = 10) -> list[CanonAnchor]:
        """Return canon anchors broadly relevant to the current scene."""
        participants = set(
            self.scene_state.present_characters if self.scene_state else []
        )
        anchors = [
            anchor
            for anchor in self.canon_anchors
            if anchor.subject in participants or anchor.category == "world_fact"
        ]
        return anchors[:limit]

    def get_active_issues(
        self,
        limit: int = DEFAULT_ACTIVE_ISSUE_LIMIT,
        participants: Optional[list[str]] = None,
        statuses: Optional[list[IssueStatus]] = None,
    ) -> list[IssueState]:
        """Return active issues filtered deterministically by participants and status."""
        return get_active_issues_helper(
            manager=self,
            limit=limit,
            participants=participants,
            statuses=statuses,
        )

    def retrieve_public_events(
        self,
        *,
        participants: Optional[list[str]] = None,
        issue_ids: Optional[list[str]] = None,
        location: Optional[str] = None,
        significance: Optional[list[str]] = None,
        limit: Optional[int] = None,
        known_by: Optional[str] = None,
        min_turn_index: Optional[int] = None,
    ) -> list[PublicEvent]:
        """Return public events filtered by deterministic continuity criteria."""
        return retrieve_public_events_helper(
            manager=self,
            participants=participants,
            issue_ids=issue_ids,
            location=location,
            significance=significance,
            limit=limit,
            known_by=known_by,
            min_turn_index=min_turn_index,
        )

    def retrieve_summary_blocks(
        self,
        *,
        participants: Optional[list[str]] = None,
        issue_ids: Optional[list[str]] = None,
        location: Optional[str] = None,
        limit: int = DEFAULT_SUMMARY_PROMPT_LIMIT,
        min_turn_index: Optional[int] = None,
    ) -> list[SummaryBlock]:
        """Return summary blocks filtered deterministically for prompt assembly."""
        return retrieve_summary_blocks_helper(
            manager=self,
            participants=participants,
            issue_ids=issue_ids,
            location=location,
            limit=limit,
            min_turn_index=min_turn_index,
        )

    def get_resolved_issue_descriptions(self, limit: int = 8) -> list[str]:
        """Return recent resolved issue descriptions for orchestration/UI compatibility."""
        return get_resolved_issue_descriptions_helper(manager=self, limit=limit)

    def get_orchestration_context(
        self,
        *,
        active_issue_limit: int = DEFAULT_ACTIVE_ISSUE_LIMIT,
        recent_event_limit: int = DEFAULT_RECENT_EVENT_PROMPT_LIMIT,
        summary_limit: int = DEFAULT_SUMMARY_PROMPT_LIMIT,
    ) -> dict[str, Any]:
        """Return a continuity-owned orchestration view for app prompt assembly."""
        return build_orchestration_context(
            manager=self,
            active_issue_limit=active_issue_limit,
            recent_event_limit=recent_event_limit,
            summary_limit=summary_limit,
        )

    def share_event_knowledge(
        self, event_id: str, character_name: str, knowledge_type: str
    ) -> None:
        """Record that a character knows an event by observation, telling, or inference."""
        share_event_knowledge_helper(
            manager=self,
            event_id=event_id,
            character_name=character_name,
            knowledge_type=knowledge_type,
        )

    def _turn_tokens(self, move: dict[str, Any]) -> set[str]:
        return turn_tokens(move=move, issue_tokens_fn=self._issue_tokens)

    def _event_tokens(self, event: PublicEvent) -> set[str]:
        return event_tokens(event=event, issue_tokens_fn=self._issue_tokens)

    def _mentioned_participants(self, text: str, participants: list[str]) -> list[str]:
        return mentioned_participants_helper(text=text, participants=participants)

    def _merge_issue_terms(self, issue: IssueState, matched_terms: set[str]) -> None:
        merge_issue_terms(issue=issue, matched_terms=matched_terms)

    def _link_issue_interactions(self, issue_id: str) -> None:
        link_issue_interactions(manager=self, issue_id=issue_id)

    def _propagate_knowledge_from_turn(
        self,
        acting_character: str,
        move: dict[str, Any],
        other_characters: list[str],
    ) -> None:
        propagate_knowledge_from_turn_helper(
            manager=self,
            acting_character=acting_character,
            move=move,
            other_characters=other_characters,
            knowledge_share_min_overlap=KNOWLEDGE_SHARE_MIN_OVERLAP,
            turn_tokens_fn=self._turn_tokens,
            event_tokens_fn=self._event_tokens,
            mentioned_participants_fn=self._mentioned_participants,
            share_event_knowledge_fn=self.share_event_knowledge,
        )

    def _issue_tokens(self, text: str) -> set[str]:
        """Normalize issue text into comparable tokens."""
        return issue_tokens(text=text, stopwords=ISSUE_TOKEN_STOPWORDS)

    def _find_matching_issue(
        self, pressure_profile: dict[str, Any]
    ) -> IssueState | None:
        """Find an existing unresolved issue that likely matches this pressure."""
        return find_matching_issue(
            manager=self,
            pressure_profile=pressure_profile,
            issue_tokens_fn=self._issue_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full continuity manager state for persistence."""
        return serialize_manager_state(manager=self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContinuityManager":
        """Restore the continuity manager from persisted state."""
        return restore_manager_state(
            manager_cls=cls,
            data=data,
            default_summary_interval=DEFAULT_SUMMARY_INTERVAL,
            default_recent_event_window=DEFAULT_RECENT_EVENT_WINDOW,
        )

    def initialize_scene(
        self,
        location: Optional[str],
        opening_description: str,
        present_characters: list[str],
        initial_issues: Optional[list[IssueState]] = None,
    ) -> None:
        """Set up fresh continuity state for a new scene."""
        initialize_scene_state(
            manager=self,
            location=location,
            opening_description=opening_description,
            present_characters=present_characters,
            initial_issues=initial_issues,
        )

    def process_turn(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        other_characters: list[str],
        timestamp: Optional[datetime] = None,
    ) -> ContinuitySnapshot:
        """Process a completed turn and update continuity state.

        Args:
            acting_character: Name of character who just acted
            move: Structured move with action, dialogue, motivation
            director_decision: Director's decision for this turn
            other_characters: Names of other present characters
            timestamp: When this turn occurred (defaults to now)

        Returns:
            Snapshot of continuity state after processing
        """
        timestamp = self._normalize_timestamp(timestamp)

        if self.scene_state is None:
            raise RuntimeError("Scene not initialized. Call initialize_scene() first.")

        turn_index = self.turn_counter + 1
        turn_consequences = self._classify_turn_consequences(
            acting_character,
            move,
            director_decision,
        )

        event = self._maybe_create_event(
            acting_character,
            move,
            director_decision,
            timestamp,
            turn_index,
            turn_consequences,
        )
        if event:
            self.public_events.append(event)
            self.scene_state.recent_event_ids.append(event.event_id)
            self.scene_state.recent_event_ids = self.scene_state.recent_event_ids[-10:]

        self._update_scene_state(
            acting_character,
            move,
            director_decision,
            event,
            turn_consequences,
        )

        self._maybe_create_issue(
            acting_character,
            move,
            director_decision,
            event,
            timestamp,
            turn_consequences,
        )

        self._update_issues(
            acting_character,
            move,
            event,
            turn_consequences,
        )

        resolved_outcome_debug = apply_registered_resolved_outcome_updates(
            manager=self,
            move=move,
            event=event,
            turn_consequences=turn_consequences,
            turn_index=turn_index,
        )
        turn_consequences.setdefault("resolved_outcomes", {}).update(
            resolved_outcome_debug
        )

        self._update_interpretations(
            acting_character, move, director_decision, other_characters, timestamp
        )

        self._propagate_knowledge_from_turn(acting_character, move, other_characters)

        self.turn_counter = turn_index
        self.turn_metadata_by_index[turn_index] = turn_consequences
        self._maybe_generate_summary_block(timestamp)

        return self.get_snapshot(timestamp)

    def _maybe_create_event(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        timestamp: datetime,
        turn_index: int,
        turn_consequences: dict[str, Any],
    ) -> Optional[PublicEvent]:
        if not turn_consequences.get("should_create_event", False):
            return None

        self.event_counter += 1
        event_id = f"evt_{timestamp.isoformat()}_{self.event_counter}"

        return PublicEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=str(turn_consequences.get("event_type", "action") or "action"),
            participants=[acting_character],
            summary=str(
                turn_consequences.get("summary", "")
                or f"{acting_character} took action"
            ),
            turn_index=turn_index,
            location=self.scene_state.location if self.scene_state else None,
            significance=str(turn_consequences.get("significance", "minor") or "minor"),
            observed_by=(
                self.scene_state.present_characters[:]
                if self.scene_state
                else [acting_character]
            ),
            known_by=(
                self.scene_state.present_characters[:]
                if self.scene_state
                else [acting_character]
            ),
            state_changes=[
                str(item)
                for item in turn_consequences.get("state_changes", [])
                if str(item).strip()
            ],
            actionable_implications=[
                str(item)
                for item in turn_consequences.get("actionable_implications", [])
                if str(item).strip()
            ],
            grounding_markers=[
                str(item)
                for item in turn_consequences.get("grounding_markers", [])
                if str(item).strip()
            ],
        )

    def _maybe_generate_summary_block(self, timestamp: datetime) -> SummaryBlock | None:
        """Compress older public history into a structured summary block at a fixed interval."""
        return maybe_generate_summary_block_helper(manager=self, timestamp=timestamp)

    def _build_summary_block(
        self, events: list[PublicEvent], generated_at: datetime
    ) -> SummaryBlock:
        """Build a structured summary block from aged-out public events."""
        return build_summary_block_helper(
            manager=self, events=events, generated_at=generated_at
        )

    def _collect_issue_updates(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, str]]:
        """Collect structured issue lifecycle changes within a summary window."""
        return collect_issue_updates_helper(
            manager=self, start_time=start_time, end_time=end_time
        )

    def _collect_interpretation_shifts(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, object]]:
        """Collect grouped interpretation changes within a summary window."""
        return collect_interpretation_shifts_helper(
            manager=self, start_time=start_time, end_time=end_time
        )

    def get_summary_blocks(
        self, limit: int = DEFAULT_SUMMARY_PROMPT_LIMIT
    ) -> list[SummaryBlock]:
        """Return recent summary blocks for prompt assembly."""
        return get_summary_blocks_helper(manager=self, limit=limit)

    def _update_scene_state(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        event: Optional[PublicEvent],
        turn_consequences: dict[str, Any],
    ) -> None:
        """Update scene state based on director decisions and flow."""
        if self.scene_state is None:
            return

        tension_shift = director_decision.get("tension_shift", "")
        environment_event = director_decision.get("environment_event", "")
        consequence_tags = {
            str(item) for item in turn_consequences.get("tags", []) if str(item).strip()
        }

        if tension_shift == "escalate":
            self._escalate_tension()
        elif tension_shift == "soften":
            self._reduce_tension()

        if environment_event:
            self.scene_state.recent_environment_events.append(environment_event)
            self.scene_state.recent_environment_events = (
                self.scene_state.recent_environment_events[-5:]
            )
            self.scene_state.environment_description = environment_event

        if "exit" in consequence_tags:
            constraints = self.scene_state.character_presence_constraints or {}
            must_remain_cast = (
                str(constraints.get(acting_character, "") or "") == "must_remain"
            )
            if not must_remain_cast:
                scene_for_exit = self.scene_state.to_dict()
                hard_departure = has_hard_scene_departure_evidence(move, scene_for_exit)
                skip_soft_removal = (
                    not hard_departure
                    and self._should_skip_soft_exit_presence_removal(
                        acting_character, move
                    )
                )
                if not skip_soft_removal:
                    self.scene_state.present_characters = [
                        name
                        for name in self.scene_state.present_characters
                        if name != acting_character
                    ]
                    if acting_character not in self.scene_state.absent_but_relevant:
                        self.scene_state.absent_but_relevant.append(acting_character)
        if "entry" in consequence_tags:
            if acting_character not in self.scene_state.present_characters:
                self.scene_state.present_characters.append(acting_character)
            self.scene_state.absent_but_relevant = [
                name
                for name in self.scene_state.absent_but_relevant
                if name != acting_character
            ]
            self.remove_from_offstage(acting_character)

        scene_dict = self.scene_state.to_dict()
        if detect_exit_from_scene(move, scene_dict):
            self.mark_character_offstage(acting_character)
        if has_scene_reentry_evidence(move):
            self.remove_from_offstage(acting_character)

        self._update_scene_phase()

        consequence_delta = next(
            (
                str(change)
                for change in (
                    event.state_changes
                    if event is not None
                    else turn_consequences.get("state_changes", [])
                )
                if str(change).strip()
            ),
            "",
        )
        self.scene_state.recent_delta = (
            consequence_delta
            or (event.summary if event else "")
            or environment_event
            or tension_shift
            or str(move.get("action", "character action"))
        )

        self._reconcile_presence_lists()
        self._assert_presence_invariant_after_reconcile()

    def _reconcile_presence_lists(self) -> None:
        """Drop absent entries that are still present; dedupe both lists."""
        if self.scene_state is None:
            return
        seen_present: set[str] = set()
        deduped_present: list[str] = []
        for name in self.scene_state.present_characters:
            n = str(name).strip()
            if not n or n in seen_present:
                continue
            seen_present.add(n)
            deduped_present.append(n)
        self.scene_state.present_characters = deduped_present
        present_set = set(self.scene_state.present_characters)
        filtered_absent = [
            str(n).strip()
            for n in self.scene_state.absent_but_relevant
            if str(n).strip() and str(n).strip() not in present_set
        ]
        seen_absent: set[str] = set()
        deduped_absent: list[str] = []
        for n in filtered_absent:
            if n in seen_absent:
                continue
            seen_absent.add(n)
            deduped_absent.append(n)
        self.scene_state.absent_but_relevant = deduped_absent

        present_off = set(self.scene_state.present_characters)
        seen_off: set[str] = set()
        deduped_off: list[str] = []
        for n in self.scene_state.offstage_characters:
            n = str(n).strip()
            if not n or n not in present_off or n in seen_off:
                continue
            seen_off.add(n)
            deduped_off.append(n)
        self.scene_state.offstage_characters = deduped_off

    def mark_character_offstage(self, character_name: str) -> None:
        if self.scene_state is None:
            return
        if character_name not in self.scene_state.present_characters:
            return
        if character_name not in self.scene_state.offstage_characters:
            self.scene_state.offstage_characters.append(character_name)

    def remove_from_offstage(self, character_name: str) -> None:
        if self.scene_state is None:
            return
        self.scene_state.offstage_characters = [
            n for n in self.scene_state.offstage_characters if n != character_name
        ]

    def _assert_presence_invariant_after_reconcile(self) -> None:
        if self.scene_state is None:
            return
        present = set(self.scene_state.present_characters)
        absent = set(self.scene_state.absent_but_relevant)
        overlap = present & absent
        if not overlap:
            return
        message = (
            "continuity presence invariant failed after reconcile: "
            f"present ∩ absent_but_relevant = {overlap!r}"
        )
        if os.environ.get("RP_CONTINUITY_STRICT_INVARIANTS", "").strip() == "1":
            raise AssertionError(message)
        logger.warning(message)

    def _acting_character_named_in_current_move(
        self, acting_character: str, move: dict[str, Any]
    ) -> bool:
        """True if the actor's id tokens appear in this turn's authored text."""
        tokens: list[str] = []
        for segment in acting_character.replace("_", " ").split():
            s = segment.strip()
            if len(s) >= 3:
                tokens.append(s.lower())
        if not tokens:
            return False
        motivation = move.get("motivation", {})
        if not isinstance(motivation, dict):
            motivation = {}
        chunks = [
            str(move.get("action", "") or ""),
            str(move.get("dialogue", "") or ""),
            str(motivation.get("goal", "") or ""),
            str(motivation.get("tactic", "") or ""),
        ]
        text = " ".join(chunks).lower()
        for token in tokens:
            if re.search(rf"\b{re.escape(token)}\b", text):
                return True
        return False

    def _acting_character_required_by_active_confrontation(
        self, acting_character: str
    ) -> bool:
        if not self.scene_state:
            return False
        issues = get_active_issues_helper(
            manager=self,
            limit=24,
            participants=[acting_character],
            statuses=[IssueStatus.ACTIVE, IssueStatus.ESCALATING],
        )
        for issue in issues:
            if acting_character not in issue.participants:
                continue
            if len(issue.participants) >= 2:
                return True
            blocked = getattr(issue, "blocked_characters", None) or []
            if acting_character in blocked:
                return True
            rn = (issue.required_next_step or "").lower()
            if any(
                needle in rn
                for needle in (
                    "targeted character",
                    "must exit",
                    "challenge back",
                    "submit",
                    "respond",
                )
            ):
                return True
        return False

    def _should_skip_soft_exit_presence_removal(
        self, acting_character: str, move: dict[str, Any]
    ) -> bool:
        if self._acting_character_named_in_current_move(acting_character, move):
            return True
        if self._acting_character_required_by_active_confrontation(acting_character):
            return True
        return False

    def _maybe_create_issue(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        event: Optional[PublicEvent],
        timestamp: datetime,
        turn_consequences: dict[str, Any],
    ) -> None:
        """Create a lightweight issue when a turn introduces clear pressure."""
        maybe_create_issue(
            manager=self,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
            event=event,
            consequence_tags={
                str(item)
                for item in turn_consequences.get("tags", [])
                if str(item).strip()
            },
            state_changes=[
                str(item)
                for item in turn_consequences.get("state_changes", [])
                if str(item).strip()
            ],
            actionable_implications=[
                str(item)
                for item in turn_consequences.get("actionable_implications", [])
                if str(item).strip()
            ],
            timestamp=timestamp,
            max_active_issues=MAX_ACTIVE_ISSUES,
            turn_tokens_fn=self._turn_tokens,
            find_matching_issue_fn=self._find_matching_issue,
            merge_issue_terms_fn=self._merge_issue_terms,
            link_issue_interactions_fn=self._link_issue_interactions,
        )

    def _escalate_tension(self) -> None:
        """Increase scene tension level."""
        levels = ["low", "moderate", "high", "extreme"]
        current = self.scene_state.current_tension_level
        if current in levels:
            idx = levels.index(current)
            if idx < len(levels) - 1:
                self.scene_state.current_tension_level = levels[idx + 1]

    def _reduce_tension(self) -> None:
        """Decrease scene tension level."""
        levels = ["low", "moderate", "high", "extreme"]
        current = self.scene_state.current_tension_level
        if current in levels:
            idx = levels.index(current)
            if idx > 0:
                self.scene_state.current_tension_level = levels[idx - 1]

    def _update_scene_phase(self) -> None:
        """Update scene phase based on tension and progression."""
        tension = self.scene_state.current_tension_level
        phase = self.scene_state.phase

        if phase == ScenePhase.OPENING and tension in ["moderate", "high"]:
            self.scene_state.phase = ScenePhase.RISING
        elif phase == ScenePhase.RISING and tension == "extreme":
            self.scene_state.phase = ScenePhase.CLIMAX
        elif phase == ScenePhase.CLIMAX and tension in ["low", "moderate"]:
            self.scene_state.phase = ScenePhase.FALLING

    def _update_issues(
        self,
        acting_character: str,
        move: dict[str, Any],
        event: Optional[PublicEvent],
        turn_consequences: dict[str, Any],
    ) -> None:
        """Update issue states based on turn content."""
        update_issues(
            manager=self,
            acting_character=acting_character,
            move=move,
            event=event,
            consequence_tags={
                str(item)
                for item in turn_consequences.get("tags", [])
                if str(item).strip()
            },
            state_changes=[
                str(item)
                for item in turn_consequences.get("state_changes", [])
                if str(item).strip()
            ],
            actionable_implications=[
                str(item)
                for item in turn_consequences.get("actionable_implications", [])
                if str(item).strip()
            ],
            issue_stall_turn_threshold=ISSUE_STALL_TURN_THRESHOLD,
            turn_tokens_fn=self._turn_tokens,
            issue_tokens_fn=self._issue_tokens,
            merge_issue_terms_fn=self._merge_issue_terms,
            link_issue_interactions_fn=self._link_issue_interactions,
        )

    def _update_interpretations(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        other_characters: list[str],
        timestamp: datetime,
    ) -> None:
        """Update per-character interpretations of what just happened."""
        update_interpretations_helper(
            manager=self,
            acting_character=acting_character,
            move=move,
            other_characters=other_characters,
            timestamp=timestamp,
        )

    def get_snapshot(self, timestamp: Optional[datetime] = None) -> ContinuitySnapshot:
        """Get a complete snapshot of current continuity state."""
        return build_snapshot(
            manager=self,
            timestamp=timestamp,
            normalize_timestamp_fn=self._normalize_timestamp,
        )

    def get_character_context(
        self, character_name: str, max_interpretations: int = 5
    ) -> dict[str, Any]:
        """Get layered context for a specific character.

        Returns:
            Dict with scene_state, active_issues, recent_events, and character's interpretations
        """
        return build_character_context(
            manager=self,
            character_name=character_name,
            max_interpretations=max_interpretations,
            default_active_issue_limit=DEFAULT_ACTIVE_ISSUE_LIMIT,
            default_summary_prompt_limit=DEFAULT_SUMMARY_PROMPT_LIMIT,
        )
