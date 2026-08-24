"""Issue #21 — bounded scene progression projection for Director/Narrator."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.modules.continuity_state_public_event import PublicEvent  # noqa: E402
from domain.modules.continuity_state_scene import ScenePhase  # noqa: E402
from domain.modules.prompt_builders import build_narrator_render_prompt  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
)
from domain_api.continuity_context_projector import (  # noqa: E402
    project_authoritative_context,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_repository import SessionRepository  # noqa: E402


ENTRANCE_OPENING = (
    "You stood at the mansion entrance and lifted your hand toward the door."
)


class Issue21SceneProgressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_session(self) -> str:
        session_id = self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id
        fixture = self.repo.require(session_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.opening_description = ENTRANCE_OPENING
        fixture.manager.scene_state.recent_delta = "Alice stepped into the foyer."
        fixture.manager.scene_state.phase = ScenePhase.RISING
        fixture.manager.scene_state.current_tension_level = "moderate"
        return session_id

    def _start_round(self, session_id: str) -> str:
        return self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id

    def _commit_alice(self, session_id: str, round_id: str, *, turn_index: int) -> None:
        self.kernel.commit_move(
            CommitRequest(
                inference_id=f"inf-commit-{turn_index}",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=turn_index,
            )
        )

    def _director_manifest(self, session_id: str):
        round_id = self._start_round(session_id)
        return self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-director-21",
                turn_index=0,
                attempt_index=0,
            )
        )

    def test_director_receives_scene_setup_progression_and_live_scene_state(self) -> None:
        session_id = self._create_session()
        manifest = self._director_manifest(session_id)
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertEqual(
            kinds,
            {
                "scene_setup",
                "scene_state",
                "scene_progression",
                "actor_suitability",
                "director_scratch",
                "inference_instruction",
            },
        )
        setup = next(c for c in manifest.contributions if c.source_kind == "scene_setup")
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        progression = next(
            c for c in manifest.contributions if c.source_kind == "scene_progression"
        )
        self.assertIn("historical background", setup.content.lower())
        self.assertIn(ENTRANCE_OPENING, setup.content)
        self.assertNotIn("scene premise", scene.content.lower())
        self.assertNotIn(ENTRANCE_OPENING, scene.content)
        self.assertIn("scene progression", progression.content.lower())
        self.assertNotIn("recent delta", progression.content.lower())
        self.assertIn("scene phase: rising", progression.content.lower())
        self.assertIn("current tension level: moderate", progression.content.lower())

    def test_character_manifest_excludes_scene_setup_and_progression(self) -> None:
        session_id = self._create_session()
        round_id = self._start_round(session_id)
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-alice",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("scene_setup", kinds)
        self.assertNotIn("scene_progression", kinds)
        scene = next(c for c in manifest.contributions if c.source_kind == "scene_state")
        self.assertNotIn(ENTRANCE_OPENING, scene.content)

    def test_scene_progression_uses_recent_event_window_bound(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        fixture.manager.recent_event_window = 8
        projections = project_authoritative_context(
            fixture,
            role="director",
            hg_scene_id=session_id,
            hg_round_id="round-test",
        )
        progression = next(
            p for p in projections if p.source_kind == "scene_progression"
        )
        self.assertEqual(progression.provenance["recent_event_window"], 8)

    def test_multi_round_commits_project_public_event_summaries(self) -> None:
        session_id = self._create_session()
        fixture = self.repo.require(session_id)
        now = datetime.now(timezone.utc)
        fixture.manager.public_events.extend(
            [
                PublicEvent(
                    event_id="evt_turn_0",
                    timestamp=now,
                    event_type="action",
                    participants=["Alice"],
                    summary="Alice opened the door and stepped into the foyer.",
                    turn_index=0,
                ),
                PublicEvent(
                    event_id="evt_turn_1",
                    timestamp=now,
                    event_type="action",
                    participants=["Alice"],
                    summary="Alice closed the door and moved toward the sitting room.",
                    turn_index=1,
                ),
            ]
        )
        projections = project_authoritative_context(
            fixture,
            role="narrator",
            hg_scene_id=session_id,
            hg_round_id="round-test",
            continuity_turn_index=2,
        )
        progression = next(
            p for p in projections if p.source_kind == "scene_progression"
        )
        self.assertEqual(progression.provenance["public_event_count"], 2)
        self.assertIn("[turn 0]", progression.content)
        self.assertIn("foyer", progression.content.lower())
        self.assertIn("[turn 1]", progression.content)
        self.assertIn("sitting room", progression.content.lower())
        self.assertNotIn("scene premise", progression.content.lower())

    def test_narrator_manifest_includes_scene_progression_after_commit(self) -> None:
        session_id = self._create_session()
        round_id = self._start_round(session_id)
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-commit-narrator",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-narrator-21",
                character_id="Alice",
                domain_commit_id=commit.domain_commit_id,
                continuity_turn_index=commit.continuity_turn_index,
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("scene_setup", kinds)
        self.assertIn("scene_progression", kinds)
        self.assertIn("committed_move", kinds)
        self.assertIn("director_decision", kinds)

    def test_scenario_grade_multi_round_manifests_preserve_setup_progression_split(self) -> None:
        session_id = self._create_session()
        for turn_index in range(3):
            round_id = self._start_round(session_id)
            self._commit_alice(session_id, round_id, turn_index=turn_index)
            next_round_id = self._start_round(session_id)
            manifest = self.kernel.prepare_director_context(
                DirectorContextPrepareRequest(
                    hg_scene_id=session_id,
                    hg_round_id=next_round_id,
                    inference_id=f"inf-director-round-{turn_index}",
                    turn_index=0,
                    attempt_index=0,
                )
            )
            setup = next(
                c for c in manifest.contributions if c.source_kind == "scene_setup"
            )
            scene = next(
                c for c in manifest.contributions if c.source_kind == "scene_state"
            )
            progression = next(
                c for c in manifest.contributions if c.source_kind == "scene_progression"
            )
            self.assertIn(ENTRANCE_OPENING, setup.content)
            self.assertNotIn(ENTRANCE_OPENING, scene.content)
            self.assertNotIn(ENTRANCE_OPENING, progression.content)
            self.assertNotIn("recent delta", progression.content.lower())

    def test_narrator_prompt_documents_environment_hierarchy(self) -> None:
        prompt = build_narrator_render_prompt(
            char_name="Alice",
            action="She leaned forward to begin the interview.",
            dialogue="",
            environment_event="The front door creaks open.",
            scene_context="Scene progression shows Alice seated in the sitting room.",
        )
        lowered = prompt.lower()
        self.assertIn("authoritative scene progression", lowered)
        self.assertIn("omit environment material when it conflicts", lowered)


if __name__ == "__main__":
    unittest.main()
