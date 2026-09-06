"""Issue #131 — Narrator presentation manifest deduplication (A+B)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.narrator_environment_contract import EnvironmentalResponseObligation  # noqa: E402
from domain_api.narrator_environment_sufficiency import (  # noqa: E402
    format_environmental_response_obligations,
)


def _commit_alice(kernel: DomainKernel, scene_id: str, rnd_id: str):
    return kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-131",
            hg_scene_id=scene_id,
            hg_round_id=rnd_id,
            character_id="Alice",
            validated_move={
                "move_schema_version": 2,
                "beats": [{"type": "action", "action": "looks around the workshop"}],
            },
            director_decision={
                "next_actor": "Alice",
                "end_round": True,
                "reason": "test",
                "environment_event": "",
                "tension_shift": "",
            },
            expected_turn_index=0,
        )
    )


def _sample_audit(*, n_obligations: int = 2) -> dict:
    obligations = [
        EnvironmentalResponseObligation(
            obligation_id=f"env-obl-{i}",
            need_id=f"need-{i}",
            rendering_question=f"What detail {i}?",
            render_behavior="communicate_grounded",
            grounded_material=(f"grounded detail {i}",),
            resolution_category="A",
            response_sufficient=True,
            mediation_outcome="match",
            sufficiency_state="sufficient",
        )
        for i in range(1, n_obligations + 1)
    ]
    obligation_text = format_environmental_response_obligations(obligations)
    return {
        "cognition_id": "cog-131-test",
        "location_ref": "location:workshop",
        "n1": {
            "baseline_sufficient": False,
            "information_needs": [
                {"need_id": f"need-{i}", "question": f"Q{i}"} for i in range(1, n_obligations + 1)
            ],
        },
        "librarian_queries": [],
        "n2_resolutions": [],
        "establishment_decisions": [],
        "sufficiency_evaluations": [],
        "environmental_response_obligations": [o.to_dict() for o in obligations],
        "environmental_response_obligations_text": obligation_text,
    }


class NarratorPresentationPackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = DomainKernel.for_fixture_store()
        self.scene_id = self.kernel.create_scene().hg_scene_id
        self.rnd_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=self.scene_id)
        ).hg_round_id
        commit = _commit_alice(self.kernel, self.scene_id, self.rnd_id)
        assert commit.committed and commit.domain_commit_id
        self.commit_id = commit.domain_commit_id
        self.turn_idx = commit.continuity_turn_index or 1

    def _prepare(self, audit: dict | None = None):
        return self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-nar-131",
                character_id="Alice",
                domain_commit_id=self.commit_id,
                continuity_turn_index=self.turn_idx,
                attempt_index=0,
                environment_cognition_audit=audit,
            )
        )

    def test_no_cognition_audit_lane_in_presentation_manifest(self) -> None:
        audit = _sample_audit()
        manifest = self._prepare(audit)
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("narrator_environment_cognition", kinds)

    def test_obligation_lane_present_without_instruction_duplication(self) -> None:
        audit = _sample_audit()
        obligation_text = audit["environmental_response_obligations_text"]
        manifest = self._prepare(audit)
        obligation = next(
            c for c in manifest.contributions if c.source_kind == "environmental_response_obligation"
        )
        instruction = next(
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        )
        self.assertEqual(obligation.content, obligation_text)
        self.assertNotIn(obligation_text, instruction.content)
        self.assertIn("environmental response obligations", instruction.content.lower())

    def test_semantic_correction_lane_unchanged_on_retry(self) -> None:
        audit = _sample_audit(n_obligations=1)
        correction = {
            "source": "presentation_fidelity_validation",
            "validation_class": "speech_verbatim",
            "required_speech_dialogues": ["Hello"],
        }
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-nar-131-retry",
                character_id="Alice",
                domain_commit_id=self.commit_id,
                continuity_turn_index=self.turn_idx,
                attempt_index=1,
                environment_cognition_audit=audit,
                correction_context=correction,
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("semantic_correction", kinds)
        self.assertNotIn("narrator_environment_cognition", kinds)

    def test_manifest_size_reduces_materially_with_audit(self) -> None:
        audit = _sample_audit(n_obligations=5)
        manifest = self._prepare(audit)
        total = sum(len(c.content) for c in manifest.contributions)
        obligation = next(
            c for c in manifest.contributions if c.source_kind == "environmental_response_obligation"
        )
        instruction = next(
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        )
        audit_json_len = len(__import__("json").dumps(audit, indent=2))
        self.assertLess(total, audit_json_len + len(obligation.content) + len(instruction.content))
        self.assertLess(len(instruction.content), len(obligation.content) + 5000)


if __name__ == "__main__":
    unittest.main()
