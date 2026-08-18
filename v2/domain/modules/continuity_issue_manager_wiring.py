"""Issue lifecycle wiring and constants for ``ContinuityManager`` (Issue #149 Slice 2).

Manager-thinning only: constants plus thin bridges to ``continuity_issue_helpers``.
Does **not** change helper algorithms or ``process_turn`` sequencing.
"""

from __future__ import annotations

from typing import Any, Callable

from continuity_issue_helpers import (
    find_matching_issue,
    issue_tokens,
    link_issue_interactions,
    merge_issue_terms,
)
from continuity_state import IssueState

MAX_ACTIVE_ISSUES = 3
DEFAULT_ACTIVE_ISSUE_LIMIT = 4
ISSUE_STALL_TURN_THRESHOLD = 3
ISSUE_TOKEN_STOPWORDS = {
    "about",
    "after",
    "because",
    "before",
    "could",
    "did",
    "from",
    "have",
    "into",
    "just",
    "much",
    "should",
    "that",
    "their",
    "them",
    "they",
    "this",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


def issue_tokens_for_manager_stopwords(text: str) -> set[str]:
    """Tokenize ``text`` using the continuity manager issue stopword set."""
    return issue_tokens(text=text, stopwords=ISSUE_TOKEN_STOPWORDS)


def merge_issue_terms_positional(issue: IssueState, matched_terms: set[str]) -> None:
    """Adapter: helpers use keyword-only ``merge_issue_terms``; callers use two positionals."""
    merge_issue_terms(issue=issue, matched_terms=matched_terms)


def find_matching_issue_for_manager(
    manager: Any, pressure_profile: dict[str, Any]
) -> IssueState | None:
    return find_matching_issue(
        manager=manager,
        pressure_profile=pressure_profile,
        issue_tokens_fn=issue_tokens_for_manager_stopwords,
    )


def link_issue_interactions_callback(manager: Any) -> Callable[[str], None]:
    """Callback shape expected by ``maybe_create_issue`` / ``update_issues``."""

    def _cb(issue_id: str) -> None:
        link_issue_interactions(manager=manager, issue_id=issue_id)

    return _cb
