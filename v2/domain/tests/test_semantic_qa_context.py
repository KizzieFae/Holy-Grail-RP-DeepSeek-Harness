"""Tests for shared semantic-QA context assembly (#25)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import PromptContribution  # noqa: E402
from domain_api.semantic_qa_context import build_semantic_qa_context_response  # noqa: E402


def test_assembly_transports_role_contributions_and_refs_without_rubric() -> None:
    role_contrib = PromptContribution(
        contribution_id="manifest-test-role-context",
        source_kind="scene_state",
        authority_class="authoritative",
        knowledge_ids=("scene:1",),
        priority=10,
        content="Role-provided context only.",
        provenance={"evaluation_pass_id": "eval-pass-1"},
    )
    authority_refs = [
        {
            "ref_id": "continuity_fact:scene:location",
            "kind": "continuity_fact",
            "authority_class": "authoritative",
            "label": "Location",
            "text": "Dorm",
        },
    ]
    response = build_semantic_qa_context_response(
        manifest_id="manifest-semantic-qa-eval-pass-1",
        evaluation_pass_id="eval-pass-1",
        evaluation_target_role="director",
        inference_id="inf-director-1",
        inference_kind="director_semantic_qa",
        hg_scene_id="scene-1",
        hg_round_id="round-1",
        turn_index=0,
        role_contributions=[role_contrib],
        authority_references=authority_refs,
        candidate_package={"candidate_decision": {"next_actor": "Alice"}},
        candidate_label="Director decision candidate",
    )

    assert response.evaluation_target_role == "director"
    assert response.authority_references[0]["authority_class"] == "authoritative"
    assert any(c.contribution_id.endswith("-authority-references") for c in response.contributions)
    assert any(c.contribution_id.endswith("-candidate-package") for c in response.contributions)
    assert any("Role-provided context only." in c.content for c in response.contributions)
    assert all("R02b" not in c.content for c in response.contributions)
