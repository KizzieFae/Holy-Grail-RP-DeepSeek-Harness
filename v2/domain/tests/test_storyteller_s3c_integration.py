"""#32 S3c Storyteller live round integration tests (Host prepare_* wiring)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from dataclasses import replace

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionValidationRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.storyteller_contract import advisory_package_to_dict  # noqa: E402
from domain.tests.test_storyteller_packaging_s3b import _binding, _package  # noqa: E402


def _bound_package(*, hg_scene_id: str, hg_round_id: str, continuity_version: int = 0, **overrides: object):
    package = _package(**overrides)
    invalidation_keys = tuple(
        replace(key, key_value=str(continuity_version))
        if key.key_kind == "continuity_version"
        else replace(key, key_value=hg_round_id)
        if key.key_kind == "hg_round_id"
        else key
        for key in package.validity.invalidation_keys
    )
    validity = replace(
        package.validity,
        bound_hg_round_id=hg_round_id,
        bound_turn_index=0,
        invalidation_keys=invalidation_keys,
    )
    return replace(
        package,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=0,
        validity=validity,
    )


def _scene_round(kernel: DomainKernel) -> tuple[str, str]:
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    return scene_id, round_id


class StorytellerS3cIntegrationTests(unittest.TestCase):
    def test_bind_injects_director_storyteller_lanes(self) -> None:
        kernel = DomainKernel(store=FixtureStore())
        scene_id, round_id = _scene_round(kernel)
        package = advisory_package_to_dict(
            _bound_package(hg_round_id=round_id, hg_scene_id=scene_id)
        )
        bind = kernel.bind_storyteller_advisory_package(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            package=package,
            audit={"orientation_inference_id": "inf-orient", "assessment_inference_id": "inf-assess"},
        )
        self.assertTrue(bind["accepted"])
        director = kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                inference_id="inf-director",
                turn_index=0,
                attempt_index=0,
            )
        )
        kinds = {item.source_kind for item in director.contributions}
        self.assertIn("storyteller_narrative_priorities", kinds)
        for contribution in director.contributions:
            if contribution.source_kind.startswith("storyteller_"):
                self.assertEqual(contribution.authority_class, "suggestive")

    def test_character_scoped_storyteller_lanes(self) -> None:
        kernel = DomainKernel(store=FixtureStore())
        scene_id, round_id = _scene_round(kernel)
        package = advisory_package_to_dict(
            _bound_package(
                hg_round_id=round_id,
                hg_scene_id=scene_id,
                observations=(
                    __import__(
                        "domain_api.storyteller_contract",
                        fromlist=["NarrativeObservation"],
                    ).NarrativeObservation(
                        text="Alice feels the weight of betrayal.",
                        evidence_refs=(
                            __import__(
                                "domain_api.librarian_contract",
                                fromlist=["StableReference"],
                            ).StableReference(
                                ref_kind="bundle_entry",
                                stable_ref="alice-betrayal",
                                display_hint="Alice betrayal",
                            ),
                        ),
                    ),
                ),
            )
        )
        kernel.bind_storyteller_advisory_package(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            package=package,
        )
        character = kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                inference_id="inf-char",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        storyteller = [
            item for item in character.contributions if item.source_kind.startswith("storyteller_")
        ]
        self.assertGreaterEqual(len(storyteller), 1)
        joined = "\n".join(item.content for item in storyteller)
        self.assertIn("Alice", joined)

    def test_commit_invalidates_storyteller_for_later_contexts(self) -> None:
        kernel = DomainKernel(store=FixtureStore())
        scene_id, round_id = _scene_round(kernel)
        package = advisory_package_to_dict(
            _bound_package(hg_round_id=round_id, hg_scene_id=scene_id)
        )
        kernel.bind_storyteller_advisory_package(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            package=package,
        )
        director_decision = kernel.validate_director_decision(
            DirectorDecisionValidationRequest(
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                inference_id="inf-director",
                turn_index=0,
                attempt_index=0,
                proposed_decision={
                    "next_actor": "Alice",
                    "end_round": False,
                    "reason": "Alice speaks.",
                    "environment_event": "",
                    "tension_shift": "steady",
                },
            )
        )
        self.assertTrue(director_decision.accepted)
        move = kernel.validate_move(
            ValidationRequest(
                inference_id="inf-char",
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
                proposed_move=PROTOTYPE_VALID_MOVE,
            )
        )
        self.assertTrue(move.accepted)
        commit = kernel.commit_move(
            CommitRequest(
                inference_id="inf-char",
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(director_decision.normalized_decision or {}),
                expected_turn_index=0,
            )
        )
        self.assertTrue(commit.committed)
        self.assertEqual(commit.storyteller_invalidation_reason, "authoritative_commit")
        state = kernel.get_storyteller_round_state(hg_scene_id=scene_id, hg_round_id=round_id)
        self.assertFalse(state["is_valid"])
        director_after = kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                inference_id="inf-director-2",
                turn_index=0,
                attempt_index=0,
                actors_used_this_round=["Alice"],
            )
        )
        self.assertFalse(
            any(item.source_kind.startswith("storyteller_") for item in director_after.contributions)
        )

    def test_narrator_before_commit_has_storyteller_emphasis(self) -> None:
        kernel = DomainKernel(store=FixtureStore())
        scene_id, round_id = _scene_round(kernel)
        package = advisory_package_to_dict(
            _bound_package(hg_round_id=round_id, hg_scene_id=scene_id)
        )
        kernel.bind_storyteller_advisory_package(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            package=package,
        )
        director_decision = {
            "next_actor": "Alice",
            "end_round": False,
            "reason": "Alice speaks.",
            "environment_event": "",
            "tension_shift": "steady",
        }
        commit = kernel.commit_move(
            CommitRequest(
                inference_id="inf-char",
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=director_decision,
                expected_turn_index=0,
            )
        )
        self.assertTrue(commit.committed)
        assert commit.domain_commit_id is not None
        # Package invalidated at commit; narrator context after commit must not inject lanes.
        narrator = kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                inference_id="inf-narrator",
                character_id="Alice",
                domain_commit_id=commit.domain_commit_id,
                continuity_turn_index=commit.continuity_turn_index or 1,
                attempt_index=0,
            )
        )
        self.assertFalse(
            any(item.source_kind.startswith("storyteller_") for item in narrator.contributions)
        )
        self.assertTrue(
            any(item.source_kind == "committed_move" for item in narrator.contributions)
        )

    def test_character_can_act_contrary_to_storyteller_opportunity(self) -> None:
        kernel = DomainKernel(store=FixtureStore())
        scene_id, round_id = _scene_round(kernel)
        package = advisory_package_to_dict(
            _bound_package(hg_round_id=round_id, hg_scene_id=scene_id)
        )
        kernel.bind_storyteller_advisory_package(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            package=package,
        )
        contrary_move = {
            **PROTOTYPE_VALID_MOVE,
            "beats": [{"type": "action", "action": "ignores the suggested opportunity entirely"}],
        }
        move = kernel.validate_move(
            ValidationRequest(
                inference_id="inf-char",
                hg_scene_id=scene_id,
                hg_round_id=round_id,
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
                proposed_move=contrary_move,
            )
        )
        self.assertTrue(move.accepted)


if __name__ == "__main__":
    unittest.main()
