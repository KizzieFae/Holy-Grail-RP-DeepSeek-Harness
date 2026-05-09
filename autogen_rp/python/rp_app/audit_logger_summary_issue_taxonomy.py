"""Heuristic issue buckets for audit summary aggregation (Issue #154 Slice A)."""

from typing import Any

ISSUE_CATEGORY_KEYS = (
    "character_drift",
    "memory_drift",
    "turn_selection_mistakes",
    "repetitive_phrasing",
    "continuity_signal_gaps",
    "issue_lifecycle_gaps",
)


def empty_issue_categories() -> dict[str, dict[str, Any]]:
    return {key: {"count": 0, "examples": []} for key in ISSUE_CATEGORY_KEYS}


def categorize_issue_text(text: str) -> str | None:
    normalized = str(text or "").lower()
    if not normalized:
        return None
    if any(
        token in normalized
        for token in [
            "character_drift",
            "wrong pov",
            "voice profile",
            "identity anchor",
        ]
    ):
        return "character_drift"
    if any(
        token in normalized
        for token in ["memory", "canon", "continuity", "summary block", "anchor"]
    ):
        return "memory_drift"
    if any(
        token in normalized
        for token in [
            "turn_selection",
            "direct address",
            "spotlight",
            "available_next_actors",
            "fallback selection",
        ]
    ):
        return "turn_selection_mistakes"
    if any(
        token in normalized
        for token in [
            "duplicate",
            "repeated content",
            "substantial content overlap",
            "repetitive",
        ]
    ):
        return "repetitive_phrasing"
    if any(
        token in normalized
        for token in [
            "state change",
            "recent_delta",
            "continuity_event_type",
            "actionable implication",
            "dialogue-only",
            "no material change",
            "consequence",
        ]
    ):
        return "continuity_signal_gaps"
    if any(
        token in normalized
        for token in [
            "stalled issue",
            "issue lifecycle",
            "resolved issue",
            "active issue",
            "issue update",
        ]
    ):
        return "issue_lifecycle_gaps"
    return None


def record_issue_category(
    categories: dict[str, dict[str, Any]], category: str | None, example: str
) -> None:
    if category is None or category not in categories:
        return
    categories[category]["count"] += 1
    if example and example not in categories[category]["examples"]:
        categories[category]["examples"].append(example)
        categories[category]["examples"] = categories[category]["examples"][:5]
