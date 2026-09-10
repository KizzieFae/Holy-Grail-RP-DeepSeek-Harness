"""Post-commit semantic eligibility (#164).

Deterministic gate for 0–1 Storyteller issue-pressure assessment per commit.
"""

from __future__ import annotations

from typing import Literal

from continuity_issue_retrieval import get_active_issues
from continuity_state import IssueStatus

from .session_state import LiveSession

EligibilityOutcome = Literal[
    "eligible_active_issues",
    "no_eligible_active_issues",
    "eligibility_uncertain_fail_open",
]

_ELIGIBLE_STATUSES = [IssueStatus.ACTIVE, IssueStatus.ESCALATING]


def evaluate_post_commit_semantic_eligibility(
    fixture: LiveSession,
) -> tuple[bool, EligibilityOutcome]:
    """Return (inference_required, outcome).

    Fail open when eligibility cannot be determined deterministically.
    """
    try:
        manager = fixture.manager
        if manager is None:
            return True, "eligibility_uncertain_fail_open"
        active = get_active_issues(
            manager=manager,
            limit=1,
            statuses=_ELIGIBLE_STATUSES,
        )
        if not active:
            return False, "no_eligible_active_issues"
        return True, "eligible_active_issues"
    except Exception:
        return True, "eligibility_uncertain_fail_open"
