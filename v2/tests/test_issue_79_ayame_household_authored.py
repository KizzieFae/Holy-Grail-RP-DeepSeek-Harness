"""Issue #79 — Ayame household authored scenario alignment tests."""

from __future__ import annotations

import json
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
    OpeningPerceptualVisibilityAttachRequest,
    RoundStartRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_setup import (  # noqa: E402
    _materialize_role_private_secrets,
    _merge_character_private_secret,
)
from domain_api.setup_catalog import list_template_openers_catalog  # noqa: E402
from scene_template import SceneTemplate, SceneTemplateManager  # noqa: E402

HOST_PRIVATE_MARKER = "engineered the chain of events"
SHARED_PREMISE_MARKER = "scheduled household interview"
ORCHESTRATION_LEAK = "steered toward live-in domestic employment under the host's control"
OPENER_MARKER = "still telling yourself your streak of misfortune had been nothing but bad luck"


class Issue79AyameHouseholdAuthoredTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_ayame_household_session(
        self,
        *,
        host_file: str = "ayame",
        applicant_file: str = "kizzie",
    ) -> tuple[str, str, str]:
        openers = list_template_openers_catalog("ayame_household_entry_evaluation")
        self.assertTrue(openers)
        opener_id = openers[0]["opener_id"]
        info = self.kernel.create_session(
            characters=[host_file, applicant_file],
            scene_template_id="ayame_household_entry_evaluation",
            role_assignments={
                host_file: "host",
                applicant_file: "applicant",
            },
            opening={"mode": "template", "opener_id": opener_id},
        )
        fixture = self.repo.require(info.hg_session_id)
        host_name = fixture.setup_snapshot["names_by_file"][host_file]
        applicant_name = fixture.setup_snapshot["names_by_file"][applicant_file]
        self.kernel.attach_opening_perceptual_visibility(
            OpeningPerceptualVisibilityAttachRequest(
                hg_session_id=info.hg_session_id,
                perceptual_visibility={
                    "units": [
                        {
                            "unit_id": "public_mansion",
                            "kind": "observable_scene",
                            "text": (
                                "The interview had been scheduled almost at once. Now you stood at the entrance "
                                "to a mansion that looked too polished, too quiet, and too expensive to belong to your life. "
                                "Somewhere inside, Ayame Suzuki waited to conduct what was supposed to be an ordinary household interview."
                            ),
                            "recipients": {"scope": "public"},
                        },
                        {
                            "unit_id": "applicant_internal",
                            "kind": "internal",
                            "text": (
                                "It had been a horrible week. You had lost your job, then your apartment, "
                                "and desperation was starting to feel like a second skin."
                            ),
                            "recipients": {"scope": "private", "characters": [applicant_name]},
                        },
                        {
                            "unit_id": "applicant_closer",
                            "kind": "internal",
                            "text": (
                                "You lifted your hand toward the door, still telling yourself your streak of misfortune "
                                "had been nothing but bad luck."
                            ),
                            "recipients": {"scope": "private", "characters": [applicant_name]},
                        },
                    ]
                },
            )
        )
        return info.hg_session_id, host_name, applicant_name

    def _character_manifest(self, session_id: str, *, character_id: str):
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        return self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id=f"inf-{character_id.lower()}-79",
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )

    def test_template_parses_role_private_knowledge(self) -> None:
        template = SceneTemplateManager().load_template("ayame_household_entry_evaluation")
        self.assertIn("host", template.role_private_knowledge)
        self.assertIn(HOST_PRIVATE_MARKER, template.role_private_knowledge["host"])
        serialized = template.to_dict()
        self.assertIn("role_private_knowledge", serialized)
        self.assertIn(HOST_PRIVATE_MARKER, serialized["role_private_knowledge"]["host"])

    def test_legacy_template_without_role_private_knowledge_still_loads(self) -> None:
        tmp_path = Path(self._tmpdir) / "templates"
        tmp_path.mkdir()
        payload = {
            "template_id": "legacy_no_private",
            "cohesion_policy": "anchor_only",
            "anchor_role_name": "guest",
            "premise": "A simple room.",
            "role_slots": [
                {"role_name": "guest", "required": True},
            ],
        }
        (tmp_path / "legacy_no_private.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        template = SceneTemplateManager(tmp_path).load_template("legacy_no_private")
        self.assertEqual(template.role_private_knowledge, {})

    def test_template_snapshot_preserves_role_private_knowledge(self) -> None:
        session_id, _, _ = self._create_ayame_household_session()
        snapshot = self.repo.require(session_id).setup_snapshot
        template = snapshot.get("scene_template") or {}
        self.assertIn("role_private_knowledge", template)
        self.assertIn(HOST_PRIVATE_MARKER, template["role_private_knowledge"]["host"])

    def test_role_assignment_resolves_host_and_applicant(self) -> None:
        session_id, host_name, applicant_name = self._create_ayame_household_session()
        fixture = self.repo.require(session_id)
        roles = fixture.manager.scene_state.role_assignments
        self.assertEqual(roles.get(host_name), "host")
        self.assertEqual(roles.get(applicant_name), "applicant")

    def test_ayame_receives_host_private_orchestration_knowledge(self) -> None:
        session_id, host_name, _ = self._create_ayame_household_session()
        secret = self.repo.require(session_id).character_private_secrets[host_name]
        self.assertIn(HOST_PRIVATE_MARKER, secret)
        manifest = self._character_manifest(session_id, character_id=host_name)
        private = next(
            c for c in manifest.contributions if c.source_kind == "character_private"
        )
        self.assertIn(HOST_PRIVATE_MARKER, private.content)

    def test_kizzie_does_not_receive_host_private_orchestration_knowledge(self) -> None:
        session_id, host_name, applicant_name = self._create_ayame_household_session()
        host_secret = self.repo.require(session_id).character_private_secrets[host_name]
        manifest = self._character_manifest(session_id, character_id=applicant_name)
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("character_private", kinds)
        for contribution in manifest.contributions:
            self.assertNotIn(host_secret, contribution.content)
            self.assertNotIn(ORCHESTRATION_LEAK, contribution.content)

    def test_both_receive_shared_premise_not_private_causation(self) -> None:
        session_id, host_name, applicant_name = self._create_ayame_household_session()
        for character_id in (host_name, applicant_name):
            manifest = self._character_manifest(session_id, character_id=character_id)
            scene_context = next(
                c for c in manifest.contributions if c.source_kind == "scene_context"
            )
            self.assertIn(SHARED_PREMISE_MARKER, scene_context.content)
            self.assertNotIn(HOST_PRIVATE_MARKER, scene_context.content)
            self.assertNotIn(ORCHESTRATION_LEAK, scene_context.content)

    def test_opener_in_transcript_not_scene_setup(self) -> None:
        session_id, _, applicant_name = self._create_ayame_household_session()
        manifest = self._character_manifest(session_id, character_id=applicant_name)
        transcript = next(
            c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
        )
        self.assertIn(OPENER_MARKER, transcript.content)
        scene_context = next(
            c for c in manifest.contributions if c.source_kind == "scene_context"
        )
        self.assertNotIn(OPENER_MARKER, scene_context.content)

    def test_director_excludes_character_private(self) -> None:
        session_id, host_name, _ = self._create_ayame_household_session()
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        director = self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-director-79",
                turn_index=0,
                attempt_index=0,
            )
        )
        host_secret = self.repo.require(session_id).character_private_secrets[host_name]
        self.assertNotIn(
            "character_private",
            {c.source_kind for c in director.contributions},
        )
        for contribution in director.contributions:
            self.assertNotIn(host_secret, contribution.content)

    def test_host_private_knowledge_follows_role_assignment_not_character_name(self) -> None:
        session_id, host_name, _ = self._create_ayame_household_session(
            host_file="willow",
            applicant_file="kizzie",
        )
        self.assertNotEqual(host_name, "Ayame")
        secret = self.repo.require(session_id).character_private_secrets[host_name]
        self.assertIn(HOST_PRIVATE_MARKER, secret)
        ayame_secret = self.repo.require(session_id).character_private_secrets.get("Ayame")
        self.assertIsNone(ayame_secret)

    def test_merge_preserves_card_and_scenario_private_knowledge(self) -> None:
        secrets = {"Host": "CARD_PRIVATE_MEMORY"}
        _materialize_role_private_secrets(
            role_private_knowledge={"host": "SCENARIO_PRIVATE_FACT"},
            role_assignments_by_file={"host_file": "host"},
            names_by_file={"host_file": "Host"},
            secrets=secrets,
        )
        self.assertEqual(
            secrets["Host"],
            _merge_character_private_secret("CARD_PRIVATE_MEMORY", "SCENARIO_PRIVATE_FACT"),
        )


if __name__ == "__main__":
    unittest.main()
