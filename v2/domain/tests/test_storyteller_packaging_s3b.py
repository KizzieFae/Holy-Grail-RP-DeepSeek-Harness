"""#32 S3b Storyteller advisory package → Packaging mapper tests."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import PromptContribution  # noqa: E402
from domain_api.librarian_contract import InvalidationKey, StableReference  # noqa: E402
from domain_api.librarian_packaging_validity import PackagingBindingContext  # noqa: E402
from domain_api.storyteller_contract import (  # noqa: E402
    AssessmentValidity,
    NarrativeObservation,
    NarrativePriority,
    NarrativeTension,
    ProgressionOpportunity,
    StorytellerAdvisoryPackage,
    StorytellerAuditRecord,
    StorytellerBundleRefs,
    StorytellerDegradation,
    UnresolvedThread,
    invalidate_storyteller_package,
)
from domain_api.storyteller_packaging_mapper import map_storyteller_package_to_contributions  # noqa: E402
from domain_api.storyteller_packaging_policy import policy_for_storyteller_consumer  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain_api.plot_cognition_projection_contract import MODEL_A_CHARACTER_SCOPE_REF_KIND  # noqa: E402


def _character_scope_ref(character_id: str) -> StableReference:
    return StableReference(
        ref_kind=MODEL_A_CHARACTER_SCOPE_REF_KIND,
        stable_ref=character_id,
    )


def _fixture():
    return initialize_live_session(cast=["Alice", "Bob"], plot_cognition_scope_id="scope-s3b-test")


def _binding(**overrides: object) -> PackagingBindingContext:
    base = PackagingBindingContext(
        hg_round_id="round-1",
        turn_index=0,
        pipeline_stage="director",
        continuity_version=3,
        authoritative_snapshot_id="snap-1",
    )
    if not overrides:
        return base
    return PackagingBindingContext(**{**base.__dict__, **overrides})


def _ref(stable_ref: str, *, display_hint: str | None = None) -> StableReference:
    return StableReference(ref_kind="bundle_entry", stable_ref=stable_ref, display_hint=display_hint)


def _package(**overrides: object) -> StorytellerAdvisoryPackage:
    package = StorytellerAdvisoryPackage(
        schema="hg_storyteller_advisory_package_v1",
        package_id="pkg-test-1",
        assessment_id="assess-1",
        orientation_id="orient-1",
        hg_scene_id="scene-1",
        hg_round_id="round-1",
        turn_index=0,
        computed_at_stage="round_start",
        validity=AssessmentValidity(
            bound_hg_round_id="round-1",
            bound_turn_index=0,
            valid_from_authoritative_snapshot_id="snap-1",
            invalidation_keys=(
                InvalidationKey(key_kind="continuity_version", key_value="3"),
                InvalidationKey(key_kind="hg_round_id", key_value="round-1"),
            ),
            is_valid=True,
        ),
        bundle_refs=StorytellerBundleRefs(
            primary_request_id="req-1",
            primary_bundle_id="bundle-1",
        ),
        evidence_refs=(_ref("entry-1"),),
        observations=(
            NarrativeObservation(
                text="Alice's trust fracture is thematically central.",
                evidence_refs=(_ref("entry-1", display_hint="Alice trust"),),
            ),
        ),
        active_tensions=(
            NarrativeTension(
                label="Betrayal strain",
                interpretive_note="Unresolved betrayal creates pressure without forcing confrontation.",
                evidence_refs=(_ref("entry-1"),),
            ),
        ),
        narrative_priorities=(
            NarrativePriority(
                focus="Trust fracture",
                why_it_matters="Actors may attend to whether reconciliation or avoidance becomes meaningful.",
                evidence_refs=(_ref("entry-1"),),
            ),
            NarrativePriority(
                focus="Hidden passage",
                why_it_matters="Secrecy may shape how allies respond.",
                evidence_refs=(_ref("entry-2"),),
            ),
        ),
        progression_opportunities=(
            ProgressionOpportunity(
                opportunity_label="Confrontation or avoidance",
                narrative_hook="The betrayal creates an opportunity for either path to become meaningful.",
                evidence_refs=(_ref("entry-1"),),
            ),
        ),
        unresolved_threads=(
            UnresolvedThread(
                thread_label="Broken treaty seal",
                neglect_risk="May fade if not referenced again.",
                evidence_refs=(_ref("entry-1"),),
            ),
        ),
        uncertainty=(),
        information_gaps=(),
        degradation=StorytellerDegradation(level="none", mode="none"),
        audit=StorytellerAuditRecord(
            orientation_inference_id="inf-orient",
            assessment_inference_id="inf-assess",
            inference_ids=("inf-orient", "inf-assess"),
            librarian_request_ids=("req-1",),
            librarian_bundle_ids=("bundle-1",),
        ),
        preservation_signals=(),
    )
    if overrides:
        return StorytellerAdvisoryPackage(**{**package.__dict__, **overrides})
    return package


class StorytellerDirectorPackagingTests(unittest.TestCase):
    def test_maps_priorities_tensions_and_opportunities_suggestively(self) -> None:
        result = map_storyteller_package_to_contributions(
            _package(),
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertTrue(result.eligibility.accepted)
        self.assertGreaterEqual(len(result.contributions), 3)
        kinds = {item.source_kind for item in result.contributions}
        self.assertIn("storyteller_narrative_priorities", kinds)
        self.assertIn("storyteller_active_tensions", kinds)
        self.assertIn("storyteller_progression_opportunities", kinds)
        for contribution in result.contributions:
            self.assertEqual(contribution.authority_class, "suggestive")
            self.assertNotEqual(contribution.source_kind, "director_context")
            lowered = contribution.content.lower()
            self.assertTrue(
                "advisory" in lowered or "possibility" in lowered or "attend to" in lowered,
                contribution.content,
            )

    def test_invalid_package_maps_nothing(self) -> None:
        invalidated = invalidate_storyteller_package(_package(), reason="authoritative_commit")
        result = map_storyteller_package_to_contributions(
            invalidated,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertEqual(result.contributions, ())
        self.assertFalse(result.eligibility.accepted)
        self.assertIn("invalidated", result.eligibility.rejection_codes[0])

    def test_no_actor_selection_fields_in_mapped_content(self) -> None:
        bad = _package(
            narrative_priorities=(
                NarrativePriority(
                    focus="Alice must act next",
                    why_it_matters="Required action for plot.",
                    evidence_refs=(_ref("entry-1"),),
                ),
            )
        )
        result = map_storyteller_package_to_contributions(
            bad,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        for contribution in result.contributions:
            self.assertNotIn("next_actor", contribution.content.lower())
            self.assertNotIn("required action", contribution.content.lower())


class StorytellerCharacterPackagingTests(unittest.TestCase):
    def test_character_scoping_omits_unscoped_advice(self) -> None:
        package = _package(
            observations=(
                NarrativeObservation(
                    text="Global scene mood is tense.",
                    evidence_refs=(_ref("scene-mood"),),
                ),
                NarrativeObservation(
                    text="Alice feels the weight of betrayal.",
                    evidence_refs=(
                        _character_scope_ref("Alice"),
                        _ref("alice-betrayal", display_hint="Alice betrayal"),
                    ),
                ),
            ),
            active_tensions=(
                NarrativeTension(
                    label="Bob distance",
                    interpretive_note="Bob is pulling away from Alice.",
                    evidence_refs=(_character_scope_ref("Alice"), _ref("bob-alice")),
                ),
            ),
            progression_opportunities=(
                ProgressionOpportunity(
                    opportunity_label="Alice reconciliation",
                    narrative_hook="Alice could seek clarity if she chooses.",
                    evidence_refs=(_character_scope_ref("Alice"), _ref("alice-hook")),
                ),
            ),
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="manifest-character",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Alice",
            fixture=_fixture(),
        )
        contents = "\n".join(item.content for item in result.contributions)
        self.assertIn("Alice", contents)
        self.assertNotIn("Global scene mood", contents)
        for contribution in result.contributions:
            self.assertEqual(contribution.authority_class, "suggestive")
            self.assertIn(
                contribution.source_kind,
                {
                    "storyteller_thematic_context",
                    "storyteller_active_tensions",
                    "storyteller_progression_hooks",
                },
            )
            self.assertNotIn("dialogue", contribution.content.lower())
            self.assertNotIn("must say", contribution.content.lower())

    def test_character_without_scope_maps_nothing(self) -> None:
        result = map_storyteller_package_to_contributions(
            _package(),
            manifest_id="manifest-character",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Bob",
            fixture=_fixture(),
        )
        self.assertEqual(result.contributions, ())


class StorytellerNarratorPackagingTests(unittest.TestCase):
    def test_narrator_emphasis_guidance_is_suggestive(self) -> None:
        result = map_storyteller_package_to_contributions(
            _package(),
            manifest_id="manifest-narrator",
            consumer_target="narrator",
            binding=_binding(pipeline_stage="narrator"),
        )
        self.assertGreaterEqual(len(result.contributions), 1)
        for contribution in result.contributions:
            self.assertEqual(contribution.source_kind, "storyteller_emphasis_guidance")
            self.assertEqual(contribution.authority_class, "suggestive")
            self.assertNotIn("structured_move", contribution.content.lower())
            self.assertNotIn("dialogue", contribution.content.lower())


class StorytellerPackagingGeneralTests(unittest.TestCase):
    def test_preserves_storyteller_order_within_categories(self) -> None:
        package = _package(
            narrative_priorities=(
                NarrativePriority(
                    focus="First priority",
                    why_it_matters="First matters.",
                    evidence_refs=(_ref("entry-1"),),
                ),
                NarrativePriority(
                    focus="Second priority",
                    why_it_matters="Second matters.",
                    evidence_refs=(_ref("entry-2"),),
                ),
            )
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        priority_contribs = [
            item for item in result.contributions if item.source_kind == "storyteller_narrative_priorities"
        ]
        self.assertGreaterEqual(len(priority_contribs), 2)
        self.assertIn("First priority", priority_contribs[0].content)
        self.assertIn("Second priority", priority_contribs[1].content)
        self.assertLess(priority_contribs[0].priority, priority_contribs[1].priority)

    def test_provenance_preserved(self) -> None:
        result = map_storyteller_package_to_contributions(
            _package(),
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        contribution = result.contributions[0]
        self.assertEqual(contribution.provenance.get("package_id"), "pkg-test-1")
        self.assertEqual(contribution.provenance.get("bundle_id"), "bundle-1")
        self.assertEqual(contribution.provenance.get("projection_kind"), "storyteller_packaging_mapper")
        self.assertEqual(contribution.provenance.get("binding_level"), "advisory")

    def test_degraded_package_maps_with_degradation_visible(self) -> None:
        package = _package(
            degradation=StorytellerDegradation(level="partial", mode="librarian_degraded", detail="partial_sources"),
            uncertainty=(  # type: ignore[arg-type]
                __import__(
                    "domain_api.storyteller_contract",
                    fromlist=["UncertaintyRecord"],
                ).UncertaintyRecord(
                    topic="Hidden passage danger",
                    reason="Bundle incomplete.",
                ),
            ),
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        self.assertGreater(len(result.contributions), 0)
        joined = "\n".join(item.content for item in result.contributions)
        self.assertIn("degradation", joined.lower())

    def test_preservation_signals_not_mapped_to_consumer_lanes(self) -> None:
        signal = __import__(
            "domain_api.storyteller_contract",
            fromlist=["PreservationSignal"],
        ).PreservationSignal(
            signal_id="sig-1",
            subject_label="Broken treaty seal",
            narrative_significance_note="May matter later to the story.",
            attention_refs=(_ref("entry-1"),),
        )
        package = _package(preservation_signals=(signal,))
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
        )
        joined = "\n".join(item.content for item in result.contributions)
        self.assertNotIn("PreservationSignal", joined)
        self.assertNotIn("persistence", joined.lower())

    def test_policy_caps_are_deterministic(self) -> None:
        policy = policy_for_storyteller_consumer("director")
        priorities = tuple(
            NarrativePriority(
                focus=f"Priority {index}",
                why_it_matters=f"Why {index}",
                evidence_refs=(_ref(f"entry-{index}"),),
            )
            for index in range(6)
        )
        package = _package(narrative_priorities=priorities)
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="manifest-director",
            consumer_target="director",
            binding=_binding(),
            policy=policy,
        )
        mapped_priorities = [
            item for item in result.contributions if item.source_kind == "storyteller_narrative_priorities"
        ]
        self.assertLessEqual(len(mapped_priorities), policy.max_priorities)


if __name__ == "__main__":
    unittest.main()
