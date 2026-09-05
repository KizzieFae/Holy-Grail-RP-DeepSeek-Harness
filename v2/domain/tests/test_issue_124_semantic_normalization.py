"""Issue #124 — semantic decomposition normalization tests."""

from __future__ import annotations

import unittest

from player_semantic_normalization import (
    FAILURE_FRAGMENT_AMBIGUOUS,
    FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL,
    FAILURE_SIR_NON_VERBATIM,
    FAILURE_SIR_SUBSTANTIVE_OMISSION,
    FAILURE_VALIDATION_REJECTED,
    normalize_player_semantic_decomposition,
)
from player_perceptual_service import validate_player_perceptual_decomposition


def _sir(*units: dict) -> dict:
    return {"units": list(units)}


class Issue124SemanticNormalizationTests(unittest.TestCase):
    def test_simple_speech_accepted(self) -> None:
        content = "Hello everyone."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Hello everyone.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
            ),
        )
        self.assertTrue(result["accepted"])
        decomposition = result["player_decomposition"]
        assert decomposition is not None
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        self.assertEqual(record.units[0].source_provenance["order_index"], 0)

    def test_out_of_order_units_sorted_by_source_position(self) -> None:
        content = "Alpha. Beta."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Beta.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
                {
                    "kind": "speech",
                    "text": "Alpha.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
            ),
        )
        self.assertTrue(result["accepted"])
        decomposition = result["player_decomposition"]
        assert decomposition is not None
        texts = [
            unit["text"]
            for unit in sorted(
                decomposition["perceptual_visibility"]["units"],
                key=lambda item: item["source_provenance"]["order_index"],
            )
        ]
        self.assertEqual(texts, ["Alpha.", "Beta."])

    def test_repeated_identical_fragment_unique_semantics(self) -> None:
        content = "Yes. Yes."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Yes.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
                {
                    "kind": "speech",
                    "text": "Yes.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
            ),
        )
        self.assertTrue(result["accepted"])
        decomposition = result["player_decomposition"]
        assert decomposition is not None
        self.assertEqual(len(decomposition["perceptual_visibility"]["units"]), 2)

    def test_material_ambiguity_retryable_on_first_attempt(self) -> None:
        content = "she nodded. she nodded."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "observable_event",
                    "text": "she nodded.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
                {
                    "kind": "internal",
                    "text": "she nodded.",
                    "recipients": {"scope": "private", "characters": [], "roles": []},
                },
            ),
            attempt_index=0,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_FRAGMENT_AMBIGUOUS)
        self.assertTrue(result["retry_eligible"])

    def test_material_ambiguity_terminal_after_retry(self) -> None:
        content = "she nodded. she nodded."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "observable_event",
                    "text": "she nodded.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
                {
                    "kind": "internal",
                    "text": "she nodded.",
                    "recipients": {"scope": "private", "characters": [], "roles": []},
                },
            ),
            attempt_index=1,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL)
        self.assertFalse(result["retry_eligible"])

    def test_substantive_omission_detected(self) -> None:
        content = "Alpha Beta"
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Alpha",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
            ),
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)

    def test_non_verbatim_excerpt_rejected(self) -> None:
        result = normalize_player_semantic_decomposition(
            content="Hello.",
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Goodbye.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
            ),
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_NON_VERBATIM)

    def test_whitespace_gap_becomes_non_projects(self) -> None:
        content = "Hi. There"
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Hi.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
                {
                    "kind": "speech",
                    "text": "There",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                },
            ),
        )
        self.assertTrue(result["accepted"])
        decomposition = result["player_decomposition"]
        assert decomposition is not None
        dispositions = [
            segment["disposition"]
            for segment in decomposition["source_accounting"]["segments"]
        ]
        self.assertIn("non_projects", dispositions)

    def test_internal_public_scope_rejected_at_validation(self) -> None:
        result = normalize_player_semantic_decomposition(
            content="secret thought",
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "internal",
                    "text": "secret thought",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
            ),
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_VALIDATION_REJECTED)

    def test_audit_chain_present(self) -> None:
        content = "Hello."
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=_sir(
                {
                    "kind": "speech",
                    "text": "Hello.",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
            ),
            generation={"inference_id": "test"},
        )
        self.assertTrue(result["accepted"])
        decomposition = result["player_decomposition"]
        assert decomposition is not None
        generation = decomposition["generation"]
        self.assertIn("semantic_decomposition", generation)
        self.assertIn("normalization", generation)


if __name__ == "__main__":
    unittest.main()
