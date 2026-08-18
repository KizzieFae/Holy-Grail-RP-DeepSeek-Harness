"""Continuity manager for RP app.

Runs between turns to convert transient dialogue into durable narrative state.
Responsible for: promoting moves to events, updating issue state,
updating scene state, managing character interpretations, enforcing knowledge boundaries.

Implementation is split across ``continuity_manager_*_surface`` helpers; this module
remains the stable import façade and sole orchestrator for ``process_turn``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from continuity_presence_helpers import PresenceAuthorityScratch

from continuity_scene_state_update import run_update_scene_state
from continuity_turn_classification import classify_turn_consequences_for_manager

from continuity_issue_helpers import (
    event_tokens,
    turn_tokens,
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
from continuity_semantic_proposals import (
    ContinuityProposalLegalityError,
    ProposalAuthorityContext,
    ProposalAuthorityOutcome,
    compile_proposal_excursion_mutations,
    evaluate_proposal_legality,
    proposal_authority_metadata,
)
from continuity_audit_origin import (
    manager_notify_raw_location_bypass_for_audit,
    manager_record_continuity_audit_event,
    manager_suppress_direct_excursion_bypass_audit,
)
from continuity_setup_seam_v77 import ContinuitySetupSeamIncompleteError
from continuity_scene_helpers import (
    initialize_scene_state,
    restore_manager_state,
    serialize_manager_state,
)
from perception_audibility import normalize_move_audibility

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    ContinuitySnapshot,
    ExcursionRecord,
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

from continuity_manager_canon_surface import (
    get_relevant_canon_anchors as get_relevant_canon_anchors_surface,
    get_scene_canon_anchors as get_scene_canon_anchors_surface,
    seed_character_canon_anchors as seed_character_canon_anchors_surface,
    upsert_canon_anchor as upsert_canon_anchor_surface,
)
from continuity_manager_event_surface import (
    build_summary_block_for_manager,
    collect_interpretation_shifts_for_manager,
    maybe_create_event_for_manager,
    maybe_generate_summary_block_for_manager,
)
from continuity_manager_excursions import (
    active_excursion_character_ids as active_excursion_character_ids_surface,
    close_excursion as close_excursion_surface,
    open_excursion as open_excursion_surface,
    update_excursion as update_excursion_surface,
)
from continuity_manager_issue_surface import (
    collect_issue_updates_for_manager,
    maybe_create_issue_for_manager,
    update_issues_for_manager,
)
from continuity_manager_presence_surface import (
    apply_canonical_reentry_scratch as apply_canonical_reentry_scratch_surface,
    apply_must_remain_presence_from_fn as apply_must_remain_presence_from_fn_surface,
    apply_pre_turn_user_presence_routing as apply_pre_turn_user_presence_routing_surface,
    assert_presence_invariant_after_reconcile_scratch as assert_presence_invariant_after_reconcile_scratch_surface,
    bootstrap_present_characters_from_cast as bootstrap_present_characters_from_cast_surface,
    ensure_at_least_one_present_character as ensure_at_least_one_present_character_surface,
    ensure_at_least_one_present_character_scratch as ensure_at_least_one_present_character_scratch_surface,
    presence_scratch_from_scene_state as presence_scratch_from_scene_state_surface,
    purge_excursion_participants_from_offstage_scratch as purge_excursion_participants_from_offstage_scratch_surface,
    reconcile_presence_lists as reconcile_presence_lists_surface,
    reconcile_presence_lists_scratch as reconcile_presence_lists_scratch_surface,
    resync_presence_through_authority as resync_presence_through_authority_surface,
    strip_active_excursions_from_focal_scratch as strip_active_excursions_from_focal_scratch_surface,
    synchronize_presence_from_canonical_authority as synchronize_presence_from_canonical_authority_surface,
)
from continuity_manager_queries import (
    get_active_issues_for_manager,
    get_character_context_for_manager,
    get_orchestration_context_for_manager,
    get_resolved_issue_descriptions_for_manager,
    get_snapshot_for_manager,
    get_summary_blocks_for_manager,
    mentioned_participants_for_text,
    propagate_knowledge_from_turn_for_manager,
    retrieve_public_events_for_manager,
    retrieve_summary_blocks_for_manager,
    share_event_knowledge_for_manager,
    update_interpretations_for_manager,
)

DEFAULT_SUMMARY_INTERVAL = 12
DEFAULT_RECENT_EVENT_WINDOW = 8
DEFAULT_SUMMARY_PROMPT_LIMIT = 3
DEFAULT_RECENT_EVENT_PROMPT_LIMIT = 6
KNOWLEDGE_SHARE_MIN_OVERLAP = 2


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
        return open_excursion_surface(
            self,
            participant_character_ids=participant_character_ids,
            excursion_id=excursion_id,
            opened_at_turn=opened_at_turn,
        )

    def update_excursion(
        self,
        excursion_id: str,
        *,
        participant_character_ids: Optional[list[str]] = None,
    ) -> None:
        """Update an active excursion; resyncs focal presence if participant membership changes."""
        update_excursion_surface(
            self,
            excursion_id,
            participant_character_ids=participant_character_ids,
        )

    def close_excursion(
        self,
        excursion_id: str,
        *,
        closed_at_turn: Optional[int] = None,
    ) -> None:
        """Mark an excursion closed, resync focal presence, and restore participants to focal roster.

        Slice C **reintegration** merge (events/issues/outcomes) is separate from this API; focal
        re-presence after close uses the same canonical reentry scratch as structured
        ``presence_changes`` (GitHub #214 Tier B).
        """
        close_excursion_surface(
            self, excursion_id, closed_at_turn=closed_at_turn
        )

    def active_excursion_character_ids(self) -> set[str]:
        """Union of participants on all active excursions (E_active); read-only."""
        return active_excursion_character_ids_surface(self)

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
        upsert_canon_anchor_surface(self, anchor)

    def seed_character_canon_anchors(self, character_states: dict[str, Any]) -> None:
        """Seed protected canon anchors from current character state data."""
        seed_character_canon_anchors_surface(self, character_states)

    def get_relevant_canon_anchors(
        self,
        character_name: str,
        participants: Optional[list[str]] = None,
        limit: int = 6,
    ) -> list[CanonAnchor]:
        """Return canon anchors most relevant to the named character in this scene."""
        return get_relevant_canon_anchors_surface(
            self, character_name, participants=participants, limit=limit
        )

    def get_scene_canon_anchors(self, limit: int = 10) -> list[CanonAnchor]:
        """Return canon anchors broadly relevant to the current scene."""
        return get_scene_canon_anchors_surface(self, limit)

    def get_active_issues(
        self,
        limit: int = DEFAULT_ACTIVE_ISSUE_LIMIT,
        participants: Optional[list[str]] = None,
        statuses: Optional[list[IssueStatus]] = None,
    ) -> list[IssueState]:
        """Return active issues filtered deterministically by participants and status."""
        return get_active_issues_for_manager(
            self,
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
        return retrieve_public_events_for_manager(
            self,
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
        return retrieve_summary_blocks_for_manager(
            self,
            participants=participants,
            issue_ids=issue_ids,
            location=location,
            limit=limit,
            min_turn_index=min_turn_index,
        )

    def get_resolved_issue_descriptions(self, limit: int = 8) -> list[str]:
        """Return recent resolved issue descriptions for orchestration/UI compatibility."""
        return get_resolved_issue_descriptions_for_manager(self, limit=limit)

    def get_orchestration_context(
        self,
        *,
        active_issue_limit: int = DEFAULT_ACTIVE_ISSUE_LIMIT,
        recent_event_limit: int = DEFAULT_RECENT_EVENT_PROMPT_LIMIT,
        summary_limit: int = DEFAULT_SUMMARY_PROMPT_LIMIT,
    ) -> dict[str, Any]:
        """Return a continuity-owned orchestration view for app prompt assembly."""
        return get_orchestration_context_for_manager(
            self,
            active_issue_limit=active_issue_limit,
            recent_event_limit=recent_event_limit,
            summary_limit=summary_limit,
        )

    def share_event_knowledge(
        self, event_id: str, character_name: str, knowledge_type: str
    ) -> None:
        """Record that a character knows an event by observation, telling, or inference."""
        share_event_knowledge_for_manager(
            self, event_id, character_name, knowledge_type
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
        return mentioned_participants_for_text(text, participants)

    def _propagate_knowledge_from_turn(
        self,
        acting_character: str,
        move: dict[str, Any],
        other_characters: list[str],
    ) -> None:
        propagate_knowledge_from_turn_for_manager(
            self,
            acting_character,
            move,
            other_characters,
            knowledge_share_min_overlap=KNOWLEDGE_SHARE_MIN_OVERLAP,
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
        proposal_authority_context: Optional[ProposalAuthorityContext] = None,
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
        authority_ctx = proposal_authority_context
        if authority_ctx is None:
            authority_ctx = evaluate_proposal_legality(
                move,
                acting_character=acting_character,
                scene_state=self.scene_state.to_dict(),
                active_excursion_character_ids=self.active_excursion_character_ids(),
                excursions=self.excursions,
            )
        if authority_ctx.outcome == ProposalAuthorityOutcome.REJECT:
            raise ContinuityProposalLegalityError(
                authority_ctx.reason_detail or authority_ctx.reason_code or "reject"
            )

        self._active_proposal_authority_context = authority_ctx
        proposal_mutations: list[MutationRequest] = []
        if authority_ctx.outcome == ProposalAuthorityOutcome.ACCEPT:
            proposal_mutations = compile_proposal_excursion_mutations(
                authority_ctx.accepted_proposals,
                acting_character=acting_character,
                excursions=self.excursions,
            )

        resolved_mutations = compose_resolved_mutations(
            move=move,
            director_decision=director_decision,
            scene_state=self.scene_state,
            session_mutation_candidates=session_mutation_candidates,
            proposal_mutation_candidates=proposal_mutations or None,
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
                proposal_authority_context=authority_ctx,
            )
        finally:
            self._continuity_pipeline_turn_active = False
            self._active_proposal_authority_context = None

    def _maybe_create_event(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        timestamp: datetime,
        turn_index: int,
        turn_consequences: dict[str, Any],
    ) -> Optional[PublicEvent]:
        return maybe_create_event_for_manager(
            self,
            acting_character,
            move,
            director_decision,
            timestamp,
            turn_index,
            turn_consequences,
        )

    def _maybe_generate_summary_block(self, timestamp: datetime) -> SummaryBlock | None:
        """Compress older public history into a structured summary block at a fixed interval."""
        return maybe_generate_summary_block_for_manager(self, timestamp)

    def _build_summary_block(
        self, events: list[PublicEvent], generated_at: datetime
    ) -> SummaryBlock:
        """Build a structured summary block from aged-out public events."""
        return build_summary_block_for_manager(self, events, generated_at)

    def _collect_issue_updates(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, str]]:
        """Collect structured issue lifecycle changes within a summary window."""
        return collect_issue_updates_for_manager(self, start_time, end_time)

    def _collect_interpretation_shifts(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, object]]:
        """Collect grouped interpretation changes within a summary window."""
        return collect_interpretation_shifts_for_manager(self, start_time, end_time)

    def get_summary_blocks(
        self, limit: int = DEFAULT_SUMMARY_PROMPT_LIMIT
    ) -> list[SummaryBlock]:
        """Return recent summary blocks for prompt assembly."""
        return get_summary_blocks_for_manager(self, limit=limit)

    def _presence_scratch_from_scene_state(self) -> PresenceAuthorityScratch:
        return presence_scratch_from_scene_state_surface(self)

    def _strip_active_excursions_from_focal_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Enforce P_focal ∩ E_active = ∅ before committing presence."""
        strip_active_excursions_from_focal_scratch_surface(self, scratch)

    def _purge_excursion_participants_from_offstage_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        """Excursion participants must not be soft-offstage (Issue #81 Slice B).

        Clears ``offstage_characters`` and presence-status rows for ``E_active`` in the
        same scratch write as focal stripping — no partial excursion-without-presence-fix.
        """
        purge_excursion_participants_from_offstage_scratch_surface(self, scratch)

    def _resync_presence_through_authority(self) -> None:
        """Full presence pipeline: reconcile → invariant → ensure-one → sync (single writer)."""
        resync_presence_through_authority_surface(self)

    def _synchronize_presence_from_canonical_authority(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        synchronize_presence_from_canonical_authority_surface(self, scratch)

    def apply_pre_turn_user_presence_routing(
        self,
        *,
        trigger_text: str,
        participant_names: list[str],
        get_character_display_name_fn: Callable[[str], str],
        pending_forced_speaker: str | None,
    ) -> None:
        """Apply Traveler offstage hints through the single presence sync path."""
        apply_pre_turn_user_presence_routing_surface(
            self,
            trigger_text=trigger_text,
            participant_names=participant_names,
            get_character_display_name_fn=get_character_display_name_fn,
            pending_forced_speaker=pending_forced_speaker,
        )

    def apply_must_remain_presence_from_fn(
        self, get_must_remain_characters_fn: Callable[[dict[str, Any]], Any]
    ) -> None:
        apply_must_remain_presence_from_fn_surface(self, get_must_remain_characters_fn)

    def bootstrap_present_characters_from_cast(self, character_names: list[str]) -> None:
        """If on-stage roster is empty, seed it from the cast list (restore / init guard)."""
        bootstrap_present_characters_from_cast_surface(self, character_names)

    def _reconcile_presence_lists_scratch(self, scratch: PresenceAuthorityScratch) -> None:
        reconcile_presence_lists_scratch_surface(self, scratch)

    def _apply_canonical_reentry_scratch(
        self, scratch: PresenceAuthorityScratch, character_name: str
    ) -> None:
        apply_canonical_reentry_scratch_surface(self, scratch, character_name)

    def _ensure_at_least_one_present_character_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        ensure_at_least_one_present_character_scratch_surface(self, scratch)

    def _assert_presence_invariant_after_reconcile_scratch(
        self, scratch: PresenceAuthorityScratch
    ) -> None:
        assert_presence_invariant_after_reconcile_scratch_surface(scratch)

    def _reconcile_presence_lists(self) -> None:
        """Drop absent entries that are still present; dedupe both lists (synced write path)."""
        reconcile_presence_lists_surface(self)

    def _ensure_at_least_one_present_character(self) -> None:
        """Deadlock guard via scratch + single sync (see scratch helper for tier rules)."""
        ensure_at_least_one_present_character_surface(self)

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
        maybe_create_issue_for_manager(
            self,
            acting_character,
            move,
            director_decision,
            event,
            timestamp,
            turn_consequences,
        )

    def _update_issues(
        self,
        acting_character: str,
        move: dict[str, Any],
        event: Optional[PublicEvent],
        turn_consequences: dict[str, Any],
    ) -> None:
        """Update issue states based on turn content."""
        update_issues_for_manager(
            self,
            acting_character,
            move,
            event,
            turn_consequences,
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
        update_interpretations_for_manager(
            self,
            acting_character,
            move,
            other_characters,
            timestamp,
        )

    def get_snapshot(self, timestamp: Optional[datetime] = None) -> ContinuitySnapshot:
        """Get a complete snapshot of current continuity state."""
        return get_snapshot_for_manager(
            self, timestamp, self._normalize_timestamp
        )

    def get_character_context(
        self, character_name: str, max_interpretations: int = 5
    ) -> dict[str, Any]:
        """Get layered context for a specific character.

        Returns:
            Dict with scene_state, active_issues, recent_events, and character's interpretations
        """
        return get_character_context_for_manager(
            self,
            character_name,
            max_interpretations=max_interpretations,
            default_active_issue_limit=DEFAULT_ACTIVE_ISSUE_LIMIT,
            default_summary_prompt_limit=DEFAULT_SUMMARY_PROMPT_LIMIT,
        )
