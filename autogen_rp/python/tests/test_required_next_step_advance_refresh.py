"""Tests for mixed-transition plateau refresh on ``required_next_step``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_issue_helpers import (  # noqa: E402
    REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE,
    apply_mixed_transition_plateau_refresh,
    update_issues,
    issue_tokens,
    link_issue_interactions,
    merge_issue_terms,
    turn_tokens,
)
from continuity_manager import ISSUE_TOKEN_STOPWORDS, ContinuityManager  # noqa: E402
from continuity_state import IssueState, IssueStatus  # noqa: E402


def _minimal_move() -> dict:
    return {
        "action": "holds position",
        "dialogue": "Still here.",
        "motivation": {"goal": "maintain standoff", "tactic": "wait"},
    }


def _plateau_turn_profile(*, required_next_step: str) -> dict:
    return {
        "pressure_kind": "control_conflict",
        "blocked_what": "Control of the corridor",
        "blocked_characters": ["Alice"],
        "last_change": "Alice holds the line",
        "required_next_step": required_next_step,
        "description": "Control of the corridor. Required next move: hold.",
        "participants": ["Alice"],
        "should_track": True,
        "source_text": "hold line corridor",
    }


def test_escalated_escalated_same_norm_no_refresh_without_advanced() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Same obligation.",
    )
    tp = _plateau_turn_profile(required_next_step="Same obligation.")
    issue.required_next_step = tp["required_next_step"]

    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="escalated", turn_profile=tp, current_turn_index=1
    )
    assert issue.required_next_step_plateau_streak == 1
    assert issue.required_next_step_plateau_has_advanced is False
    assert issue.required_next_step == "Same obligation."

    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="escalated", turn_profile=tp, current_turn_index=2
    )
    assert issue.required_next_step_plateau_streak == 2
    assert issue.required_next_step_plateau_has_advanced is False
    assert issue.required_next_step == "Same obligation."


def test_advanced_escalated_same_norm_refreshes() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Same obligation.",
    )
    tp = _plateau_turn_profile(required_next_step="Same obligation.")
    issue.required_next_step = tp["required_next_step"]

    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=1
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="escalated", turn_profile=tp, current_turn_index=2
    )
    assert issue.required_next_step == REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE
    assert issue.required_next_step_plateau_streak == 0
    assert issue.required_next_step_plateau_has_advanced is False


def test_escalated_then_advanced_same_norm_refreshes() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Same obligation.",
    )
    tp = _plateau_turn_profile(required_next_step="Same obligation.")
    issue.required_next_step = tp["required_next_step"]

    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="escalated", turn_profile=tp, current_turn_index=1
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=2
    )
    assert issue.required_next_step == REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE


def test_repeated_advanced_refreshes() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Same obligation text every beat.",
    )
    tp = _plateau_turn_profile(required_next_step="Same obligation text every beat.")
    issue.required_next_step = tp["required_next_step"]

    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=1
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=2
    )
    assert issue.required_next_step == REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE


def test_norm_change_resets_streak_to_one() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="First step",
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue,
        transition="advanced",
        turn_profile=_plateau_turn_profile(required_next_step="First step"),
        current_turn_index=1,
    )
    assert issue.required_next_step_plateau_streak == 1

    issue.required_next_step = "Second different step"
    apply_mixed_transition_plateau_refresh(
        issue=issue,
        transition="advanced",
        turn_profile=_plateau_turn_profile(required_next_step="Second different step"),
        current_turn_index=2,
    )
    assert issue.required_next_step == "Second different step"
    assert issue.required_next_step_plateau_streak == 1


def test_non_consecutive_counted_resets_streak_to_one() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Hold.",
    )
    tp = _plateau_turn_profile(required_next_step="Hold.")
    issue.required_next_step = tp["required_next_step"]
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=1
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp, current_turn_index=5
    )
    assert issue.required_next_step_plateau_streak == 1
    assert issue.required_next_step == "Hold."


def test_non_counted_transition_resets_streak_zero() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="X",
        required_next_step_plateau_streak=2,
        required_next_step_plateau_last_norm="x",
        required_next_step_plateau_last_turn_index=2,
        required_next_step_plateau_has_advanced=True,
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue,
        transition="narrowed",
        turn_profile=_plateau_turn_profile(required_next_step="X"),
        current_turn_index=3,
    )
    assert issue.required_next_step_plateau_streak == 0
    assert issue.required_next_step_plateau_has_advanced is False


def test_refresh_uses_template_when_turn_profile_matches_stale() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Stale obligation.",
    )
    tp_same = _plateau_turn_profile(required_next_step="Stale obligation.")
    issue.required_next_step = tp_same["required_next_step"]
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp_same, current_turn_index=1
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="advanced", turn_profile=tp_same, current_turn_index=2
    )
    assert issue.required_next_step == REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE


def test_refresh_uses_turn_derived_when_fresh_differs_from_stale() -> None:
    issue = IssueState(
        issue_id="i1",
        description="Test",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Stale obligation.",
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue,
        transition="advanced",
        turn_profile=_plateau_turn_profile(required_next_step="Stale obligation."),
        current_turn_index=1,
    )
    tp_distinct = _plateau_turn_profile(
        required_next_step="Distinct obligation from turn profile."
    )
    apply_mixed_transition_plateau_refresh(
        issue=issue, transition="escalated", turn_profile=tp_distinct, current_turn_index=2
    )
    assert issue.required_next_step == "Distinct obligation from turn profile."


def test_multiple_issues_only_matched_issue_mutates_plateau() -> None:
    alice = IssueState(
        issue_id="alice_issue",
        description="Alice control arc",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        required_next_step="Hold.",
    )
    bob = IssueState(
        issue_id="bob_issue",
        description="Bob separate arc",
        participants=["Bob"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="plan_execution",
        required_next_step="Decide.",
    )
    tp = _plateau_turn_profile(required_next_step="Hold.")
    apply_mixed_transition_plateau_refresh(
        issue=alice, transition="advanced", turn_profile=tp, current_turn_index=1
    )
    assert alice.required_next_step_plateau_streak == 1
    assert bob.required_next_step_plateau_streak == 0
    assert bob.required_next_step_plateau_last_norm == ""


def test_issue_state_serializes_plateau_fields() -> None:
    issue = IssueState(
        issue_id="i1",
        description="D",
        participants=["A"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        required_next_step_plateau_streak=2,
        required_next_step_plateau_last_norm="hold line",
        required_next_step_plateau_last_turn_index=5,
        required_next_step_plateau_has_advanced=True,
    )
    restored = IssueState.from_dict(issue.to_dict())
    assert restored.required_next_step_plateau_streak == 2
    assert restored.required_next_step_plateau_last_norm == "hold line"
    assert restored.required_next_step_plateau_last_turn_index == 5
    assert restored.required_next_step_plateau_has_advanced is True


def test_update_issues_norm_change_each_turn_no_plateau_template() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Hall",
        opening_description="Standoff",
        present_characters=["Alice", "Bob"],
    )
    issue = IssueState(
        issue_id="seed",
        description="Control standoff with Bob",
        participants=["Alice", "Bob"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        blocked_what="Control of the corridor",
        required_next_step="Step one.",
    )
    manager.issues[issue.issue_id] = issue
    manager.scene_state.active_issue_ids = [issue.issue_id]

    profiles = [
        _plateau_turn_profile(required_next_step="Step one."),
        _plateau_turn_profile(required_next_step="Step two is different."),
    ]
    call_idx = {"n": 0}

    def _fake_turn_profile(**kwargs: object) -> dict:
        del kwargs
        p = profiles[call_idx["n"]]
        call_idx["n"] += 1
        return dict(p)

    with (
        patch("continuity_issue_helpers._pressure_match_score", return_value=10),
        patch("continuity_issue_helpers._determine_issue_transition", return_value="advanced"),
        patch("continuity_issue_helpers._build_turn_pressure_profile", _fake_turn_profile),
    ):
        for tc in (0, 1):
            manager.turn_counter = tc
            update_issues(
                manager=manager,
                acting_character="Alice",
                move=_minimal_move(),
                event=None,
                consequence_tags=set(),
                state_changes=[],
                actionable_implications=[],
                issue_stall_turn_threshold=99,
                turn_tokens_fn=lambda m: turn_tokens(
                    move=m,
                    issue_tokens_fn=lambda t: issue_tokens(
                        text=t, stopwords=ISSUE_TOKEN_STOPWORDS
                    ),
                ),
                issue_tokens_fn=lambda t: issue_tokens(
                    text=t, stopwords=ISSUE_TOKEN_STOPWORDS
                ),
                merge_issue_terms_fn=lambda iss, terms: merge_issue_terms(
                    issue=iss, matched_terms=terms
                ),
                link_issue_interactions_fn=lambda iid: link_issue_interactions(
                    manager=manager, issue_id=iid
                ),
            )

    assert manager.issues["seed"].required_next_step == "Step two is different."
    assert manager.issues["seed"].required_next_step != REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE
    assert manager.issues["seed"].required_next_step_plateau_streak == 1


def test_update_issues_integration_advanced_escalated_refreshes() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Hall",
        opening_description="Standoff",
        present_characters=["Alice", "Bob"],
    )
    issue = IssueState(
        issue_id="seed",
        description="Control standoff with Bob",
        participants=["Alice", "Bob"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        blocked_what="Control of the corridor",
        required_next_step="Repeated same next step.",
    )
    manager.issues[issue.issue_id] = issue
    manager.scene_state.active_issue_ids = [issue.issue_id]

    fixed_profile = _plateau_turn_profile(required_next_step="Repeated same next step.")
    trans_seq = iter(["advanced", "escalated"])

    def _fake_turn_profile(**kwargs: object) -> dict:
        del kwargs
        return dict(fixed_profile)

    def _fake_transition(**kwargs: object) -> str:
        del kwargs
        return next(trans_seq)

    with (
        patch("continuity_issue_helpers._pressure_match_score", return_value=10),
        patch("continuity_issue_helpers._determine_issue_transition", _fake_transition),
        patch("continuity_issue_helpers._build_turn_pressure_profile", _fake_turn_profile),
    ):
        manager.turn_counter = 0
        update_issues(
            manager=manager,
            acting_character="Alice",
            move=_minimal_move(),
            event=None,
            consequence_tags=set(),
            state_changes=[],
            actionable_implications=[],
            issue_stall_turn_threshold=99,
            turn_tokens_fn=lambda m: turn_tokens(
                move=m,
                issue_tokens_fn=lambda t: issue_tokens(text=t, stopwords=ISSUE_TOKEN_STOPWORDS)
            ),
            issue_tokens_fn=lambda t: issue_tokens(text=t, stopwords=ISSUE_TOKEN_STOPWORDS),
            merge_issue_terms_fn=lambda iss, terms: merge_issue_terms(
                issue=iss, matched_terms=terms
            ),
            link_issue_interactions_fn=lambda iid: link_issue_interactions(
                manager=manager, issue_id=iid
            ),
        )
        assert manager.issues["seed"].required_next_step == "Repeated same next step."
        assert manager.issues["seed"].required_next_step_plateau_streak == 1

        manager.turn_counter = 1
        update_issues(
            manager=manager,
            acting_character="Alice",
            move=_minimal_move(),
            event=None,
            consequence_tags=set(),
            state_changes=[],
            actionable_implications=[],
            issue_stall_turn_threshold=99,
            turn_tokens_fn=lambda m: turn_tokens(
                move=m,
                issue_tokens_fn=lambda t: issue_tokens(text=t, stopwords=ISSUE_TOKEN_STOPWORDS)
            ),
            issue_tokens_fn=lambda t: issue_tokens(text=t, stopwords=ISSUE_TOKEN_STOPWORDS),
            merge_issue_terms_fn=lambda iss, terms: merge_issue_terms(
                issue=iss, matched_terms=terms
            ),
            link_issue_interactions_fn=lambda iid: link_issue_interactions(
                manager=manager, issue_id=iid
            ),
        )

    assert manager.issues["seed"].required_next_step == REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE
    assert manager.issues["seed"].required_next_step_plateau_streak == 0
