"""Issue #81 — continuity mutation pipeline (spatial + excursion lifecycle)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


from continuity_manager import ContinuityManager
from continuity_mutation_pipeline import (
    CanonicalAtom,
    ContinuityMutationError,
    ContinuityMutationType,
    MutationRequest,
    MutationResolutionKey,
    MutationSourceClass,
    apply_resolved_mutations,
    compose_resolved_mutations,
    extract_m_spatial_candidates,
    validate_excursion_lifecycle_move_shape,
    validate_spatial_transition_move_shape,
    validate_resolved_mutations_globally,
)
from continuity_setup_seam_v77 import finalize_continuity_setup_seam
from continuity_state import ExcursionStatus
from response_validation import validate_bot_response


def _minimal_move_for_spatial_validation(**spatial: object) -> dict:
    m: dict = {
        "action": "steps forward",
        "dialogue": "Hello.",
        "motivation": {
            "goal": "test",
            "tactic": "test",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }
    for k, v in spatial.items():
        m[k] = v
    return m


def _fresh_manager_dorm() -> ContinuityManager:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="o",
        present_characters=["A", "B"],
    )
    assert mgr.scene_state is not None
    mgr.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    finalize_continuity_setup_seam(mgr, cast=["A", "B"])
    return mgr


def _loc() -> MutationResolutionKey:
    return MutationResolutionKey.for_location()


def test_extract_m_spatial_empty_when_absent() -> None:
    assert extract_m_spatial_candidates({"action": "x", "dialogue": "", "motivation": {}}) == []


def test_compose_m_sets_location_payload() -> None:
    move = {
        "action": "walks out",
        "dialogue": "",
        "motivation": {},
        "spatial_transition": {"location": "  Hallway  "},
    }
    resolved = compose_resolved_mutations(
        move=move,
        director_decision={},
        scene_state=None,
        session_mutation_candidates=None,
    )
    lk = _loc()
    assert lk in resolved
    assert resolved[lk].payload["location"] == "Hallway"
    assert resolved[lk].source == MutationSourceClass.M


def test_precedence_session_beats_move() -> None:
    move = {
        "action": "x",
        "dialogue": "",
        "motivation": {},
        "spatial_transition": {"location": "FromMove"},
    }
    session = [
        MutationRequest(
            mutation_type=ContinuityMutationType.SPATIAL_TRANSITION,
            atom=CanonicalAtom.LOCATION,
            source=MutationSourceClass.S,
            payload={"location": "FromSession"},
        )
    ]
    resolved = compose_resolved_mutations(
        move=move,
        director_decision={},
        scene_state=None,
        session_mutation_candidates=session,
    )
    lk = _loc()
    assert resolved[lk].payload["location"] == "FromSession"
    assert resolved[lk].source == MutationSourceClass.S


def test_duplicate_same_source_rejected() -> None:
    move = {
        "spatial_transition": {"location": "A"},
        "action": "",
        "dialogue": "",
        "motivation": {},
    }
    two_m = [
        MutationRequest(
            mutation_type=ContinuityMutationType.SPATIAL_TRANSITION,
            atom=CanonicalAtom.LOCATION,
            source=MutationSourceClass.M,
            payload={"location": "X"},
        ),
        MutationRequest(
            mutation_type=ContinuityMutationType.SPATIAL_TRANSITION,
            atom=CanonicalAtom.LOCATION,
            source=MutationSourceClass.M,
            payload={"location": "Y"},
        ),
    ]
    with pytest.raises(ContinuityMutationError, match="multiple"):
        compose_resolved_mutations(
            move=move,
            director_decision={},
            scene_state=None,
            session_mutation_candidates=two_m,
        )


def test_invalid_spatial_transition_shape() -> None:
    ok, msg = validate_spatial_transition_move_shape(
        {"spatial_transition": "not-a-dict", "action": "", "dialogue": "", "motivation": {}}
    )
    assert not ok
    assert "[SPATIAL_TRANSITION]" in msg


def test_process_turn_updates_location_after_finalize() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="Dorm",
        opening_description="o",
        present_characters=["A", "B"],
    )
    assert m.scene_state is not None
    m.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    finalize_continuity_setup_seam(m, cast=["A", "B"])

    m.process_turn(
        acting_character="A",
        move={
            "action": "leaves",
            "dialogue": "",
            "motivation": {},
            "spatial_transition": {"location": "Corridor"},
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert m.scene_state.location == "Corridor"
    meta = m.turn_metadata_by_index.get(m.turn_counter, {})
    assert "continuity_mutation_resolution" in meta
    assert meta["continuity_mutation_resolution"]["location"]["source"] == "M"


def test_apply_resolved_mutations_only_location_atom() -> None:
    from continuity_state import SceneState

    ss = SceneState(location="Old")
    resolved = {
        MutationResolutionKey.for_location(): MutationRequest(
            mutation_type=ContinuityMutationType.SPATIAL_TRANSITION,
            atom=CanonicalAtom.LOCATION,
            source=MutationSourceClass.M,
            payload={"location": "New"},
        )
    }
    validate_resolved_mutations_globally(resolved, ss, "A", continuity_manager=None)
    apply_resolved_mutations(
        resolved,
        scene_state=ss,
        continuity_manager=None,
        commit_turn_index=None,
    )
    assert ss.location == "New"


def test_validate_bot_response_rejects_spatial_missing_location() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation(spatial_transition={})
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert reason.startswith("[SPATIAL_TRANSITION]")
    assert mgr.scene_state is not None
    assert mgr.scene_state.location == "Dorm"
    assert mgr.turn_counter == 0


def test_validate_bot_response_rejects_spatial_empty_location() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation(
        spatial_transition={"location": "   "},
    )
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert "[SPATIAL_TRANSITION]" in reason
    assert mgr.scene_state.location == "Dorm"
    assert mgr.turn_counter == 0


def test_validate_bot_response_rejects_spatial_overlong_location() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation(
        spatial_transition={"location": "x" * 501},
    )
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert "[SPATIAL_TRANSITION]" in reason
    assert mgr.scene_state.location == "Dorm"
    assert mgr.turn_counter == 0


def test_validate_bot_response_rejects_spatial_non_string_location() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation(
        spatial_transition={"location": 42},
    )
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert "[SPATIAL_TRANSITION]" in reason
    assert "string" in reason.lower()
    assert mgr.scene_state.location == "Dorm"
    assert mgr.turn_counter == 0


def test_process_turn_invalid_spatial_raises_no_commit() -> None:
    mgr = _fresh_manager_dorm()
    with pytest.raises(ContinuityMutationError):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "x",
                "dialogue": "",
                "motivation": {},
                "spatial_transition": {"location": 99},
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )
    assert mgr.scene_state is not None
    assert mgr.scene_state.location == "Dorm"
    assert mgr.turn_counter == 0


def test_compose_excursion_open_m() -> None:
    move = {
        "action": "x",
        "dialogue": "",
        "motivation": {},
        "excursion_lifecycle": {
            "operation": "open",
            "participant_character_ids": ["A", "B"],
        },
    }
    resolved = compose_resolved_mutations(
        move=move,
        director_decision={},
        scene_state=None,
        session_mutation_candidates=None,
    )
    pk = MutationResolutionKey.for_excursion_scope("__pending_open__")
    assert pk in resolved
    assert resolved[pk].mutation_type == ContinuityMutationType.EXCURSION_OPEN
    assert resolved[pk].payload["participant_character_ids"] == ["A", "B"]


def test_process_turn_opens_excursion_and_audit() -> None:
    mgr = _fresh_manager_dorm()
    anchor = mgr.anchor_character_id
    assert anchor
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex1",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert "ex1" in mgr.excursions
    rec = mgr.excursions["ex1"]
    assert rec.status == ExcursionStatus.ACTIVE
    assert rec.opened_at_turn == 1
    assert rec.closed_at_turn is None
    e_active = mgr.active_excursion_character_ids()
    assert e_active == {"B"}
    assert anchor not in e_active
    present = set(mgr.scene_state.present_characters or [])
    assert not (present & e_active)
    assert anchor in present
    meta = mgr.turn_metadata_by_index.get(1, {})
    assert "excursion_lifecycle:ex1" in meta["continuity_mutation_resolution"]


def test_process_turn_closes_excursion_records_turn_and_clears_e_active() -> None:
    mgr = _fresh_manager_dorm()
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "open",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_close",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert mgr.turn_counter == 1
    assert mgr.active_excursion_character_ids() == {"B"}

    mgr.process_turn(
        acting_character="A",
        move={
            "action": "close",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_close",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert mgr.turn_counter == 2
    closed = mgr.excursions["ex_close"]
    assert closed.status == ExcursionStatus.CLOSED
    assert closed.closed_at_turn == 2
    assert mgr.active_excursion_character_ids() == set()
    present = set(mgr.scene_state.present_characters or [])
    assert not (present & mgr.active_excursion_character_ids())
    meta_close = mgr.turn_metadata_by_index.get(2, {})
    assert (
        meta_close["continuity_mutation_resolution"]["excursion_lifecycle:ex_close"][
            "mutation_type"
        ]
        == "EXCURSION_CLOSE"
    )


def test_process_turn_close_excursion_idempotent_apply_preserves_first_close_turn() -> None:
    """Second close in a later turn is a no-op at the record level (defensive close_excursion)."""
    mgr = _fresh_manager_dorm()
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "open",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_idem",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c1",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_idem",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    first_closed_at = mgr.excursions["ex_idem"].closed_at_turn
    assert first_closed_at == 2

    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c2",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_idem",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert mgr.excursions["ex_idem"].status == ExcursionStatus.CLOSED
    assert mgr.excursions["ex_idem"].closed_at_turn == first_closed_at


def test_process_turn_excursion_clears_soft_offstage_for_participants() -> None:
    """Opening an excursion clears soft-offstage rows for participants in the same sync."""
    mgr = _fresh_manager_dorm()
    anchor = mgr.anchor_character_id or "A"
    assert anchor
    mgr.scene_state.present_characters = [anchor]
    mgr.scene_state.offstage_characters = ["B"]
    mgr.scene_state.character_presence_status["B"] = "temporary_offstage"

    mgr.process_turn(
        acting_character=anchor,
        move={
            "action": "branch",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_off",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    e_active = mgr.active_excursion_character_ids()
    assert "B" in e_active
    assert anchor not in e_active
    present = set(mgr.scene_state.present_characters or [])
    assert not (present & e_active)
    off = list(mgr.scene_state.offstage_characters or [])
    assert "B" not in off
    assert "B" not in (mgr.scene_state.character_presence_status or {})
    assert (
        str(mgr.scene_state.character_presence_status.get("B", "") or "").strip()
        != "temporary_offstage"
    )


def test_excursion_rejects_anchor_participant() -> None:
    mgr = _fresh_manager_dorm()
    assert mgr.anchor_character_id
    with pytest.raises(ContinuityMutationError, match="anchor"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "x",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "open",
                    "excursion_id": "ex_anchor",
                    "participant_character_ids": [mgr.anchor_character_id or ""],
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )


def test_excursion_rejects_second_active_membership() -> None:
    mgr = _fresh_manager_dorm()
    mgr.open_excursion(participant_character_ids=["B"], excursion_id="e0")
    with pytest.raises(ContinuityMutationError, match="conflicts"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "x",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "open",
                    "excursion_id": "e1",
                    "participant_character_ids": ["B"],
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )


def test_validate_bot_response_rejects_excursion_bad_operation() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation()
    move["excursion_lifecycle"] = {"operation": "reintegrate", "excursion_id": "x"}
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert "[EXCURSION_LIFECYCLE]" in reason


def test_validate_excursion_close_shape() -> None:
    ok, msg = validate_excursion_lifecycle_move_shape(
        {
            "excursion_lifecycle": {"operation": "close", "excursion_id": "  z  "},
            "action": "",
            "dialogue": "",
            "motivation": {},
        }
    )
    assert ok and msg == ""


def test_precedence_session_beats_move_excursion() -> None:
    move = {
        "action": "x",
        "dialogue": "",
        "motivation": {},
        "excursion_lifecycle": {
            "operation": "close",
            "excursion_id": "exs",
        },
    }
    session = [
        MutationRequest(
            mutation_type=ContinuityMutationType.EXCURSION_OPEN,
            atom=CanonicalAtom.EXCURSION_LIFECYCLE,
            source=MutationSourceClass.S,
            payload={
                "operation": "open",
                "excursion_id": "exs",
                "participant_character_ids": ["A"],
            },
        )
    ]
    resolved = compose_resolved_mutations(
        move=move,
        director_decision={},
        scene_state=None,
        session_mutation_candidates=session,
    )
    k = MutationResolutionKey.for_excursion_scope("exs")
    assert resolved[k].source == MutationSourceClass.S
    assert resolved[k].mutation_type == ContinuityMutationType.EXCURSION_OPEN


class _FailOnAppendList(list):
    """List that raises on append (failure injection for Slice C rollback tests)."""

    def __init__(self, *args: object, reason: str = "injected_append_failure") -> None:
        super().__init__(*args)
        self._reason = reason

    def append(self, item: object) -> None:  # type: ignore[override]
        raise RuntimeError(self._reason)


class _FailSetItemIssueDict(dict):
    """Dict that raises on __setitem__ for a specific key (issue create injection)."""

    def __init__(self, *args: object, fail_key: str, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._fail_key = fail_key

    def __setitem__(self, key: object, value: object) -> None:
        if key == self._fail_key:
            raise RuntimeError("injected_issue_setitem_failure")
        super().__setitem__(key, value)


def _snapshot_slice_c_durable_state(
    mgr: ContinuityManager, excursion_id: str
) -> dict:
    rec = mgr.excursions[excursion_id]
    ss = mgr.scene_state
    assert ss is not None
    return {
        "turn_counter": mgr.turn_counter,
        "public_event_ids": [e.event_id for e in mgr.public_events],
        "resolved_outcome_ids": [o.outcome_id for o in mgr.resolved_outcomes],
        "issue_ids": sorted(mgr.issues.keys()),
        "issues_payload": {k: mgr.issues[k].to_dict() for k in sorted(mgr.issues)},
        "active_issue_ids": list(ss.active_issue_ids),
        "excursion_status": rec.status,
        "closed_at_turn": rec.closed_at_turn,
        "reintegration_commit_id_applied": rec.reintegration_commit_id_applied,
        "present_characters": list(ss.present_characters),
        "offstage_characters": list(ss.offstage_characters),
        "character_presence_status": dict(ss.character_presence_status),
        "e_active": frozenset(mgr.active_excursion_character_ids()),
    }


def _reint_block(
    *,
    commit_id: str = "reint_commit_v1",
    events: list | None = None,
    issues: list | None = None,
    outcomes: list | None = None,
) -> dict:
    return {
        "reintegration_commit_id": commit_id,
        "events": events or [],
        "issues": issues or [],
        "resolved_outcomes": outcomes or [],
    }


def test_slice_c_close_reintegration_applies_event_and_identity() -> None:
    mgr = _fresh_manager_dorm()
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "open ex",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_r1",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "close",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_r1",
                "reintegration": _reint_block(
                    commit_id="cid_slice_c_1",
                    events=[
                        {
                            "summary": "Excursion thread resolved",
                            "participants": ["B"],
                        }
                    ],
                ),
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    rec = mgr.excursions["ex_r1"]
    assert rec.reintegration_commit_id_applied == "cid_slice_c_1"
    assert len(mgr.public_events) == 1
    assert mgr.public_events[0].summary == "Excursion thread resolved"


def test_slice_c_same_reintegration_commit_id_idempotent() -> None:
    mgr = _fresh_manager_dorm()
    close_move = {
        "action": "close",
        "dialogue": "",
        "motivation": {},
        "excursion_lifecycle": {
            "operation": "close",
            "excursion_id": "ex_idem_r",
            "reintegration": _reint_block(
                commit_id="same_cid",
                events=[
                    {"summary": "Once", "participants": ["B"]},
                ],
            ),
        },
    }
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_idem_r",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move=close_move,
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    n_after_first = len(mgr.public_events)
    mgr.process_turn(
        acting_character="A",
        move=close_move,
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert len(mgr.public_events) == n_after_first


def test_slice_c_different_reintegration_commit_id_rejected() -> None:
    mgr = _fresh_manager_dorm()
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_conflict",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_conflict",
                "reintegration": _reint_block(
                    commit_id="first_id",
                    events=[{"summary": "S", "participants": ["B"]}],
                ),
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    with pytest.raises(ContinuityMutationError, match="conflicts"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "c2",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "close",
                    "excursion_id": "ex_conflict",
                    "reintegration": _reint_block(
                        commit_id="second_id",
                        events=[{"summary": "S2", "participants": ["B"]}],
                    ),
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )


def test_slice_c_reintegration_only_on_close_operation() -> None:
    mgr = _fresh_manager_dorm()
    move = _minimal_move_for_spatial_validation()
    move["excursion_lifecycle"] = {
        "operation": "open",
        "excursion_id": "x",
        "participant_character_ids": ["B"],
        "reintegration": _reint_block(),
    }
    is_valid, reason = validate_bot_response(
        content=f"{move['action']} {move['dialogue']}",
        speaker="A",
        user_name="U",
        chat_history=[],
        move=move,
    )
    assert is_valid is False
    assert "[REINTEGRATION]" in reason or "only allowed" in reason.lower()


def test_slice_c_reintegration_issue_and_outcome_merge() -> None:
    mgr = _fresh_manager_dorm()
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_full",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex_full",
                "reintegration": _reint_block(
                    commit_id="cid_full",
                    events=[],
                    issues=[
                        {
                            "operation": "create",
                            "issue_id": "issue_reint_1",
                            "description": "Pressure from excursion",
                            "participants": ["B"],
                        }
                    ],
                    outcomes=[
                        {
                            "outcome_id": "out_reint_1",
                            "category": "assignment",
                            "key": "sleeping_surface",
                            "subject_id": "B",
                            "value": {"assignee_id": "B", "surface_id": "cot"},
                            "aspect_id": "lodging.sleep_surface",
                            "slot_key": "lodging.sleep_surface::B",
                        }
                    ],
                ),
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert "issue_reint_1" in mgr.issues
    assert any(o.outcome_id == "out_reint_1" for o in mgr.resolved_outcomes)


def test_slice_c_rollback_restores_state_when_event_append_fails() -> None:
    mgr = _fresh_manager_dorm()
    eid = "ex_rb_evt"
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": eid,
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    snap = _snapshot_slice_c_durable_state(mgr, eid)
    tc = mgr.turn_counter
    mgr.public_events = _FailOnAppendList(list(mgr.public_events))
    with pytest.raises(RuntimeError, match="injected_append_failure"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "c",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "close",
                    "excursion_id": eid,
                    "reintegration": _reint_block(
                        commit_id="cid_rb_evt",
                        events=[{"summary": "x", "participants": ["B"]}],
                    ),
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )
    assert _snapshot_slice_c_durable_state(mgr, eid) == snap
    assert mgr.turn_counter == tc


def test_slice_c_rollback_restores_state_when_issue_create_fails() -> None:
    mgr = _fresh_manager_dorm()
    eid = "ex_rb_iss"
    inj_key = "issue_rb_inj"
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": eid,
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    snap = _snapshot_slice_c_durable_state(mgr, eid)
    tc = mgr.turn_counter
    mgr.issues = _FailSetItemIssueDict(dict(mgr.issues), fail_key=inj_key)
    with pytest.raises(RuntimeError, match="injected_issue_setitem_failure"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "c",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "close",
                    "excursion_id": eid,
                    "reintegration": _reint_block(
                        commit_id="cid_rb_iss",
                        events=[],
                        issues=[
                            {
                                "operation": "create",
                                "issue_id": inj_key,
                                "description": "d",
                                "participants": ["B"],
                            }
                        ],
                    ),
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )
    assert inj_key not in mgr.issues
    assert _snapshot_slice_c_durable_state(mgr, eid) == snap
    assert mgr.turn_counter == tc


def test_slice_c_rollback_restores_state_when_outcome_append_fails() -> None:
    mgr = _fresh_manager_dorm()
    eid = "ex_rb_out"
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": eid,
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    snap = _snapshot_slice_c_durable_state(mgr, eid)
    tc = mgr.turn_counter
    mgr.resolved_outcomes = _FailOnAppendList(
        list(mgr.resolved_outcomes), reason="injected_outcome_failure"
    )
    with pytest.raises(RuntimeError, match="injected_outcome_failure"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "c",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "close",
                    "excursion_id": eid,
                    "reintegration": _reint_block(
                        commit_id="cid_rb_out",
                        events=[],
                        outcomes=[
                            {
                                "outcome_id": "out_rb_inj",
                                "category": "assignment",
                                "key": "sleeping_surface",
                                "subject_id": "B",
                                "value": {"assignee_id": "B", "surface_id": "cot"},
                                "aspect_id": "lodging.sleep_surface",
                                "slot_key": "lodging.sleep_surface::B",
                            }
                        ],
                    ),
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )
    assert _snapshot_slice_c_durable_state(mgr, eid) == snap
    assert mgr.turn_counter == tc


def test_slice_c_process_turn_post_close_presence_and_invariants() -> None:
    mgr = _fresh_manager_dorm()
    anchor = mgr.anchor_character_id
    assert anchor
    eid = "ex_post_close"
    mgr.scene_state.present_characters = [anchor]
    mgr.scene_state.offstage_characters = ["B"]
    mgr.scene_state.character_presence_status["B"] = "temporary_offstage"

    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": eid,
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": eid,
                "reintegration": _reint_block(
                    commit_id="cid_post",
                    events=[{"summary": "merged", "participants": ["B"]}],
                ),
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    rec = mgr.excursions[eid]
    assert rec.status == ExcursionStatus.CLOSED
    assert rec.closed_at_turn == mgr.turn_counter
    assert rec.reintegration_commit_id_applied == "cid_post"
    assert mgr.active_excursion_character_ids() == set()
    assert "B" not in (mgr.scene_state.offstage_characters or [])
    assert (
        str(mgr.scene_state.character_presence_status.get("B", "") or "").strip()
        != "temporary_offstage"
    )
    present = set(mgr.scene_state.present_characters or [])
    assert "B" in present
    assert not (present & mgr.active_excursion_character_ids())


def test_slice_c_late_merge_after_close_without_reintegration() -> None:
    mgr = _fresh_manager_dorm()
    eid = "ex_late_merge"
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "o",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": eid,
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    mgr.process_turn(
        acting_character="A",
        move={
            "action": "c0",
            "dialogue": "",
            "motivation": {},
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": eid,
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    rec = mgr.excursions[eid]
    assert rec.status == ExcursionStatus.CLOSED
    assert rec.reintegration_commit_id_applied is None

    merge_move = {
        "action": "c1",
        "dialogue": "",
        "motivation": {},
        "excursion_lifecycle": {
            "operation": "close",
            "excursion_id": eid,
            "reintegration": _reint_block(
                commit_id="cid_late_1",
                events=[{"summary": "late merge", "participants": ["B"]}],
            ),
        },
    }
    n_ev_before = len(mgr.public_events)
    mgr.process_turn(
        acting_character="A",
        move=merge_move,
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert rec.reintegration_commit_id_applied == "cid_late_1"
    assert len(mgr.public_events) == n_ev_before + 1
    assert mgr.public_events[-1].summary == "late merge"

    mgr.process_turn(
        acting_character="A",
        move=merge_move,
        director_decision={"next_actor": "B"},
        other_characters=["B"],
    )
    assert len(mgr.public_events) == n_ev_before + 1

    with pytest.raises(ContinuityMutationError, match="conflicts"):
        mgr.process_turn(
            acting_character="A",
            move={
                "action": "c2",
                "dialogue": "",
                "motivation": {},
                "excursion_lifecycle": {
                    "operation": "close",
                    "excursion_id": eid,
                    "reintegration": _reint_block(
                        commit_id="cid_late_2",
                        events=[{"summary": "nope", "participants": ["B"]}],
                    ),
                },
            },
            director_decision={"next_actor": "B"},
            other_characters=["B"],
        )
