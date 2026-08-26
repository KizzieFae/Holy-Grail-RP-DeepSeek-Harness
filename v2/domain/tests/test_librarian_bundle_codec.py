"""Regression tests for librarian bundle HTTP codec (#45)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_bundle_codec import librarian_knowledge_bundle_from_dict  # noqa: E402


class LibrarianBundleCodecTests(unittest.TestCase):
    def test_bundle_entry_without_synthesis_meta_decodes(self) -> None:
        payload = {
            "bundle_id": "bundle-1",
            "request_id": "req-1",
            "consumer_role": "character",
            "pipeline_stage": "character",
            "hg_round_id": "round-1",
            "turn_index": 0,
            "mediation_mode": "contextual_semantic",
            "validity": {
                "validity_scope": "stage_current",
                "bound_hg_round_id": "round-1",
                "bound_turn_index": 0,
                "bound_pipeline_stage": "character",
                "valid_from_authoritative_snapshot_id": "snap-1",
                "invalidation_keys": [],
            },
            "degradation": {"level": "none", "mode": "none", "deterministic_fallback_used": False},
            "satisfaction": {"truncated": False},
            "entries": [
                {
                    "entry_id": "entry-1",
                    "ref": {
                        "ref_kind": "catalog_source",
                        "stable_ref": "lmi:cand:ni-fact-g",
                        "display_hint": "ni-fact-g",
                    },
                    "content": "FACT_G_VISIBLE_MARKER: latch detail",
                    "information_class": "compiled_index",
                    "source_tier": "retrieval_candidate",
                    "authority_class": "suggestive",
                    "visibility_scope": "public",
                    "librarian_annotation": {
                        "relevance_rank": 1,
                        "interpretive_status": "likely",
                        "relevance_band": "high",
                    },
                    "provenance": {"catalog_source_id": "lmi:cand:ni-fact-g"},
                }
            ],
            "budget_accounting": {
                "entries_returned": 1,
                "entries_considered": 1,
                "chars_returned": 32,
                "chars_budget": 8000,
                "entries_truncated": 0,
            },
            "source_diagnostics": {"consulted_tiers": [], "omitted_tiers": []},
            "audit": {
                "bundle_hash": "hash-1",
                "retrieval_request_ids": [],
                "candidate_ids_considered": ["ni-fact-g"],
                "original_request_id": "req-1",
                "mediation_mode": "contextual_semantic",
                "mediation_strategy": "contextual_semantic",
            },
        }
        bundle = librarian_knowledge_bundle_from_dict(payload)
        self.assertEqual(len(bundle.entries), 1)
        self.assertEqual(bundle.entries[0].temporal_relationship, "current")
        self.assertIn("FACT_G_VISIBLE_MARKER", bundle.entries[0].content)


if __name__ == "__main__":
    unittest.main()
