"""M11.3 authoritative scene grounding and canon context projection tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
_RP_APP = _ROOT / "autogen_rp" / "python" / "rp_app"
for path in (_V2, _RP_APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    RoundStartRequest,
)
from domain_api.continuity_context_projector import project_authoritative_context  # noqa: E402
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.knowledge_write_policy import upsert_canon_anchor_for_test  # noqa: E402
from domain_api.scope_knowledge_repository import LEARNED_WORLD_KNOWLEDGE  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class ContinuityContextM113Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_session(self) -> str:
        return self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id

    def _start_round(self, session_id: str) -> str:
        return self.kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id

    def _prepare_character(self, session_id: str, *, character_id: str = "Alice"):
        round_id = self._start_round(session_id)
        return self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id=f"inf-{character_id.lower()}",
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )

    def _prepare_director(self, session_id: str):
        round_id = self._start_round(session_id)
        return self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-director",
                turn_index=0,
                attempt_index=0,
            )
        )

    def test_canon_anchor_projects_as_authoritative_continuity_canon(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_bridge",
            statement="The bridge is closed.",
        )
        manifest = self._prepare_character(session_id)
        canon = next(c for c in manifest.contributions if c.source_kind == "continuity_canon")
        self.assertEqual(canon.authority_class, "authoritative")
        self.assertIn("bridge is closed", canon.content.lower())
        self.assertIn("live_continuity_projection", canon.provenance["authority_note"])

    def test_mid_session_scene_mutation_reflects_immediately(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.location = "Storm Harbor"
        manifest = self._prepare_character(session_id)
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        self.assertIn("storm harbor", scene.content.lower())

    def test_scene_mutation_does_not_write_knowledge_scope_store(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_gate",
            statement="The gate is sealed.",
        )
        round_id = self._start_round(session_id)
        self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-alice",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        before = len(
            self.repo.scope_knowledge_repo.list_records(
                fixture.memory_scope_id,
                knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
            )
        )
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.location = "Changed Pier"
        self._prepare_character(session_id)
        after = len(
            self.repo.scope_knowledge_repo.list_records(
                fixture.memory_scope_id,
                knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
            )
        )
        self.assertEqual(before, after)

    def test_authoritative_canon_outranks_stale_learned_world_knowledge(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_weather",
            statement="It is raining.",
        )
        round_id = self._start_round(session_id)
        self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-alice",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_weather",
            statement="The storm has passed.",
        )
        self.repo.persist(fixture)
        manifest = self._prepare_character(session_id)
        canon = next(c for c in manifest.contributions if c.source_kind == "continuity_canon")
        learned = [
            c for c in manifest.contributions if c.source_kind == "learned_world_knowledge"
        ]
        self.assertIn("storm has passed", canon.content.lower())
        self.assertFalse(any("raining" in c.content.lower() for c in learned))

    def test_character_canon_visibility_is_filtered(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_alice",
            subject="Alice",
            category="character_trait",
            statement="Alice keeps a coded journal.",
        )
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_world",
            category="world_fact",
            statement="The harbor lights are out.",
        )
        alice = self._prepare_character(session_id, character_id="Alice")
        bob = self._prepare_character(session_id, character_id="Bob")
        alice_canon = next(c for c in alice.contributions if c.source_kind == "continuity_canon")
        bob_canon = next(c for c in bob.contributions if c.source_kind == "continuity_canon")
        self.assertIn("coded journal", alice_canon.content.lower())
        self.assertNotIn("coded journal", bob_canon.content.lower())
        self.assertIn("harbor lights", bob_canon.content.lower())

    def test_director_receives_authoritative_lanes_with_canon(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_director",
            statement="The market square is cordoned off.",
        )
        manifest = self._prepare_director(session_id)
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("scene_state", kinds)
        self.assertIn("continuity_canon", kinds)

    def test_authoritative_projection_survives_repository_restart(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_restart",
            statement="The lighthouse still stands.",
        )
        self.repo.persist(fixture)
        self.repo.clear_cache()
        restarted = SessionRepository(self._tmpdir)
        restarted_kernel = DomainKernel(repository=restarted)
        manifest = self._prepare_character(session_id)
        canon = next(c for c in manifest.contributions if c.source_kind == "continuity_canon")
        self.assertIn("lighthouse", canon.content.lower())
        _ = restarted_kernel

    def test_real_card_context_planes_coexist(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        manifest = self._prepare_character(info.hg_session_id, character_id="Kizzie")
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("scene_state", kinds)
        self.assertIn("authored_character_knowledge", kinds)
        self.assertIn("scene_reference", kinds)

    def test_projector_reads_live_state_not_persisted_copy(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.location = "Alpha Dock"
        projections = project_authoritative_context(
            fixture,
            role="character",
            character_id="Alice",
            hg_scene_id=session_id,
            hg_round_id="round-test",
        )
        scene = next(p for p in projections if p.source_kind == "scene_state")
        self.assertIn("alpha dock", scene.content.lower())
        self.assertEqual(scene.provenance["projection_kind"], "live_scene_state")


if __name__ == "__main__":
    unittest.main()
