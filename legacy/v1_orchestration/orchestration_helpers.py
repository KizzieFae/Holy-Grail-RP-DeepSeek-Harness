"""Orchestration helpers: continuity mirror, turn-selection policy, bounded histories, narrator context.

Director addressee string resolution lives outside this module. Public surfaces here affect
``next_actor`` / orchestration cache (continuation, fairness, progression override, fallback chooser)
and ``orchestration_state`` shape — not character move validation.

Mechanical split (Issue #164): implementations live in sibling modules; this file is a thin façade.
"""

from orchestration_continuity_mirror import sync_orchestration_state_from_continuity
from orchestration_continuation import resolve_continuation_override_actor
from orchestration_progression import (
    _pick_high_progression_actor,
    assign_progression_band_for_actor,
    resolve_progression_override_actor,
)
from orchestration_scene_context import build_recent_scene_context
from orchestration_spotlight import (
    apply_participation_fairness_to_decision,
    choose_fallback_actor,
    first_unheard_available_actor_this_round,
)
from orchestration_state_init import (
    build_default_orchestration_state,
    ensure_orchestration_state,
)
from orchestration_turn_append import append_turn_to_orchestration_state
