"""Continuity manager for RP app.

Runs between turns to convert transient dialogue into durable narrative state.
Responsible for: promoting moves to events, updating issue state,
updating scene state, managing character interpretations, enforcing knowledge boundaries.
"""

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from scene_exit_detection import has_scene_reentry_evidence

from continuity_presence_helpers import (
    PresenceAuthorityScratch,
    align_exit_narrative_with_effective_presence,
    apply_canonical_exit_offstage_transition_scratch,
    apply_canonical_reentry_scratch,
    assert_presence_invariant_after_reconcile_scratch,
    ensure_at_least_one_present_character_scratch,
    presence_scratch_from_scene_state,
    process_structured_reentries_from_move_scratch,
    purge_excursion_participants_from_offstage_scratch,
    reconcile_presence_lists_scratch,
    strip_active_excursions_from_focal_scratch,
)

from continuity_issue_helpers import (
    event_tokens,
    get_active_issues as get_active_issues_helper,
    get_resolved_issue_descriptions as get_resolved_issue_descriptions_helper,
    maybe_create_issue,
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
    build_housing_call_state_change,
    build_location_entry_state_change,
    build_sleeping_surface_state_change,
    build_suppressant_formulation_state_change,
)
from continuity_mutation_pipeline import (
    MutationRequest,
    apply_resolved_mutations,
    compose_resolved_mutations,
    validate_resolved_mutations_globally,
)
from continuity_process_turn_orchestration import (
    run_process_turn_after_resolved_mutations_applied,
)
from continuity_audit_origin import (
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION,
)
from continuity_setup_seam_v77 import ContinuitySetupSeamIncompleteError
from continuity_scene_helpers import (
    build_character_context,
    build_orchestration_context,
    build_snapshot,
    initialize_scene_state,
    restore_manager_state,
    serialize_manager_state,
)
from perception_audibility import (
    event_knowledge_recipients,
    normalize_move_audibility,
    public_safe_event_summary,
)

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    ContinuitySnapshot,
    DetectedConsequence,
    ExcursionRecord,
    ExcursionStatus,
    IssueState,
    IssueStatus,
    PublicEvent,
    ScenePhase,
    SceneState,
    SummaryBlock,
)

from continuity_consequence_classifier import ConsequenceClassifier
from continuity_consequence_phrase_maps import (
    CATEGORY_ACTIONABLE_IMPLICATIONS,
    category_state_change_phrases,
)
from continuity_event_promotion_policy import compute_event_promotion_policy_fields
from tension_pacing_policy import (
    apply_consequence_up_saturation_gate,
    resolve_hybrid_pacing,
)
from user_presence_signals import (
    apply_user_trigger_to_offstage_on_scratch,
    release_pending_forced_speaker_on_scratch,
)
from continuity_issue_manager_wiring import (
    DEFAULT_ACTIVE_ISSUE_LIMIT,
    ISSUE_STALL_TURN_THRESHOLD,
    ISSUE_TOKEN_STOPWORDS,
    MAX_ACTIVE_ISSUES,
    find_matching_issue_for_manager,
    issue_tokens_for_manager_stopwords,
    link_issue_interactions_callback,
    merge_issue_terms_positional,
)

DEFAULT_SUMMARY_INTERVAL = 12
DEFAULT_RECENT_EVENT_WINDOW = 8
DEFAULT_SUMMARY_PROMPT_LIMIT = 3
DEFAULT_RECENT_EVENT_PROMPT_LIMIT = 6
KNOWLEDGE_SHARE_MIN_OVERLAP = 2

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
        self.anchor_character_id: Optional[str] = None
        self.setup_seam_complete: bool = False
        self.excursions: dict[str, ExcursionRecord] = {}
        # Issue #79 Slice 3 — session audit origin log (read/flush at export only).
        self.continuity_audit_origin_log: list[dict[str, Any]] = []
        self._continuity_pipeline_turn_active: bool = False
        self._continuity_in_reintegration_apply: bool = False
        self._pending_pipeline_audit_origin_index: Optional[int] = None

    def _suppress_direct_excursion_bypass_audit(self) -> bool:
        return bool(
            self._continuity_pipeline_turn_active
            or self._continuity_in_reintegration_apply
        )

    def _record_continuity_audit_event(
        self, kind: str, continuity_turn_index: int
    ) -> None:
        self.continuity_audit_origin_log.append(
            {"continuity_turn_index": int(continuity_turn_index), "kind": str(kind)}
        )

    def notify_raw_location_bypass_for_audit(
        self, *, continuity_turn_index: Optional[int] = None
    ) -> None:
        """Call after assigning ``scene_state.location`` outside ``process_turn`` (Slice 3)."""
        idx = (
            int(continuity_turn_index)
            if continuity_turn_index is not None
            else int(self.turn_counter)
        )
        self._record_continuity_audit_event(
            CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION, idx
        )

    def open_excursion(
        self,
        *,
        participant_character_ids: list[str],
        excursion_id: Optional[str] = None,
        opened_at_turn: Optional[int] = None,
    ) -> str:
        """Register an active excursion, then resync focal presence (excursion–focal boundary)."""
        participants = [
            str(x).strip()
            for x in participant_character_ids
            if str(x or "").strip()
        ]
        if not participants:
            raise ValueError("open_excursion requires at least one participant")
        eid = (str(excursion_id).strip() if excursion_id else "") or str(uuid.uuid4())
        if eid in self.excursions:
            raise ValueError(f"excursion_id already exists: {eid!r}")
        opened_turn = (
            int(opened_at_turn)
            if opened_at_turn is not None
            else int(self.turn_counter)
        )
        self.excursions[eid] = ExcursionRecord(
            excursion_id=eid,
            participant_character_ids=participants,
            status=ExcursionStatus.ACTIVE,
            opened_at_turn=opened_turn,
            closed_at_turn=None,
        )
        self._resync_presence_through_authority()
        if not self._suppress_direct_excursion_bypass_audit():
            self._record_continuity_audit_event(
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API, opened_turn
            )
        return eid

    def update_excursion(
        self,
        excursion_id: str,
        *,
        participant_character_ids: Optional[list[str]] = None,
    ) -> None:
        """Update an active excursion; resyncs focal presence if participant membership changes."""
        eid = str(excursion_id or "").strip()
        rec = self.excursions.get(eid)
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
                self._resync_presence_through_authority()
        if not self._suppress_direct_excursion_bypass_audit():
            self._record_continuity_audit_event(
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
                int(self.turn_counter),
            )

    def close_excursion(
        self,
        excursion_id: str,
        *,
        closed_at_turn: Optional[int] = None,
    ) -> None:
        """Mark an excursion closed and resync focal presence (no excursion reintegration)."""
        eid = str(excursion_id or "").strip()
        rec = self.excursions.get(eid)
        if rec is None:
            raise KeyError(excursion_id)
        if rec.status == ExcursionStatus.CLOSED:
            return
        rec.status = ExcursionStatus.CLOSED
        rec.closed_at_turn = (
            int(closed_at_turn)
            if closed_at_turn is not None
            else int(self.turn_counter)
        )
        self._resync_presence_through_authority()
        closed_idx = int(rec.closed_at_turn or self.turn_counter)
        if not self._suppress_direct_excursion_bypass_audit():
            self._record_continuity_audit_event(
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API, closed_idx
            )

    def active_excursion_character_ids(self) -> set[str]:
        """Union of participants on all active excursions (E_active); read-only."""
        out: set[str] = set()
        for rec in self.excursions.values():
            if rec.status != ExcursionStatus.ACTIVE:
                continue
            for pid in rec.participant_character_ids:
                n = str(pid).strip()
                if n:
                    out.add(n)
        return out

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

        category_state_change = category_state_change_phrases(acting_character)
        category_implication = CATEGORY_ACTIONABLE_IMPLICATIONS

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

        promo = compute_event_promotion_policy_fields(
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
            detected=detected,
            state_changes=state_changes,
            actionable_implications=actionable_implications,
        )
        return {
            "should_create_event": promo["should_create_event"],
            "event_type": promo["event_type"],
            "summary": promo["summary"],
            "significance": promo["significance"],
            "state_changes": state_changes,
            "actionable_implications": actionable_implications,
            "tags": sorted(tags),
            "consequences": [c.category.value for c in detected],  # For audit/debug
            "grounding_markers": promo["grounding_markers"],
        }

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
        return turn_tokens(
            move=move, issue_tokens_fn=issue_tokens_for_manager_stopwords
        )

    def _event_tokens(self, event: PublicEvent) -> set[str]:
        return event_tokens(
            event=event, issue_tokens_fn=issue_tokens_for_manager_stopwords
        )

    def _mentioned_participants(self, text: str, participants: list[str]) -> list[str]:
        return mentioned_participants_helper(text=text, participants=participants)

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
        *,
        session_mutation_candidates: Optional[list[MutationRequest]] = None,
    ) -> ContinuitySnapshot:
        """Process a completed turn and update continuity state.

        Sole runtime commit authority for narrative state: ingress/validation may reject
        moves but does not partially commit. ``scene_state_updates`` semantics are applied
        on this path (registry / resolved outcomes) per Issue #140.

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

        if not self.setup_seam_complete:
            raise ContinuitySetupSeamIncompleteError(
                "D3: continuity setup seam incomplete; cannot process_turn before "
                "finalize_continuity_setup_seam (Issue #77)."
            )

        present_list = (
            list(self.scene_state.present_characters)
            if self.scene_state
            else [acting_character]
        )
        move = normalize_move_audibility(dict(move), acting_character, present_list)

        turn_index = self.turn_counter + 1
        resolved_mutations = compose_resolved_mutations(
            move=move,
            director_decision=director_decision,
            scene_state=self.scene_state,
            session_mutation_candidates=session_mutation_candidates,
        )
        validate_resolved_mutations_globally(
            resolved_mutations,
            self.scene_state,
            acting_character,
            continuity_manager=self,
        )
        self._pending_pipeline_audit_origin_index = None
        self._continuity_pipeline_turn_active = True
        try:
            apply_resolved_mutations(
                resolved_mutations,
                scene_state=self.scene_state,
                continuity_manager=self,
                commit_turn_index=turn_index,
                commit_timestamp=timestamp,
            )

            return run_process_turn_after_resolved_mutations_applied(
                self,
                acting_character=acting_character,
                move=move,
                director_decision=director_decision,
                other_characters=other_characters,
                timestamp=timestamp,
                turn_index=turn_index,
                resolved_mutations=resolved_mutations,
            )
        finally:
            self._continuity_pipeline_turn_active = False

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

        present_list = (
            list(self.scene_state.present_characters[:])
            if self.scene_state
            else [acting_character]
        )
        recipients = event_knowledge_recipients(
            move,
            acting_character=acting_character,
            present_characters=present_list,
        )
        if not recipients:
            recipients = [acting_character]
        raw_summary = str(
            turn_consequences.get("summary", "")
            or f"{acting_character} took action"
        )
        # PublicEventExtraction: only public-safe text in PublicEvent.summary (Issue #140).
        safe_summary = public_safe_event_summary(
            acting_character=acting_character,
            move=move,
            provisional_summary=raw_summary,
        )

        return PublicEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=str(turn_consequences.get("event_type", "action") or "action"),
            participants=[acting_character],
            summary=safe_summary,
            turn_index=turn_index,
            location=self.scene_state.location if self.scene_state else None,
            significance=str(turn_consequences.get("significance", "minor") or "minor"),
            observed_by=list(recipients),
            known_by=list(recipients),
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

    def _presence_scratch_from_scene_state(self) -> PresenceAuthorityScratch:
        assert self.scene_state is not None
        return presence_scratch_from_scene_state(self.scene_state)

    def _strip_active_excursions_from_focal_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Enforce P_focal ∩ E_active = ∅ before committing presence."""
        strip_active_excursions_from_focal_scratch(
            scratch, self.active_excursion_character_ids()
        )

    def _purge_excursion_participants_from_offstage_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Excursion participants must not be soft-offstage (Issue #81 Slice B).

        Clears ``offstage_characters`` and presence-status rows for ``E_active`` in the
        same scratch write as focal stripping — no partial excursion-without-presence-fix.
        """
        purge_excursion_participants_from_offstage_scratch(
            scratch, self.active_excursion_character_ids()
        )

    def _resync_presence_through_authority(self) -> None:
        """Full presence pipeline: reconcile → invariant → ensure-one → sync (single writer)."""
        if self.scene_state is None:
            return
        scratch = self._presence_scratch_from_scene_state()
        self._reconcile_presence_lists_scratch(scratch)
        self._assert_presence_invariant_after_reconcile_scratch(scratch)
        self._ensure_at_least_one_present_character_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

    def _synchronize_presence_from_canonical_authority(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        if self.scene_state is None:
            return
        self._strip_active_excursions_from_focal_scratch(scratch)
        self._purge_excursion_participants_from_offstage_scratch(scratch)
        self.scene_state.present_characters = list(scratch.present_characters)
        self.scene_state.offstage_characters = list(scratch.offstage_characters)
        self.scene_state.character_presence_status = dict(scratch.character_presence_status)
        self.scene_state.absent_but_relevant = list(scratch.absent_but_relevant)

    def apply_pre_turn_user_presence_routing(
        self,
        *,
        trigger_text: str,
        participant_names: list[str],
        get_character_display_name_fn: Callable[[str], str],
        pending_forced_speaker: str | None,
    ) -> None:
        """Apply Traveler offstage hints through the single presence sync path."""
        if self.scene_state is None:
            return
        scratch = self._presence_scratch_from_scene_state()
        apply_user_trigger_to_offstage_on_scratch(
            scratch=scratch,
            trigger_text=trigger_text,
            participant_names=participant_names,
            get_character_display_name_fn=get_character_display_name_fn,
        )
        release_pending_forced_speaker_on_scratch(
            scratch=scratch,
            pending_forced_speaker=pending_forced_speaker,
            participant_names=participant_names,
        )
        self._reconcile_presence_lists_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

    def apply_must_remain_presence_from_fn(
        self, get_must_remain_characters_fn: Callable[[dict[str, Any]], Any]
    ) -> None:
        if self.scene_state is None:
            return
        scratch = self._presence_scratch_from_scene_state()
        scene_dict = self.scene_state.to_dict()
        scene_dict["present_characters"] = list(scratch.present_characters)
        scene_dict["offstage_characters"] = list(scratch.offstage_characters)
        scene_dict["character_presence_status"] = dict(scratch.character_presence_status)
        scene_dict["absent_but_relevant"] = list(scratch.absent_but_relevant)
        must_remain = get_must_remain_characters_fn(scene_dict)
        for character_name in must_remain:
            ch = str(character_name or "").strip()
            if ch:
                self._apply_canonical_reentry_scratch(scratch, ch)
        self._reconcile_presence_lists_scratch(scratch)
        self._assert_presence_invariant_after_reconcile_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

    def bootstrap_present_characters_from_cast(self, character_names: list[str]) -> None:
        """If on-stage roster is empty, seed it from the cast list (restore / init guard)."""
        if self.scene_state is None:
            return
        if self.scene_state.present_characters:
            return
        scratch = self._presence_scratch_from_scene_state()
        scratch.present_characters = [
            str(x).strip() for x in character_names if str(x or "").strip()
        ]
        self._reconcile_presence_lists_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

    def _reconcile_presence_lists_scratch(self, scratch: PresenceAuthorityScratch) -> None:
        reconcile_presence_lists_scratch(scratch)

    def _process_structured_reentries_from_move_scratch(
        self, move: dict[str, Any], scratch: PresenceAuthorityScratch
    ) -> None:
        process_structured_reentries_from_move_scratch(move, scratch)

    def _apply_canonical_reentry_scratch(
        self, scratch: PresenceAuthorityScratch, character_name: str
    ) -> None:
        apply_canonical_reentry_scratch(scratch, character_name)

    def _apply_canonical_exit_offstage_transition_scratch(
        self,
        acting_character: str,
        move: dict[str, Any],
        *,
        consequence_tags: set[str],
        scene_dict: dict[str, Any],
        scratch: PresenceAuthorityScratch,
    ) -> None:
        if self.scene_state is None:
            return
        apply_canonical_exit_offstage_transition_scratch(
            acting_character,
            move,
            consequence_tags=consequence_tags,
            scene_dict=scene_dict,
            scratch=scratch,
            character_presence_constraints=dict(
                self.scene_state.character_presence_constraints or {}
            ),
            should_skip_soft_exit_presence_removal=self._should_skip_soft_exit_presence_removal,
        )

    def _ensure_at_least_one_present_character_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        if self.scene_state is None:
            return
        cast = [
            str(k).strip()
            for k in self.scene_state.role_assignments.keys()
            if str(k).strip()
        ]
        ensure_at_least_one_present_character_scratch(
            scratch,
            cast=cast,
            e_active=self.active_excursion_character_ids(),
            log=logger,
        )

    def _assert_presence_invariant_after_reconcile_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        assert_presence_invariant_after_reconcile_scratch(scratch, log=logger)

    def _reconcile_presence_lists(self) -> None:
        """Drop absent entries that are still present; dedupe both lists (synced write path)."""
        if self.scene_state is None:
            return
        scratch = self._presence_scratch_from_scene_state()
        self._reconcile_presence_lists_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

    def _ensure_at_least_one_present_character(self) -> None:
        """Deadlock guard via scratch + single sync (see scratch helper for tier rules)."""
        if self.scene_state is None:
            return
        scratch = self._presence_scratch_from_scene_state()
        self._ensure_at_least_one_present_character_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

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

        tension_shift_raw = ""
        if isinstance(director_decision, dict):
            tension_shift_raw = str(director_decision.get("tension_shift", "") or "").strip()

        environment_event = (
            director_decision.get("environment_event", "")
            if isinstance(director_decision, dict)
            else ""
        )
        consequence_tags = {
            str(item) for item in turn_consequences.get("tags", []) if str(item).strip()
        }

        pacing_source, pacing_direction, director_neutral = resolve_hybrid_pacing(
            director_decision=director_decision
            if isinstance(director_decision, dict)
            else {},
            turn_consequences=turn_consequences
            if isinstance(turn_consequences, dict)
            else {},
        )
        pacing_source, pacing_direction, suppressed_consequence_up = (
            apply_consequence_up_saturation_gate(
                pacing_source=pacing_source,
                pacing_direction=pacing_direction,
                current_tension_level=self.scene_state.current_tension_level,
            )
        )
        if pacing_direction == "up":
            self._escalate_tension()
        elif pacing_direction == "down":
            self._reduce_tension()
        hybrid_meta: dict[str, Any] = {
            "pacing_source": pacing_source,
            "pacing_direction": pacing_direction,
            "director_neutral": director_neutral,
        }
        if suppressed_consequence_up:
            hybrid_meta["consequence_up_suppressed_saturation"] = True
        turn_consequences["hybrid_pacing"] = hybrid_meta

        if environment_event:
            self.scene_state.recent_environment_events.append(environment_event)
            self.scene_state.recent_environment_events = (
                self.scene_state.recent_environment_events[-5:]
            )
            self.scene_state.environment_description = environment_event

        scratch = self._presence_scratch_from_scene_state()
        self._process_structured_reentries_from_move_scratch(move, scratch)

        if has_scene_reentry_evidence(move):
            self._apply_canonical_reentry_scratch(scratch, acting_character)

        if "entry" in consequence_tags:
            self._apply_canonical_reentry_scratch(scratch, acting_character)

        scene_dict = self.scene_state.to_dict()
        scene_dict["present_characters"] = list(scratch.present_characters)
        scene_dict["offstage_characters"] = list(scratch.offstage_characters)
        scene_dict["character_presence_status"] = dict(scratch.character_presence_status)
        scene_dict["absent_but_relevant"] = list(scratch.absent_but_relevant)
        self._apply_canonical_exit_offstage_transition_scratch(
            acting_character,
            move,
            consequence_tags=consequence_tags,
            scene_dict=scene_dict,
            scratch=scratch,
        )

        self._update_scene_phase()

        self._reconcile_presence_lists_scratch(scratch)
        self._assert_presence_invariant_after_reconcile_scratch(scratch)
        self._ensure_at_least_one_present_character_scratch(scratch)
        self._synchronize_presence_from_canonical_authority(scratch)

        self._align_exit_narrative_with_effective_presence(
            acting_character, turn_consequences
        )

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
            or tension_shift_raw
            or str(move.get("action", "character action"))
        )

    def _align_exit_narrative_with_effective_presence(
        self,
        acting_character: str,
        turn_consequences: dict[str, Any],
    ) -> None:
        """If exit was tagged but the actor remains on-stage, soften event-facing lines.

        Avoids authoritative contradiction: ``present_characters`` still includes the
        actor (e.g. ``must_remain`` / soft skip) while ``state_changes`` claimed full
        departure.
        """
        if self.scene_state is None:
            return
        align_exit_narrative_with_effective_presence(
            present_characters=list(self.scene_state.present_characters or []),
            acting_character=acting_character,
            turn_consequences=turn_consequences,
        )

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
            find_matching_issue_fn=lambda p: find_matching_issue_for_manager(self, p),
            merge_issue_terms_fn=merge_issue_terms_positional,
            link_issue_interactions_fn=link_issue_interactions_callback(self),
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
            issue_tokens_fn=issue_tokens_for_manager_stopwords,
            merge_issue_terms_fn=merge_issue_terms_positional,
            link_issue_interactions_fn=link_issue_interactions_callback(self),
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
