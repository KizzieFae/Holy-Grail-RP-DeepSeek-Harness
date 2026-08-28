"""M11.2 learned world knowledge + user profile scope tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
for path in (_V2,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    RoundStartRequest,
    UserProfileSetRequest,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.knowledge_write_policy import upsert_canon_anchor_for_test  # noqa: E402
from domain_api.memory_scope import new_memory_scope_id  # noqa: E402
from domain_api.scope_knowledge_repository import LEARNED_WORLD_KNOWLEDGE  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.knowledge_test_helpers import retrieve_scope_world_text  # noqa: E402  # noqa: E402


class ScopeKnowledgeM112Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_session(self, *, memory_scope_id: str | None = None) -> str:
        info = self.kernel.create_session(
            cast=["Alice", "Bob"],
            memory_scope_id=memory_scope_id,
        )
        return info.hg_session_id

    def _start_round(self, session_id: str) -> str:
        return self.kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id

    def _commit_alice(self, session_id: str, *, round_id: str, turn_index: int = 0) -> str:
        response = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-alice",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=turn_index,
            )
        )
        self.assertTrue(response.committed, response.reason)
        assert response.domain_commit_id is not None
        return response.domain_commit_id

    def _prepare_manifest(self, session_id: str, *, character_id: str = "Alice"):
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

    def _learned_world_text(self, session_id: str, *, character_id: str = "Alice") -> str:
        fixture = self.repo.require(session_id)
        return retrieve_scope_world_text(
            self.repo.knowledge_service, fixture, character_id=character_id
        )

    def test_world_fact_promoted_from_canon_anchor_on_commit(self) -> None:
        session_id = self._create_session()
        round_id = self._start_round(session_id)
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_bridge",
            statement="The bridge collapsed.",
        )
        scope_id = fixture.memory_scope_id
        self._commit_alice(session_id, round_id=round_id)

        records = self.repo.scope_knowledge_repo.list_records(
            scope_id,
            knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
        )
        self.assertEqual(len(records), 1)
        self.assertIn("bridge collapsed", records[0].content.lower())
        self.assertIn("bridge collapsed", self._learned_world_text(session_id).lower())

    def test_promotion_is_idempotent(self) -> None:
        session_id = self._create_session()
        round_id = self._start_round(session_id)
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_gate",
            statement="The gate is sealed.",
        )
        scope_id = fixture.memory_scope_id
        self._commit_alice(session_id, round_id=round_id, turn_index=0)
        round_id_2 = self._start_round(session_id)
        self._commit_alice(session_id, round_id=round_id_2, turn_index=1)

        records = self.repo.scope_knowledge_repo.list_records(
            scope_id,
            knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
        )
        self.assertEqual(len(records), 1)

    def test_stale_learned_fact_suppressed_when_anchor_changes(self) -> None:
        session_id = self._create_session()
        round_id = self._start_round(session_id)
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_weather",
            statement="It is raining.",
        )
        self._commit_alice(session_id, round_id=round_id)
        self.assertIn("raining", self._learned_world_text(session_id).lower())

        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_weather",
            statement="The storm has passed.",
        )
        self.repo.persist(fixture)
        round_id_2 = self._start_round(session_id)
        self._commit_alice(session_id, round_id=round_id_2, turn_index=1)
        text = self._learned_world_text(session_id).lower()
        self.assertNotIn("raining", text)
        self.assertIn("storm has passed", text)

    def test_scope_isolation_between_memory_scopes(self) -> None:
        scope_a = new_memory_scope_id()
        scope_b = new_memory_scope_id()
        session_a = self._create_session(memory_scope_id=scope_a)
        session_b = self._create_session(memory_scope_id=scope_b)

        fixture_a = self.repo.require(session_a)
        upsert_canon_anchor_for_test(
            fixture_a.manager,
            anchor_id="anchor_scope_a",
            statement="Scope A secret landmark.",
        )
        round_id = self._start_round(session_a)
        self._commit_alice(session_a, round_id=round_id)

        self.assertIn("scope a secret", self._learned_world_text(session_a).lower())
        self.assertNotIn(
            "scope a secret",
            self._learned_world_text(session_b).lower(),
        )

    def test_learned_knowledge_survives_repository_restart(self) -> None:
        scope_id = new_memory_scope_id()
        session_a = self._create_session(memory_scope_id=scope_id)
        fixture = self.repo.require(session_a)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_restart",
            statement="The lighthouse still stands.",
        )
        round_id = self._start_round(session_a)
        self._commit_alice(session_a, round_id=round_id)

        session_b = self.kernel.create_session(
            cast=["Alice", "Bob"],
            memory_scope_id=scope_id,
        ).hg_session_id

        self.repo.clear_cache()
        restarted_repo = SessionRepository(self._tmpdir)
        restarted_kernel = DomainKernel.for_repository(restarted_repo)
        text = self._learned_world_text(session_b, character_id="Alice")
        self.assertIn("lighthouse", text.lower())
        _ = restarted_kernel

    def test_character_scoped_world_fact_visibility(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_alice_trait",
            subject="Alice",
            statement="Alice keeps a hidden journal.",
        )
        round_id = self._start_round(session_id)
        self._commit_alice(session_id, round_id=round_id)

        alice_text = self._learned_world_text(session_id, character_id="Alice").lower()
        bob_text = self._learned_world_text(session_id, character_id="Bob").lower()
        self.assertIn("hidden journal", alice_text)
        self.assertNotIn("hidden journal", bob_text)

    def test_explicit_user_profile_write_and_retrieval(self) -> None:
        session_id = self._create_session()
        before = dict(self.repo.require(session_id).character_states)
        result = self.kernel.set_user_profile_fact(
            UserProfileSetRequest(
                hg_session_id=session_id,
                profile_key="preferred_name",
                content="Alex",
                user_persona_id="Traveler",
            )
        )
        self.assertTrue(result["knowledge_id"])
        after = self.repo.require(session_id).character_states
        self.assertEqual(before, after)

        fixture = self.repo.require(session_id)
        _world, profiles = self.repo.knowledge_service.retrieve_scope_knowledge(
            fixture, character_id="Alice"
        )
        self.assertTrue(profiles)
        profile_text = "\n".join(record.content for record in profiles)
        self.assertIn("alex", profile_text.lower())
        self.assertEqual(profiles[0].profile_key, "preferred_name")

    def test_user_profile_upsert_replaces_prior_value(self) -> None:
        session_id = self._create_session()
        self.kernel.set_user_profile_fact(
            UserProfileSetRequest(
                hg_session_id=session_id,
                profile_key="preferred_name",
                content="Alex",
            )
        )
        self.kernel.set_user_profile_fact(
            UserProfileSetRequest(
                hg_session_id=session_id,
                profile_key="preferred_name",
                content="Alexander",
            )
        )
        fixture = self.repo.require(session_id)
        _world, profiles = self.repo.knowledge_service.retrieve_scope_knowledge(
            fixture, character_id="Alice"
        )
        profile_text = "\n".join(record.content for record in profiles)
        self.assertIn("alexander", profile_text.lower())
        self.assertNotIn("alex\n", profile_text.lower())

    def test_scene_state_precedes_learned_world_authority(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        upsert_canon_anchor_for_test(
            fixture.manager,
            anchor_id="anchor_location",
            statement="The workshop is abandoned.",
        )
        round_id = self._start_round(session_id)
        self._commit_alice(session_id, round_id=round_id)

        manifest = self._prepare_manifest(session_id)
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        world_records, _profiles = self.repo.knowledge_service.retrieve_scope_knowledge(
            self.repo.require(session_id), character_id="Alice"
        )
        self.assertTrue(world_records)
        learned = world_records[0]
        self.assertEqual(scene.authority_class, "authoritative")
        self.assertEqual(learned.authority_class, "suggestive")
        self.assertLess(scene.priority, 20)

    def test_unsupported_profile_key_rejected(self) -> None:
        session_id = self._create_session()
        with self.assertRaises(ValueError):
            self.kernel.set_user_profile_fact(
                UserProfileSetRequest(
                    hg_session_id=session_id,
                    profile_key="favorite_color",
                    content="blue",
                )
            )


if __name__ == "__main__":
    unittest.main()
