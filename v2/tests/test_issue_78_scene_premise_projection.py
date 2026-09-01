"""Issue #78 — persistent scenario premise projection separate from opener."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import (  # noqa: E402
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    OpeningContextPrepareRequest,
    OpeningPerceptualVisibilityAttachRequest,
    RoundStartRequest,
)
from domain_api.continuity_context_projector import (  # noqa: E402
    project_authoritative_context,
    project_scene_setup,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.setup_catalog import list_template_openers_catalog  # noqa: E402


class Issue78ScenePremiseProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _template_session_with_opener(self) -> tuple[str, str, str]:
        openers = list_template_openers_catalog("celina_apartment_recovery_watch")
        self.assertTrue(openers)
        opener_id = openers[0]["opener_id"]
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "template", "opener_id": opener_id},
        )
        fixture = self.repo.require(info.hg_session_id)
        assert fixture.manager.scene_state is not None
        premise = str(fixture.manager.scene_state.scene_premise or "").strip()
        opener = str(fixture.manager.scene_state.opening_description or "").strip()
        self.assertTrue(premise)
        self.assertTrue(opener)
        self.assertNotEqual(premise, opener)
        protector_name = fixture.setup_snapshot["names_by_file"]["willow"]
        demi_name = fixture.setup_snapshot["names_by_file"]["kizzie"]
        self.kernel.attach_opening_perceptual_visibility(
            OpeningPerceptualVisibilityAttachRequest(
                hg_session_id=info.hg_session_id,
                perceptual_visibility={
                    "units": [
                        {
                            "unit_id": "public_opener",
                            "kind": "observable_scene",
                            "text": (
                                "Walking out of one of her boss's hotels, Celina was immediately hit "
                                "with wind-driven rain splashing directly into her face."
                            ),
                            "recipients": {"scope": "public"},
                        },
                        {
                            "unit_id": "protector_internal",
                            "kind": "internal",
                            "text": "For a moment, Celina considered walking on. Not her problem.",
                            "recipients": {"scope": "private", "characters": [protector_name]},
                        },
                    ]
                },
            )
        )
        return info.hg_session_id, premise, opener

    def test_scene_setup_uses_premise_not_opener(self) -> None:
        session_id, premise, opener = self._template_session_with_opener()
        fixture = self.repo.require(session_id)
        setup = project_scene_setup(
            fixture,
            hg_scene_id=session_id,
            hg_round_id="round-78",
        )
        assert setup is not None
        self.assertIn(premise, setup.content)
        self.assertNotIn(opener, setup.content)
        self.assertIn("persistent scenario premise", setup.content.lower())

    def test_opener_change_does_not_change_scene_setup(self) -> None:
        session_id, premise, opener = self._template_session_with_opener()
        fixture = self.repo.require(session_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.opening_description = (
            "A wholly different opener that must not alter projected premise."
        )
        self.assertNotEqual(fixture.manager.scene_state.opening_description, opener)
        setup = project_scene_setup(
            fixture,
            hg_scene_id=session_id,
            hg_round_id="round-78",
        )
        assert setup is not None
        self.assertIn(premise, setup.content)
        self.assertNotIn(
            "A wholly different opener that must not alter projected premise.",
            setup.content,
        )

    def test_character_scene_context_embeds_premise_not_opener_lane(self) -> None:
        session_id, premise, opener = self._template_session_with_opener()
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-kizzie-78",
                character_id="Kizzie",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("scene_setup", kinds)
        scene_context = next(c for c in manifest.contributions if c.source_kind == "scene_context")
        self.assertIn(premise, scene_context.content)
        self.assertNotIn(opener, scene_context.content)
        transcript = next(
            c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
        )
        self.assertIn("Walking out of one of her boss", transcript.content)

    def test_director_and_narrator_receive_persistent_premise_scene_setup(self) -> None:
        session_id, premise, opener = self._template_session_with_opener()
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        director = self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-director-78",
                turn_index=0,
                attempt_index=0,
            )
        )
        director_setup = next(
            c for c in director.contributions if c.source_kind == "scene_setup"
        )
        self.assertIn(premise, director_setup.content)
        self.assertNotIn(opener, director_setup.content)

        fixture = self.repo.require(session_id)
        narrator_projections = project_authoritative_context(
            fixture,
            role="narrator",
            hg_scene_id=session_id,
            hg_round_id=round_id,
            character_id="Kizzie",
            continuity_turn_index=0,
        )
        narrator_setup = next(p for p in narrator_projections if p.source_kind == "scene_setup")
        self.assertIn(premise, narrator_setup.content)
        self.assertNotIn(opener, narrator_setup.content)

    def test_cast_only_empty_premise_has_no_scene_setup(self) -> None:
        session_id = self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id
        fixture = self.repo.require(session_id)
        setup = project_scene_setup(
            fixture,
            hg_scene_id=session_id,
            hg_round_id="round-78",
        )
        self.assertIsNone(setup)
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        director = self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-director-cast",
                turn_index=0,
                attempt_index=0,
            )
        )
        self.assertNotIn(
            "scene_setup",
            {c.source_kind for c in director.contributions},
        )

    def test_minimal_opening_projects_premise_not_opener_as_setup(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "minimal"},
        )
        fixture = self.repo.require(info.hg_session_id)
        assert fixture.manager.scene_state is not None
        premise = str(fixture.manager.scene_state.scene_premise or "").strip()
        opening = str(fixture.manager.scene_state.opening_description or "").strip()
        self.assertTrue(premise)
        setup = project_scene_setup(
            fixture,
            hg_scene_id=info.hg_session_id,
            hg_round_id="round-78",
        )
        assert setup is not None
        self.assertIn(premise, setup.content)
        if opening != premise:
            self.assertNotIn(opening, setup.content)

    def test_opening_bootstrap_dedup_when_scene_setup_present(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "minimal"},
        )
        manifest = self.kernel.prepare_opening_context(
            OpeningContextPrepareRequest(
                hg_session_id=info.hg_session_id,
                inference_id="inf-opening-78",
            )
        )
        kinds = [c.source_kind for c in manifest.contributions]
        self.assertIn("scene_setup", kinds)
        self.assertNotIn("scene_reference", kinds)

    def test_generated_opening_keeps_scene_reference_without_scene_setup(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "generated"},
        )
        manifest = self.kernel.prepare_opening_context(
            OpeningContextPrepareRequest(
                hg_session_id=info.hg_session_id,
                inference_id="inf-opening-generated-78",
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("scene_setup", kinds)
        self.assertIn("scene_reference", kinds)


if __name__ == "__main__":
    unittest.main()
