"""Issue #194 — decomposition substantive-coverage fidelity tests."""

from __future__ import annotations

import unittest

from player_semantic_normalization import (
    FAILURE_SIR_SUBSTANTIVE_OMISSION,
    normalize_player_semantic_decomposition,
)

F06_SOURCE = (
    "Kizzie glanced up, double-checking the house number and then steeled herself before knocking."
)

F06_ATTEMPT_0 = {
    "units": [
        {
            "kind": "observable_event",
            "text": "Kizzie glanced up, double-checking the house number",
            "recipients": {"scope": "present", "characters": ["Ayame", "Kizzie"]},
        },
        {
            "kind": "internal",
            "text": "and then steeled herself before knocking",
            "recipients": {"scope": "private", "characters": ["Kizzie"]},
        },
    ]
}


class Issue194PvrCoverageFidelityTests(unittest.TestCase):
    def test_f06_terminal_period_absorbed_without_retry(self) -> None:
        result = normalize_player_semantic_decomposition(
            content=F06_SOURCE,
            speaker="Player",
            semantic_decomposition=F06_ATTEMPT_0,
            attempt_index=0,
        )
        self.assertTrue(result["accepted"])
        audit = result["normalization_audit"]
        self.assertTrue(audit.get("terminal_punctuation_absorbed"))
        units = result["player_decomposition"]["perceptual_visibility"]["units"]
        internal = next(item for item in units if item["kind"] == "internal")
        self.assertTrue(internal["text"].endswith("."))

    def test_terminal_exclamation_absorbed(self) -> None:
        content = "She knocked!"
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition={
                "units": [
                    {
                        "kind": "observable_event",
                        "text": "She knocked",
                        "recipients": {"scope": "present", "characters": [], "roles": []},
                    }
                ]
            },
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(result["normalization_audit"].get("terminal_punctuation_absorbed"))

    def test_omitted_word_still_fails(self) -> None:
        result = normalize_player_semantic_decomposition(
            content="Alpha Beta",
            speaker="Player",
            semantic_decomposition={
                "units": [
                    {
                        "kind": "speech",
                        "text": "Alpha",
                        "recipients": {"scope": "public", "characters": [], "roles": []},
                    }
                ]
            },
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)
        spans = result["normalization_audit"].get("uncovered_substantive_spans") or []
        self.assertTrue(any("Beta" in span.get("text", "") for span in spans))

    def test_omitted_internal_state_still_fails(self) -> None:
        content = "She smiled. She panicked inside."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition={
                "units": [
                    {
                        "kind": "observable_event",
                        "text": "She smiled.",
                        "recipients": {"scope": "present", "characters": [], "roles": []},
                    }
                ]
            },
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)

    def test_omitted_observable_action_still_fails(self) -> None:
        content = "She waved and then knocked."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition={
                "units": [
                    {
                        "kind": "observable_event",
                        "text": "She waved",
                        "recipients": {"scope": "present", "characters": [], "roles": []},
                    }
                ]
            },
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)

    def test_omitted_directed_speech_still_fails(self) -> None:
        content = 'She said, "Hello," to Ayame.'
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition={
                "units": [
                    {
                        "kind": "speech",
                        "text": "Hello,",
                        "recipients": {
                            "scope": "directed",
                            "characters": ["Ayame"],
                            "roles": [],
                        },
                    }
                ]
            },
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)


if __name__ == "__main__":
    unittest.main()
