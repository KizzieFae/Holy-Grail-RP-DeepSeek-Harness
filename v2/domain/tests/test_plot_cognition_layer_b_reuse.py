"""#166 Layer B epistemic evaluation reuse and Lane 1 orchestration tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.plot_cognition_layer_b_reuse import (  # noqa: E402
    clear_layer_b_reuse_for_tests,
    compute_layer_b_eval_reuse_key,
    consult_layer_b_reuse,
    store_layer_b_reuse,
)
from domain_api.plot_cognition_orchestration_contract import (  # noqa: E402
    CharacterEpistemicContextEnvelope,
)
from domain_api.plot_cognition_projection_batch import (  # noqa: E402
    clear_prepared_batches_for_tests,
    prepare_character_projection_batch,
)
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    ProjectionBudget,
    overlay_goal_to_character_candidate,
)
from domain_api.plot_cognition_projection_runtime import (  # noqa: E402
    register_projection_semantic_result,
)
from domain_api.plot_cognition_orchestration_api import (  # noqa: E402
    resolve_plot_cognition_layer_b_epistemic_reuse,
)
from domain.tests.test_plot_cognition_orchestration import (  # noqa: E402
    TEST_BUDGET,
    _character_goal,
    _round,
    _session_with_event,
)


def _envelope(**overrides) -> CharacterEpistemicContextEnvelope:
    base = {
        "schema": "hg_character_epistemic_context_envelope_v1",
        "character_id": "Alice",
        "candidate_id": "cand-1",
        "visibility_digest": "vis-digest",
        "withheld_basis_index": ({"facet_id": "f1", "category": "secret", "reason": "unknown"},),
        "known_by_snapshot_id": "kbs-1",
        "overlay_revision": 3,
        "semantic_material": {},
    }
    base.update(overrides)
    return CharacterEpistemicContextEnvelope.from_dict(base)


class LayerBEvalReuseKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_layer_b_reuse_for_tests()
        clear_prepared_batches_for_tests()

    def tearDown(self) -> None:
        clear_layer_b_reuse_for_tests()
        clear_prepared_batches_for_tests()

    def test_reuse_key_stable_for_identical_inputs(self) -> None:
        kwargs = {
            "plot_cognition_scope_id": "scope-1",
            "character_id": "Alice",
            "candidate_id": "cand-1",
            "visibility_digest": "vis",
            "withheld_basis_index": ({"facet_id": "f1", "category": "secret", "reason": "unknown"},),
            "known_by_snapshot_id": "kbs-1",
            "overlay_revision": 2,
            "assimilated_authority_source_fingerprint": "fp-abc",
        }
        first = compute_layer_b_eval_reuse_key(**kwargs)
        second = compute_layer_b_eval_reuse_key(**kwargs)
        self.assertEqual(first, second)

    def test_reuse_key_changes_on_candidate_or_overlay_revision(self) -> None:
        base = {
            "plot_cognition_scope_id": "scope-1",
            "character_id": "Alice",
            "candidate_id": "cand-1",
            "visibility_digest": "vis",
            "withheld_basis_index": (),
            "known_by_snapshot_id": "kbs-1",
            "overlay_revision": 2,
            "assimilated_authority_source_fingerprint": "fp-abc",
        }
        original = compute_layer_b_eval_reuse_key(**base)
        self.assertNotEqual(
            original,
            compute_layer_b_eval_reuse_key(**{**base, "candidate_id": "cand-2"}),
        )
        self.assertNotEqual(
            original,
            compute_layer_b_eval_reuse_key(**{**base, "overlay_revision": 3}),
        )
        self.assertNotEqual(
            original,
            compute_layer_b_eval_reuse_key(
                **{**base, "assimilated_authority_source_fingerprint": "fp-changed"}
            ),
        )

    def test_registry_hit_after_register_first_pass(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        shared_candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-reuse",
            character_id="Alice",
            candidates=(shared_candidate,),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-assimilated",
            overlay_revision=4,
        )
        item = prepared.batch.items[0]
        semantic = {
            "verdict": "pass",
            "rationale": "ok",
            "leak_indicators": [],
        }
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw=semantic,
            inference_evidence_id="ev-layer-b-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        prepared_again = prepare_character_projection_batch(
            fixture,
            manifest_id="m-reuse-2",
            character_id="Alice",
            candidates=(shared_candidate,),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-assimilated",
            overlay_revision=4,
        )
        item2 = prepared_again.batch.items[0]
        class _Kernel:
            cognition = type("Cognition", (), {"plot_cognition_overlay": None})()

        resolved = resolve_plot_cognition_layer_b_epistemic_reuse(
            _Kernel(),
            fixture,
            rnd,
            {
                "batch_id": prepared_again.batch.batch_id,
                "evaluation_pass_id": item2.evaluation_pass_id,
                "evaluation_attempt": 1,
            },
        )
        self.assertTrue(resolved["accepted"])
        self.assertEqual(resolved["action"], "reuse")
        self.assertEqual(resolved["prior_inference_evidence_id"], "ev-layer-b-1")

    def test_regeneration_attempt_forces_invoke(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-regen",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-assimilated",
        )
        item = prepared.batch.items[0]
        store_layer_b_reuse(
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            reuse_key_digest="dummy",
            semantic={"verdict": "pass"},
            inference_evidence_id="ev-old",
        )

        class _Kernel:
            cognition = type("Cognition", (), {"plot_cognition_overlay": None})()

        resolved = resolve_plot_cognition_layer_b_epistemic_reuse(
            _Kernel(),
            fixture,
            rnd,
            {
                "batch_id": prepared.batch.batch_id,
                "evaluation_pass_id": item.evaluation_pass_id,
                "evaluation_attempt": 2,
            },
        )
        self.assertEqual(resolved["action"], "invoke")
        self.assertEqual(resolved["reason"], "regeneration_or_second_pass_requires_fresh_eval")
