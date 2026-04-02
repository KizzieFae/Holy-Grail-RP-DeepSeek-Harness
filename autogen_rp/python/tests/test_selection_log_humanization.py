"""Unit tests for Track C: human-facing selection log helpers (no selector authority)."""

from semantic_validation import (
    SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD,
    filter_selection_issues_for_human_log,
    substitute_agent_keys_with_display_names,
)


def test_filter_keeps_reconciled_when_deterministic_nonempty() -> None:
    base = ["deterministic issue"]
    reconciled = ["deterministic issue", "semantic extra"]
    assert filter_selection_issues_for_human_log(
        base_issues=base,
        reconciled_issues=reconciled,
        semantic_assessment={"confidence": 0.0},
    ) == reconciled


def test_filter_keeps_reconciled_when_semantic_none() -> None:
    reconciled = ["only semantic path"]
    assert filter_selection_issues_for_human_log(
        base_issues=[],
        reconciled_issues=reconciled,
        semantic_assessment=None,
    ) == reconciled


def test_filter_drops_reconciled_when_deterministic_empty_and_low_confidence() -> None:
    reconciled = ["[SEMANTIC] selection concern"]
    assert filter_selection_issues_for_human_log(
        base_issues=[],
        reconciled_issues=reconciled,
        semantic_assessment={"confidence": SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD - 0.01},
    ) == []


def test_filter_keeps_reconciled_at_threshold() -> None:
    reconciled = ["[SEMANTIC] selection concern"]
    assert filter_selection_issues_for_human_log(
        base_issues=[],
        reconciled_issues=reconciled,
        semantic_assessment={"confidence": SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD},
    ) == reconciled


def test_substitute_longest_keys_first_avoids_partial_inside_longer() -> None:
    names = ["ab", "ab_cd"]
    display = {"ab": "Short", "ab_cd": "Long Name"}

    def lookup(k: str) -> str:
        return display.get(k, k)

    assert (
        substitute_agent_keys_with_display_names("x ab_cd y ab z", names, lookup)
        == "x Long Name y Short z"
    )


def test_substitute_whole_token_only() -> None:
    names = ["cel"]
    assert (
        substitute_agent_keys_with_display_names(
            "excel and celina",
            names,
            lambda k: "CEL" if k == "cel" else k,
        )
        == "excel and celina"
    )


def test_substitute_skips_when_display_equals_key() -> None:
    names = ["Ayame"]
    assert (
        substitute_agent_keys_with_display_names(
            "pick Ayame",
            names,
            lambda k: k,
        )
        == "pick Ayame"
    )
