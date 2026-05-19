"""Scene state update orchestration for ContinuityManager (Issue #155 Slice D).

``run_update_scene_state`` preserves the exact step order of ``ContinuityManager._update_scene_state``.
"""

from __future__ import annotations

from typing import Any, Optional

from character_move_adapters import is_canonical_v2_move
from continuity_consequence_classifier_move_tools import (
    move_with_flat_text_for_deterministic_tools,
)
from scene_exit_detection import has_scene_reentry_evidence

from continuity_presence_helpers import align_exit_narrative_with_effective_presence
from continuity_semantic_proposals import (
    ProposalAuthorityOutcome,
    apply_accepted_proposal_presence_to_scratch,
)

# GitHub #232 — reconstruction-era covered commits suppressed (removed #235–#238).
_SUPPRESS_RECONSTRUCTION_COVERED_COMMITS = True
from continuity_state import PublicEvent, ScenePhase, SceneState
from continuity_presence_pipeline import (
    manager_apply_canonical_exit_offstage_transition_scratch,
    manager_apply_canonical_reentry_scratch,
    manager_assert_presence_invariant_after_reconcile_scratch,
    manager_ensure_at_least_one_present_character_scratch,
    manager_presence_scratch_from_scene_state,
    manager_process_structured_reentries_from_move_scratch,
    manager_reconcile_presence_lists_scratch,
    manager_synchronize_presence_from_canonical_authority,
)
from tension_pacing_policy import (
    apply_consequence_up_saturation_gate,
    resolve_hybrid_pacing,
)


def escalate_scene_tension(scene_state: SceneState) -> None:
    """Increase scene tension level."""
    levels = ["low", "moderate", "high", "extreme"]
    current = scene_state.current_tension_level
    if current in levels:
        idx = levels.index(current)
        if idx < len(levels) - 1:
            scene_state.current_tension_level = levels[idx + 1]


def reduce_scene_tension(scene_state: SceneState) -> None:
    """Decrease scene tension level."""
    levels = ["low", "moderate", "high", "extreme"]
    current = scene_state.current_tension_level
    if current in levels:
        idx = levels.index(current)
        if idx > 0:
            scene_state.current_tension_level = levels[idx - 1]


def update_scene_phase_from_tension(scene_state: SceneState) -> None:
    """Update scene phase based on tension and progression."""
    tension = scene_state.current_tension_level
    phase = scene_state.phase

    if phase == ScenePhase.OPENING and tension in ["moderate", "high"]:
        scene_state.phase = ScenePhase.RISING
    elif phase == ScenePhase.RISING and tension == "extreme":
        scene_state.phase = ScenePhase.CLIMAX
    elif phase == ScenePhase.CLIMAX and tension in ["low", "moderate"]:
        scene_state.phase = ScenePhase.FALLING


def manager_align_exit_narrative_with_effective_presence(
    manager: Any,
    acting_character: str,
    turn_consequences: dict[str, Any],
) -> None:
    if manager.scene_state is None:
        return
    align_exit_narrative_with_effective_presence(
        present_characters=list(manager.scene_state.present_characters or []),
        acting_character=acting_character,
        turn_consequences=turn_consequences,
    )


def run_update_scene_state(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    event: Optional[PublicEvent],
    turn_consequences: dict[str, Any],
) -> None:
    """Update scene state based on director decisions and flow (façade: ``_update_scene_state``)."""
    if manager.scene_state is None:
        return

    tension_shift_raw = ""
    if isinstance(director_decision, dict):
        tension_shift_raw = str(
            director_decision.get("tension_shift", "") or ""
        ).strip()

    environment_event = (
        director_decision.get("environment_event", "")
        if isinstance(director_decision, dict)
        else ""
    )
    consequence_tags: set[str] = {
        str(item) for item in turn_consequences.get("tags", []) if str(item).strip()
    }

    pacing_source, pacing_direction, director_neutral = resolve_hybrid_pacing(
        director_decision=director_decision if isinstance(director_decision, dict) else {},
        turn_consequences=turn_consequences if isinstance(turn_consequences, dict) else {},
    )
    pacing_source, pacing_direction, suppressed_consequence_up = (
        apply_consequence_up_saturation_gate(
            pacing_source=pacing_source,
            pacing_direction=pacing_direction,
            current_tension_level=manager.scene_state.current_tension_level,
        )
    )
    if pacing_direction == "up":
        escalate_scene_tension(manager.scene_state)
    elif pacing_direction == "down":
        reduce_scene_tension(manager.scene_state)
    hybrid_meta: dict[str, Any] = {
        "pacing_source": pacing_source,
        "pacing_direction": pacing_direction,
        "director_neutral": director_neutral,
    }
    if suppressed_consequence_up:
        hybrid_meta["consequence_up_suppressed_saturation"] = True
    turn_consequences["hybrid_pacing"] = hybrid_meta

    if environment_event:
        manager.scene_state.recent_environment_events.append(environment_event)
        manager.scene_state.recent_environment_events = (
            manager.scene_state.recent_environment_events[-5:]
        )
        manager.scene_state.environment_description = environment_event

    scratch = manager_presence_scratch_from_scene_state(manager)
    proposal_ctx = getattr(manager, "_active_proposal_authority_context", None)
    if (
        proposal_ctx is not None
        and proposal_ctx.outcome == ProposalAuthorityOutcome.ACCEPT
    ):
        apply_accepted_proposal_presence_to_scratch(
            scratch,
            proposal_ctx.accepted_proposals,
            acting_character=acting_character,
        )

    if not _SUPPRESS_RECONSTRUCTION_COVERED_COMMITS:
        manager_process_structured_reentries_from_move_scratch(manager, move, scratch)

        move_for_reentry = (
            move_with_flat_text_for_deterministic_tools(move)
            if is_canonical_v2_move(move)
            else move
        )
        if has_scene_reentry_evidence(move_for_reentry):
            manager_apply_canonical_reentry_scratch(manager, scratch, acting_character)

        if "entry" in consequence_tags:
            manager_apply_canonical_reentry_scratch(manager, scratch, acting_character)

        scene_dict = manager.scene_state.to_dict()
        scene_dict["present_characters"] = list(scratch.present_characters)
        scene_dict["offstage_characters"] = list(scratch.offstage_characters)
        scene_dict["character_presence_status"] = dict(scratch.character_presence_status)
        scene_dict["absent_but_relevant"] = list(scratch.absent_but_relevant)
        must_remain_actor = (
            str(
                (manager.scene_state.character_presence_constraints or {}).get(
                    acting_character, ""
                )
                or ""
            ).strip()
            == "must_remain"
        )

        manager_apply_canonical_exit_offstage_transition_scratch(
            manager,
            acting_character,
            move,
            consequence_tags=consequence_tags,
            scene_dict=scene_dict,
            scratch=scratch,
            should_skip_soft_exit_presence_removal=manager._should_skip_soft_exit_presence_removal,
        )
    else:
        must_remain_actor = (
            str(
                (manager.scene_state.character_presence_constraints or {}).get(
                    acting_character, ""
                )
                or ""
            ).strip()
            == "must_remain"
        )

    update_scene_phase_from_tension(manager.scene_state)

    manager_reconcile_presence_lists_scratch(manager, scratch)
    manager_assert_presence_invariant_after_reconcile_scratch(scratch)
    exclude_same_beat: str | None = None
    if must_remain_actor:
        st_after = str(
            scratch.character_presence_status.get(acting_character, "") or ""
        ).strip()
        if (
            st_after == "temporary_offstage"
            and acting_character not in scratch.present_characters
        ):
            exclude_same_beat = acting_character
    manager_ensure_at_least_one_present_character_scratch(
        manager, scratch, exclude_same_beat_reentry_for=exclude_same_beat
    )
    manager_synchronize_presence_from_canonical_authority(manager, scratch)

    manager_align_exit_narrative_with_effective_presence(
        manager, acting_character, turn_consequences
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
    manager.scene_state.recent_delta = (
        consequence_delta
        or (event.summary if event else "")
        or environment_event
        or tension_shift_raw
        or str(move.get("action", "character action"))
    )
