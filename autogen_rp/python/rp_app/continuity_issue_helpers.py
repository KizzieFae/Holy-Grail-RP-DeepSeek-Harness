"""Facade for continuity issue helpers (Issue #157 / Phase 3D).

Splits live in ``continuity_issue_*`` modules; this module preserves historical
``from continuity_issue_helpers import …`` and ``patch("continuity_issue_helpers.…")`` paths.
"""

from __future__ import annotations

from continuity_issue_lexicon import event_tokens, issue_tokens, turn_tokens
from continuity_issue_lifecycle import maybe_create_issue, update_issues
from continuity_issue_matching import (
    _matches_issue_signals,
    _pressure_match_score,
    find_matching_issue,
    link_issue_interactions,
    merge_issue_terms,
)
from continuity_issue_pressure import _build_turn_pressure_profile
from continuity_issue_retrieval import (
    get_active_issues,
    get_resolved_issue_descriptions,
    retrieve_public_events,
    retrieve_summary_blocks,
)
from continuity_issue_transitions import (
    REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE,
    REQUIRED_NEXT_STEP_PLATEAU_FIRE_STREAK,
    _PLATEAU_COUNTED_TRANSITIONS,
    _normalize_required_next_step_key,
    apply_mixed_transition_plateau_refresh,
    _build_status_reason,
    _determine_issue_transition,
    _should_resolve_issue,
)

__all__ = [
    "REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE",
    "REQUIRED_NEXT_STEP_PLATEAU_FIRE_STREAK",
    "_PLATEAU_COUNTED_TRANSITIONS",
    "_normalize_required_next_step_key",
    "apply_mixed_transition_plateau_refresh",
    "event_tokens",
    "find_matching_issue",
    "get_active_issues",
    "get_resolved_issue_descriptions",
    "issue_tokens",
    "link_issue_interactions",
    "maybe_create_issue",
    "merge_issue_terms",
    "retrieve_public_events",
    "retrieve_summary_blocks",
    "turn_tokens",
    "update_issues",
    "_build_status_reason",
    "_build_turn_pressure_profile",
    "_determine_issue_transition",
    "_matches_issue_signals",
    "_pressure_match_score",
    "_should_resolve_issue",
]
