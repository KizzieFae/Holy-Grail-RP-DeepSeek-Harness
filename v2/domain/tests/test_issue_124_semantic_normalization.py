"""Issue #124 — semantic decomposition normalization tests."""

from __future__ import annotations

import time
import unittest

from player_semantic_normalization import (
    FAILURE_FRAGMENT_AMBIGUOUS,
    FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL,
    FAILURE_SEARCH_BUDGET_EXCEEDED,
    FAILURE_SIR_NON_VERBATIM,
    FAILURE_SIR_SUBSTANTIVE_OMISSION,
    FAILURE_VALIDATION_REJECTED,
    NORMALIZATION_DETERMINISTIC_WORK_BUDGET,
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

    def _single_char_units(self, count: int) -> dict:
        return _sir(
            *[
                {
                    "kind": "speech",
                    "text": "a",
                    "recipients": {"scope": "public", "characters": [], "roles": []},
                }
                for _ in range(count)
            ]
        )

    def test_search_budget_exceeded_on_pathological_tiling(self) -> None:
        content = "a" * 9
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(9),
            attempt_index=0,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SEARCH_BUDGET_EXCEEDED)
        self.assertTrue(result["retry_eligible"])
        audit = result["normalization_audit"]
        self.assertTrue(audit.get("budget_exceeded"))
        self.assertGreaterEqual(audit.get("work_consumed", 0), NORMALIZATION_DETERMINISTIC_WORK_BUDGET)
        self.assertIn(
            audit.get("work_exhaustion_stage"),
            {"dfs_visit", "candidate_probe", "occurrence_scan", "overlap_check", "substantive_mask"},
        )

    def test_pathological_tiling_fails_within_time_bound(self) -> None:
        content = "a" * 9
        start = time.perf_counter()
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(9),
            attempt_index=0,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SEARCH_BUDGET_EXCEEDED)
        self.assertLess(elapsed_ms, 500)

    def test_search_budget_exceeded_terminal_after_retry(self) -> None:
        content = "a" * 9
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(9),
            attempt_index=1,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SEARCH_BUDGET_EXCEEDED)
        self.assertFalse(result["retry_eligible"])

    def test_equal_fingerprints_do_not_short_circuit_to_equivalent(self) -> None:
        """Nine identical one-char units exceed the search budget instead of accepting."""
        result = normalize_player_semantic_decomposition(
            content="a" * 9,
            speaker="Player",
            semantic_decomposition=self._single_char_units(9),
        )
        self.assertNotEqual(result.get("normalization_audit", {}).get("ambiguity_class"), "equivalent")
        self.assertFalse(result["accepted"])

    def test_equivalent_repeated_fragment_still_normalizes_within_budget(self) -> None:
        content = "a" * 7
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(7),
        )
        self.assertTrue(result["accepted"])
        audit = result["normalization_audit"]
        self.assertEqual(audit.get("ambiguity_class"), "equivalent")
        self.assertLessEqual(audit.get("work_consumed", 0), NORMALIZATION_DETERMINISTIC_WORK_BUDGET)

    def test_omission_pathology_terminates_within_budget(self) -> None:
        content = "a" * 50
        start = time.perf_counter()
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(10),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)
        self.assertLess(elapsed_ms, 2000)
        self.assertLessEqual(
            result["normalization_audit"].get("work_consumed", 0),
            NORMALIZATION_DETERMINISTIC_WORK_BUDGET,
        )

    def test_long_source_budget_exceeded_not_omission(self) -> None:
        content = "a" * 50_000
        start = time.perf_counter()
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(7),
            attempt_index=0,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failure_class"], FAILURE_SEARCH_BUDGET_EXCEEDED)
        self.assertNotEqual(result["failure_class"], FAILURE_SIR_SUBSTANTIVE_OMISSION)
        audit = result["normalization_audit"]
        self.assertTrue(audit.get("budget_exceeded"))
        self.assertEqual(audit.get("work_exhaustion_stage"), "occurrence_scan")
        self.assertGreaterEqual(audit.get("work_consumed", 0), NORMALIZATION_DETERMINISTIC_WORK_BUDGET)
        self.assertLess(elapsed_ms, 500)

    def test_long_source_multi_unit_budget_exceeded_quickly(self) -> None:
        content = "a" * 100_000
        start = time.perf_counter()
        result = normalize_player_semantic_decomposition(
            content=content,
            speaker="Player",
            semantic_decomposition=self._single_char_units(7),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(result["failure_class"], FAILURE_SEARCH_BUDGET_EXCEEDED)
        self.assertEqual(result["normalization_audit"].get("work_exhaustion_stage"), "occurrence_scan")
        self.assertLess(elapsed_ms, 500)

    def test_budget_audit_fields_present_on_failure(self) -> None:
        result = normalize_player_semantic_decomposition(
            content="a" * 9,
            speaker="Player",
            semantic_decomposition=self._single_char_units(9),
            attempt_index=0,
        )
        audit = result["normalization_audit"]
        for field in (
            "deterministic_work_budget",
            "work_consumed",
            "work_occurrence_scan",
            "work_candidates_generated",
            "work_substantive_mask",
            "work_candidate_probes",
            "work_overlap_checks",
            "search_nodes_visited",
            "work_exhaustion_stage",
        ):
            self.assertIn(field, audit)
        self.assertGreater(audit.get("work_overlap_checks", 0), 0)

    def test_material_ambiguity_early_exit_stays_bounded(self) -> None:
        content = "she nodded. she nodded."
        start = time.perf_counter()
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
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(result["failure_class"], FAILURE_FRAGMENT_AMBIGUOUS)
        self.assertLess(elapsed_ms, 500)
        self.assertLessEqual(result["normalization_audit"].get("search_nodes_visited", 0), 20)


if __name__ == "__main__":
    unittest.main()
