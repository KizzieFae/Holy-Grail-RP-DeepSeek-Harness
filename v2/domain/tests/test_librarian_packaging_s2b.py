"""#34 S2b Librarian bundle → Packaging mapper tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import PromptContribution  # noqa: E402
from domain_api.librarian_contract import (  # noqa: E402
    BudgetAccounting,
    BundleAudit,
    BundleDegradation,
    BundleValidity,
    InvalidationKey,
    LibrarianAnnotation,
    LibrarianBundleEntry,
    LibrarianKnowledgeBundle,
    RequestSatisfactionSummary,
    SourceDiagnostics,
    StableReference,
    SynthesisMeta,
)
from domain_api.librarian_packaging_mapper import map_librarian_bundle_to_contributions  # noqa: E402
from domain_api.librarian_packaging_policy import policy_for_consumer  # noqa: E402
from domain_api.librarian_packaging_validity import PackagingBindingContext  # noqa: E402


def _binding(**overrides: object) -> PackagingBindingContext:
    base = PackagingBindingContext(
        hg_round_id="round-1",
        turn_index=0,
        pipeline_stage="director",
        continuity_version=3,
        authoritative_snapshot_id="cv:3:scene:scene-1:round:round-1",
    )
    if not overrides:
        return base
    return PackagingBindingContext(**{**base.__dict__, **overrides})


def _bundle(
    *,
    entries: tuple[LibrarianBundleEntry, ...],
    mediation_mode: str = "contextual_semantic",
    validity: BundleValidity | None = None,
    degradation: BundleDegradation | None = None,
) -> LibrarianKnowledgeBundle:
    binding = _binding()
    validity = validity or BundleValidity(
        validity_scope="stage_current",
        bound_hg_round_id="round-1",
        bound_turn_index=0,
        bound_pipeline_stage="director",
        valid_from_authoritative_snapshot_id=binding.authoritative_snapshot_id,
        invalidation_keys=(
            InvalidationKey(key_kind="continuity_version", key_value="3"),
            InvalidationKey(key_kind="hg_round_id", key_value="round-1"),
            InvalidationKey(key_kind="pipeline_stage", key_value="director"),
        ),
    )
    degradation = degradation or BundleDegradation(
        level="none",
        mode="none",
        deterministic_fallback_used=False,
    )
    return LibrarianKnowledgeBundle(
        bundle_id="bundle-test",
        request_id="req-test",
        consumer_role="storyteller",
        pipeline_stage="director",
        hg_round_id="round-1",
        turn_index=0,
        mediation_mode=mediation_mode,  # type: ignore[arg-type]
        validity=validity,
        degradation=degradation,
        satisfaction=RequestSatisfactionSummary(focus_questions=()),
        entries=entries,
        budget_accounting=BudgetAccounting(
            entries_returned=len(entries),
            entries_considered=len(entries),
            chars_returned=sum(len(entry.content) for entry in entries),
            chars_budget=8000,
        ),
        source_diagnostics=SourceDiagnostics(consulted_tiers=(), omitted_tiers=()),
        audit=BundleAudit(
            bundle_hash="abc123",
            retrieval_request_ids=(),
            candidate_ids_considered=(),
            original_request_id="req-test",
            mediation_mode=mediation_mode,  # type: ignore[arg-type]
            mediation_strategy="contextual_semantic_v1",
        ),
    )


def _entry(
    entry_id: str,
    content: str,
    *,
    rank: int,
    authority: str = "suggestive",
    source_tier: str = "retrieval_candidate",
    synthesis: SynthesisMeta | None = None,
    stable_ref: str | None = None,
    visibility_scope: str = "scene_orchestration",
) -> LibrarianBundleEntry:
    return LibrarianBundleEntry(
        entry_id=entry_id,
        ref=StableReference(
            ref_kind="retrieval_candidate",
            stable_ref=stable_ref or entry_id,
        ),
        content=content,
        information_class="authored_static",
        source_tier=source_tier,
        authority_class=authority,  # type: ignore[arg-type]
        visibility_scope=visibility_scope,
        provenance={"candidate_id": entry_id},
        temporal_relationship="recent",
        librarian_annotation=LibrarianAnnotation(relevance_rank=rank),
        synthesis_meta=synthesis,
    )


class LibrarianPackagingMappingTests(unittest.TestCase):
    def test_valid_bundle_maps_deterministically(self) -> None:
        bundle = _bundle(
            entries=(
                _entry("e1", "First mediated fact.", rank=1),
                _entry("e2", "Second mediated fact.", rank=2),
            )
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertTrue(result.eligibility.accepted)
        self.assertEqual(len(result.contributions), 2)
        self.assertEqual(result.contributions[0].contribution_id, "manifest-test-librarian-e1")
        self.assertEqual(result.contributions[1].source_kind, "librarian_knowledge")

    def test_preserves_librarian_order_without_reranking(self) -> None:
        bundle = _bundle(
            entries=(
                _entry("rank-1", "Highest rank.", rank=1),
                _entry("rank-2", "Middle rank.", rank=2),
                _entry("rank-3", "Lower rank.", rank=3),
            )
        )
        policy = policy_for_consumer("director")
        policy = policy.__class__(**{**policy.__dict__, "max_entries": 2})
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
            policy=policy,
        )
        self.assertEqual(
            [item.contribution_id for item in result.contributions],
            ["manifest-test-librarian-rank-1", "manifest-test-librarian-rank-2"],
        )

    def test_consumer_caps_apply_without_semantic_reranking(self) -> None:
        bundle = _bundle(
            entries=tuple(_entry(f"e{i}", f"Entry {i}.", rank=i) for i in range(1, 6))
        )
        policy = policy_for_consumer("director")
        policy = policy.__class__(**{**policy.__dict__, "max_entries": 3})
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
            policy=policy,
        )
        self.assertEqual(len(result.contributions), 3)


class LibrarianPackagingAuthorityTests(unittest.TestCase):
    def test_suggestive_remains_suggestive(self) -> None:
        bundle = _bundle(entries=(_entry("e1", "Suggestive lore.", rank=1, authority="suggestive"),))
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertEqual(result.contributions[0].authority_class, "suggestive")

    def test_authoritative_source_entry_preserves_original_authority(self) -> None:
        bundle = _bundle(
            entries=(
                _entry(
                    "auth-1",
                    "Promoted learned fact.",
                    rank=1,
                    authority="derived",
                    source_tier="retrieval_candidate",
                    stable_ref="promoted:learned:42",
                ),
            )
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        contribution = result.contributions[0]
        self.assertEqual(contribution.authority_class, "derived")
        self.assertIn("promoted:learned:42", contribution.knowledge_ids)
        self.assertNotEqual(contribution.provenance.get("projection_kind"), "authoritative_context")

    def test_synthesis_cannot_become_authoritative(self) -> None:
        synthesis = SynthesisMeta(
            synthesis_kind="summary",
            source_entry_refs=(
                StableReference(ref_kind="retrieval_candidate", stable_ref="src-a"),
                StableReference(ref_kind="retrieval_candidate", stable_ref="src-b"),
            ),
        )
        bundle = _bundle(
            entries=(
                _entry(
                    "syn-1",
                    "Bridge summary across sources.",
                    rank=1,
                    synthesis=synthesis,
                ),
            )
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="storyteller",
            binding=_binding(),
        )
        contribution = result.contributions[0]
        self.assertEqual(contribution.source_kind, "librarian_synthesis")
        self.assertEqual(contribution.authority_class, "suggestive")
        self.assertIn("src-a", contribution.knowledge_ids)


class LibrarianPackagingProvenanceTests(unittest.TestCase):
    def test_source_references_survive_mapping(self) -> None:
        bundle = _bundle(entries=(_entry("cand-9", "Hidden passage detail.", rank=1, stable_ref="cand-9"),))
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        contribution = result.contributions[0]
        self.assertIn("cand-9", contribution.knowledge_ids)
        self.assertEqual(contribution.provenance.get("stable_ref"), "cand-9")
        self.assertEqual(contribution.provenance.get("mediation_mode"), "contextual_semantic")


class LibrarianPackagingValidityTests(unittest.TestCase):
    def test_invalidated_bundle_produces_no_lanes(self) -> None:
        bundle = _bundle(entries=(_entry("e1", "Should not appear.", rank=1),))
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(continuity_version=99),
        )
        self.assertEqual(result.contributions, ())
        self.assertFalse(result.eligibility.accepted)
        self.assertIn("continuity_version_stale", result.eligibility.rejection_codes)

    def test_stage_mismatch_is_rejected(self) -> None:
        bundle = _bundle(entries=(_entry("e1", "Stage bound.", rank=1),))
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(pipeline_stage="character"),
        )
        self.assertEqual(result.contributions, ())
        self.assertIn("pipeline_stage_mismatch", result.eligibility.rejection_codes)

    def test_unavailable_bundle_omits_lanes(self) -> None:
        bundle = _bundle(
            entries=(_entry("e1", "Unavailable.", rank=1),),
            degradation=BundleDegradation(
                level="unavailable",
                mode="partial_sources",
                deterministic_fallback_used=False,
            ),
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertEqual(result.contributions, ())
        self.assertIn("degradation_unavailable", result.eligibility.rejection_codes)


class LibrarianPackagingDegradationTests(unittest.TestCase):
    def test_deterministic_fallback_bundle_remains_visibly_degraded(self) -> None:
        bundle = _bundle(
            entries=(_entry("e1", "Fallback mediated content.", rank=1),),
            mediation_mode="deterministic_fallback",
            degradation=BundleDegradation(
                level="partial",
                mode="deterministic_fallback",
                deterministic_fallback_used=True,
            ),
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertEqual(len(result.contributions), 1)
        self.assertIn("deterministic_fallback", result.contributions[0].content.lower())
        self.assertTrue(result.contributions[0].provenance.get("deterministic_fallback_used"))

    def test_authoritative_only_skips_projection_duplicate_tiers(self) -> None:
        bundle = _bundle(
            entries=(
                _entry(
                    "live-1",
                    "Live scene state duplicate.",
                    rank=1,
                    authority="authoritative",
                    source_tier="authoritative_live_continuity",
                ),
                _entry("cand-1", "Retrieval candidate remains.", rank=2),
            ),
            mediation_mode="authoritative_only",
            degradation=BundleDegradation(
                level="partial",
                mode="authoritative_only",
                deterministic_fallback_used=False,
            ),
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertEqual(len(result.contributions), 1)
        self.assertEqual(result.contributions[0].contribution_id, "manifest-test-librarian-cand-1")

    def test_storyteller_policy_socket_exists_without_storyteller_implementation(self) -> None:
        policy = policy_for_consumer("storyteller")
        self.assertEqual(policy.consumer_target, "storyteller")
        bundle = _bundle(entries=(_entry("e1", "Future storyteller lane.", rank=1),))
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-test",
            consumer_target="storyteller",
            binding=_binding(),
        )
        self.assertEqual(len(result.contributions), 1)
        for contribution in result.contributions:
            self.assertNotEqual(contribution.source_kind, "director_context")


class LibrarianPackagingCompatibilityTests(unittest.TestCase):
    def test_character_policy_does_not_use_storyteller_lanes(self) -> None:
        binding = _binding(pipeline_stage="character")
        validity = BundleValidity(
            validity_scope="stage_current",
            bound_hg_round_id="round-1",
            bound_turn_index=0,
            bound_pipeline_stage="character",
            valid_from_authoritative_snapshot_id=binding.authoritative_snapshot_id,
            invalidation_keys=(
                InvalidationKey(key_kind="continuity_version", key_value="3"),
                InvalidationKey(key_kind="hg_round_id", key_value="round-1"),
                InvalidationKey(key_kind="pipeline_stage", key_value="character"),
            ),
        )
        bundle = _bundle(
            entries=(
                _entry(
                    "e1",
                    "Character-visible mediated lore.",
                    rank=1,
                    source_tier="retrieval_candidate",
                    visibility_scope="character_scoped",
                ),
            ),
            validity=validity,
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-character-test",
            consumer_target="character",
            binding=binding,
        )
        self.assertEqual(len(result.contributions), 1)
        self.assertIsInstance(result.contributions[0], PromptContribution)


if __name__ == "__main__":
    unittest.main()
