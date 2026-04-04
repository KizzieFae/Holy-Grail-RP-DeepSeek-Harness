"""Episodic continuity inputs align with authoritative issue projection."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from continuity_scene_helpers import initialize_scene_state
from continuity_state import IssueState, IssueStatus
from episodic_memory_inputs import continuity_sequences_for_episodic


def _dt() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _manager_with_issue(*, on_active_index: bool) -> ContinuityManager:
    m = ContinuityManager()
    initialize_scene_state(
        manager=m,
        location="room",
        opening_description="",
        present_characters=["Alice", "Bob"],
    )
    assert m.scene_state is not None
    issue = IssueState(
        issue_id="iss_episodic_input",
        description="Pressure",
        participants=["Alice", "Bob"],
        status=IssueStatus.ESCALATING,
        created_at=_dt(),
    )
    m.issues[issue.issue_id] = issue
    if on_active_index:
        m.scene_state.active_issue_ids = [issue.issue_id]
    else:
        m.scene_state.active_issue_ids = []
    return m


def test_episodic_issues_empty_when_not_in_active_issue_ids():
    m = _manager_with_issue(on_active_index=False)
    _, _, issues, _ = continuity_sequences_for_episodic(m)
    assert issues == ()


def test_episodic_issues_include_when_in_active_issue_ids():
    m = _manager_with_issue(on_active_index=True)
    _, _, issues, _ = continuity_sequences_for_episodic(m)
    assert len(issues) == 1
    assert issues[0].issue_id == "iss_episodic_input"


def test_episodic_issues_excluded_when_status_not_active_escalating():
    m = _manager_with_issue(on_active_index=True)
    m.issues["iss_episodic_input"] = IssueState(
        issue_id="iss_episodic_input",
        description="Pressure",
        participants=["Alice", "Bob"],
        status=IssueStatus.RESOLVED,
        created_at=_dt(),
        resolved_at=_dt(),
    )
    _, _, issues, _ = continuity_sequences_for_episodic(m)
    assert issues == ()
