"""Continuity manager for RP app.

Runs between turns to convert transient dialogue into durable narrative state.
Responsible for: promoting moves to events, updating issue state,
updating scene state, managing character interpretations, enforcing knowledge boundaries.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from continuity_presence_helpers import PresenceAuthorityScratch

from continuity_canon_anchors import (
    get_relevant_canon_anchors as get_relevant_canon_anchors_impl,
    get_scene_canon_anchors as get_scene_canon_anchors_impl,
    seed_character_canon_anchors as seed_character_canon_anchors_impl,
    upsert_canon_anchor as upsert_canon_anchor_impl,
)
from continuity_presence_pipeline import (
    manager_apply_pre_turn_user_presence_routing as pre_turn_presence_routing_impl,
    manager_apply_must_remain_presence_from_fn as apply_must_remain_presence_impl,
    manager_bootstrap_present_characters_from_cast as bootstrap_present_from_cast_impl,
    manager_ensure_at_least_one_present_character as ensure_one_present_impl,
    manager_reconcile_presence_lists as reconcile_presence_lists_impl,
    manager_resync_presence_through_authority as resync_presence_impl,
    manager_presence_scratch_from_scene_state as presence_scratch_impl,
    manager_purge_excursion_participants_from_offstage_scratch as purge_excursion_offstage_impl,
    manager_strip_active_excursions_from_focal_scratch as strip_excursions_focal_impl,
    manager_synchronize_presence_from_canonical_authority as synchronize_presence_impl,
    manager_reconcile_presence_lists_scratch as reconcile_presence_scratch_impl,
    manager_process_structured_reentries_from_move_scratch as process_reentries_impl,
    manager_apply_canonical_reentry_scratch as apply_canonical_reentry_impl,
    manager_apply_canonical_exit_offstage_transition_scratch as apply_exit_offstage_impl,
    manager_ensure_at_least_one_present_character_scratch as ensure_one_present_scratch_impl,
    manager_assert_presence_invariant_after_reconcile_scratch as assert_invariant_scratch_impl,
)
from continuity_scene_state_update import run_update_scene_state
from continuity_turn_classification import classify_turn_consequences_for_manager

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
    manager_notify_raw_location_bypass_for_audit,
    manager_record_continuity_audit_event,
    manager_suppress_direct_excursion_bypass_audit,
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
    ExcursionRecord,
    ExcursionStatus,
    IssueState,
    IssueStatus,
    PublicEvent,
    SceneState,
    SummaryBlock,
)

from continuity_consequence_classifier import ConsequenceClassifier
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
        return manager_suppress_direct_excursion_bypass_audit(self)

    def _record_continuity_audit_event(
        self, kind: str, continuity_turn_index: int
    ) -> None:
        manager_record_continuity_audit_event(self, kind, continuity_turn_index)

    def notify_raw_location_bypass_for_audit(
        self, *, continuity_turn_index: Optional[int] = None
    ) -> None:
        """Call after assigning ``scene_state.location`` outside ``process_turn`` (Slice 3)."""
        manager_notify_raw_location_bypass_for_audit(
            self, continuity_turn_index=continuity_turn_index
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
            manager_record_continuity_audit_event(
                self,
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
                opened_turn,
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
            manager_record_continuity_audit_event(
                self,
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
            manager_record_continuity_audit_event(
                self,
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
                closed_idx,
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
        return classify_turn_consequences_for_manager(
            self,
            acting_character,
            move,
            director_decision,
            consequence_classifier=self._consequence_classifier,
        )

    def _upsert_canon_anchor(self, anchor: CanonAnchor) -> None:
        """Insert or replace a canon anchor by ID."""
        upsert_canon_anchor_impl(self, anchor)

    def seed_character_canon_anchors(self, character_states: dict[str, Any]) -> None:
        """Seed protected canon anchors from current character state data."""
        seed_character_canon_anchors_impl(self, character_states)

    def get_relevant_canon_anchors(
        self,
        character_name: str,
        participants: Optional[list[str]] = None,
        limit: int = 6,
    ) -> list[CanonAnchor]:
        """Return canon anchors most relevant to the named character in this scene."""
        return get_relevant_canon_anchors_impl(
            self, character_name, participants=participants, limit=limit
        )

    def get_scene_canon_anchors(self, limit: int = 10) -> list[CanonAnchor]:
        """Return canon anchors broadly relevant to the current scene."""
        return get_scene_canon_anchors_impl(self, limit)

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
        return presence_scratch_impl(self)

    def _strip_active_excursions_from_focal_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Enforce P_focal ∩ E_active = ∅ before committing presence."""
        strip_excursions_focal_impl(self, scratch)

    def _purge_excursion_participants_from_offstage_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Excursion participants must not be soft-offstage (Issue #81 Slice B).

        Clears ``offstage_characters`` and presence-status rows for ``E_active`` in the
        same scratch write as focal stripping — no partial excursion-without-presence-fix.
        """
        purge_excursion_offstage_impl(self, scratch)

    def _resync_presence_through_authority(self) -> None:
        """Full presence pipeline: reconcile → invariant → ensure-one → sync (single writer)."""
        resync_presence_impl(self)

    def _synchronize_presence_from_canonical_authority(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        synchronize_presence_impl(self, scratch)

    def apply_pre_turn_user_presence_routing(
        self,
        *,
        trigger_text: str,
        participant_names: list[str],
        get_character_display_name_fn: Callable[[str], str],
        pending_forced_speaker: str | None,
    ) -> None:
        """Apply Traveler offstage hints through the single presence sync path."""
        pre_turn_presence_routing_impl(
            self,
            trigger_text=trigger_text,
            participant_names=participant_names,
            get_character_display_name_fn=get_character_display_name_fn,
            pending_forced_speaker=pending_forced_speaker,
        )

    def apply_must_remain_presence_from_fn(
        self, get_must_remain_characters_fn: Callable[[dict[str, Any]], Any]
    ) -> None:
        apply_must_remain_presence_impl(self, get_must_remain_characters_fn)

    def bootstrap_present_characters_from_cast(self, character_names: list[str]) -> None:
        """If on-stage roster is empty, seed it from the cast list (restore / init guard)."""
        bootstrap_present_from_cast_impl(self, character_names)

    def _reconcile_presence_lists_scratch(self, scratch: PresenceAuthorityScratch) -> None:
        reconcile_presence_scratch_impl(self, scratch)

    def _process_structured_reentries_from_move_scratch(
        self, move: dict[str, Any], scratch: PresenceAuthorityScratch
    ) -> None:
        process_reentries_impl(self, move, scratch)

    def _apply_canonical_reentry_scratch(
        self, scratch: PresenceAuthorityScratch, character_name: str
    ) -> None:
        apply_canonical_reentry_impl(self, scratch, character_name)

    def _apply_canonical_exit_offstage_transition_scratch(
        self,
        acting_character: str,
        move: dict[str, Any],
        *,
        consequence_tags: set[str],
        scene_dict: dict[str, Any],
        scratch: PresenceAuthorityScratch,
    ) -> None:
        apply_exit_offstage_impl(
            self,
            acting_character,
            move,
            consequence_tags=consequence_tags,
            scene_dict=scene_dict,
            scratch=scratch,
            should_skip_soft_exit_presence_removal=self._should_skip_soft_exit_presence_removal,
        )

    def _ensure_at_least_one_present_character_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        ensure_one_present_scratch_impl(self, scratch)

    def _assert_presence_invariant_after_reconcile_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        assert_invariant_scratch_impl(scratch)

    def _reconcile_presence_lists(self) -> None:
        """Drop absent entries that are still present; dedupe both lists (synced write path)."""
        reconcile_presence_lists_impl(self)

    def _ensure_at_least_one_present_character(self) -> None:
        """Deadlock guard via scratch + single sync (see scratch helper for tier rules)."""
        ensure_one_present_impl(self)

    def _update_scene_state(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        event: Optional[PublicEvent],
        turn_consequences: dict[str, Any],
    ) -> None:
        """Update scene state based on director decisions and flow."""
        run_update_scene_state(
            self,
            acting_character,
            move,
            director_decision,
            event,
            turn_consequences,
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
