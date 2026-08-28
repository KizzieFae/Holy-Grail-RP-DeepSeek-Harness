"""Tests for semantic evaluation context preparation (#19)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    RoundStartRequest,
    SemanticEvaluationContextPrepareRequest,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.semantic_evaluation_context import (  # noqa: E402
    PLAYER_AGENCY_GUARDRAIL_ID,
    build_authority_references,
)


def test_authority_references_include_player_agency_guardrail() -> None:
    class _State:
        location = "Dorm"
        present_characters = ["Alice"]
        character_presence_constraints = {}
        sleeping_surface_slots = []

    class _Mgr:
        scene_state = _State()

        def get_relevant_canon_anchors(self, *_args, **_kwargs):
            return []

    class _Fixture:
        manager = _Mgr()
        cast = ["Alice"]
        character_states = {}

    refs = build_authority_references(_Fixture(), character_id="Alice", hg_round_id="r1")
    ref_ids = {ref["ref_id"] for ref in refs}
    assert PLAYER_AGENCY_GUARDRAIL_ID in ref_ids


@pytest.fixture()
def kernel() -> DomainKernel:
    k = DomainKernel.for_fixture_store()
    scene = k.create_scene(cast=["Alice"], location="Dorm")
    k.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    return k


def test_prepare_semantic_evaluation_context_kernel_shape(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    assert fixture.rounds
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = fixture.rounds[-1].hg_round_id
    req = SemanticEvaluationContextPrepareRequest(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        inference_id="inf-test",
        character_id="Alice",
        role="guest",
        turn_index=0,
        evaluation_pass_id="eval-pass-1",
        candidate_move={
            "move_schema_version": 2,
            "beats": [{"type": "action", "action": "nods"}],
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "e",
                "risk_level": "low",
            },
            "semantic_evaluation": {"decision": "no_covered_change"},
        },
        raw_model_output='{"move_schema_version":2}',
    )
    response = kernel.prepare_semantic_evaluation_context(req)
    assert response.manifest_id.startswith("manifest-semantic-eval-")
    assert response.evaluation_pass_id == "eval-pass-1"
    assert len(response.authority_references) >= 1
    assert any(ref["ref_id"] == PLAYER_AGENCY_GUARDRAIL_ID for ref in response.authority_references)
    assert response.candidate_package["candidate_move"]["move_schema_version"] == 2
