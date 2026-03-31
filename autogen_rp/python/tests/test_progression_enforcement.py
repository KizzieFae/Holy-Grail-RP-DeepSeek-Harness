"""Tests for deterministic progression delta qualification."""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_enforcement import (  # noqa: E402
    qualifies_as_progression_delta,
)


def _cm(
    *,
    turn_index: int,
    turn_metadata_by_index: dict[int, dict],
    issues: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        turn_counter=turn_index,
        turn_metadata_by_index=dict(turn_metadata_by_index),
        issues=issues or {},
    )


def test_q1_sole_consequence_repeat_of_previous_turn_does_not_qualify_when_alone() -> None:
    cm = _cm(
        turn_index=2,
        turn_metadata_by_index={
            1: {"consequences": ["revelation"]},
            2: {"consequences": ["revelation"]},
        },
    )
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=2,
            turn_meta={"consequences": ["revelation"]},
            issues_before={},
            move={},
        )
        is False
    )


def test_q1_sole_consequence_new_vs_previous_qualifies() -> None:
    cm = _cm(
        turn_index=2,
        turn_metadata_by_index={
            1: {"consequences": ["revelation"]},
            2: {"consequences": ["escalation"]},
        },
    )
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=2,
            turn_meta={"consequences": ["escalation"]},
            issues_before={},
            move={},
        )
        is True
    )


def test_q1_two_consequences_qualifies_even_if_one_matches_previous_sole() -> None:
    cm = _cm(
        turn_index=2,
        turn_metadata_by_index={
            1: {"consequences": ["revelation"]},
            2: {"consequences": ["revelation", "escalation"]},
        },
    )
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=2,
            turn_meta={"consequences": ["revelation", "escalation"]},
            issues_before={},
            move={},
        )
        is True
    )


def test_q2_issue_status_change_qualifies() -> None:
    issue = SimpleNamespace(
        issue_id="i1",
        last_turn_index=2,
        status=SimpleNamespace(value="escalating"),
        participants=["A"],
        status_reason="",
    )
    cm = _cm(turn_index=2, turn_metadata_by_index={2: {"consequences": []}}, issues={"i1": issue})
    before = {"i1": ("active", frozenset({"A"}))}
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=2,
            turn_meta={"consequences": []},
            issues_before=before,
            move={},
        )
        is True
    )


def test_q3_exit_consequence_qualifies() -> None:
    cm = _cm(turn_index=1, turn_metadata_by_index={1: {"consequences": ["exit"]}})
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=1,
            turn_meta={"consequences": ["exit"]},
            issues_before={},
            move={},
        )
        is True
    )


def test_q4_scene_state_updates_key_qualifies() -> None:
    cm = _cm(turn_index=1, turn_metadata_by_index={1: {"consequences": []}})
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=1,
            turn_meta={"consequences": []},
            issues_before={},
            move={"scene_state_updates": {"housing_call_outcome": {"status": "completed"}}},
        )
        is True
    )


def test_empty_turn_does_not_qualify() -> None:
    cm = _cm(turn_index=1, turn_metadata_by_index={1: {"consequences": []}})
    assert (
        qualifies_as_progression_delta(
            continuity_manager=cm,
            turn_index=1,
            turn_meta={"consequences": []},
            issues_before={},
            move={},
        )
        is False
    )
