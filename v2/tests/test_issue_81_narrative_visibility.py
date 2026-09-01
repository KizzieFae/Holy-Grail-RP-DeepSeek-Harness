"""Issue #81 — NarrativeVisibilityRecord behavioral validation."""

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
    CommitRequest,
    ContextPrepareRequest,
    OpeningPerceptualVisibilityAttachRequest,
    PresentationRecordRequest,
    RoundStartRequest,
)
from domain_api.kernel import DomainKernel, PROTOTYPE_DIRECTOR_DECISION  # noqa: E402
from domain_api.session_history import (  # noqa: E402
    project_history_to_character_context_chat,
    project_history_to_transcript,
)
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.setup_catalog import list_template_openers_catalog  # noqa: E402


def _mixed_narrator_nvr(*, beat_index: int = 0) -> dict:
    return {
        "units": [
            {
                "unit_id": "scene",
                "kind": "observable_scene",
                "text": "Rain drummed against the tall windows and pooled on the marble floor.",
                "recipients": {"scope": "public"},
            },
            {
                "unit_id": "action",
                "kind": "observable_event",
                "text": "Alice crossed the room with deliberate steps.",
                "recipients": {"scope": "public"},
            },
            {
                "unit_id": "speech",
                "kind": "speech",
                "text": '"This stays between us, Bob."',
                "recipients": {"scope": "directed", "characters": ["Bob"]},
                "beat_index": beat_index,
            },
            {
                "unit_id": "internal",
                "kind": "internal",
                "text": "Alice felt a spike of guilt she refused to show.",
                "recipients": {"scope": "private", "characters": ["Alice"]},
            },
            {
                "unit_id": "style",
                "kind": "presentation_only",
                "text": "The moment hung like a held breath.",
                "recipients": {"scope": "public"},
            },
        ]
    }


def _ayame_opener_nvr(*, host_name: str, applicant_name: str) -> dict:
    return {
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
    }


def _celina_opener_nvr(*, celina_name: str, demi_name: str) -> dict:
    return {
        "units": [
            {
                "unit_id": "public_storm",
                "kind": "observable_scene",
                "text": "Wind-driven rain splashed against the street as Celina walked toward her car.",
                "recipients": {"scope": "public"},
            },
            {
                "unit_id": "celina_internal",
                "kind": "internal",
                "text": "For a moment, Celina considered walking on. Not her problem.",
                "recipients": {"scope": "private", "characters": [celina_name]},
            },
            {
                "unit_id": "rescue_observable",
                "kind": "observable_event",
                "text": (
                    f"Celina squatted, hauled the kitsune up, and adjusted her grip as the demi-human's body "
                    f"shook with cold."
                ),
                "recipients": {"scope": "present"},
            },
        ]
    }


def _yukiko_public_opener_nvr() -> dict:
    return {
        "units": [
            {
                "unit_id": "shrine_public",
                "kind": "observable_scene",
                "text": (
                    "Morning light filters through the vermillion torii as the shrine grounds come alive "
                    "with quiet ritual, footsteps, bells, and the rustle of trees."
                ),
                "recipients": {"scope": "public"},
            }
        ]
    }


class Issue81NarrativeVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _start_round(self, session_id: str) -> str:
        return self.kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id

    def _manifest_transcript(self, session_id: str, *, character_id: str) -> str:
        round_id = self._start_round(session_id)
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id=f"inf-{character_id}",
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        contribution = next(
            c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
        )
        return contribution.content

    def _create_ayame_session(self) -> tuple[str, str, str]:
        openers = list_template_openers_catalog("ayame_household_entry_evaluation")
        info = self.kernel.create_session(
            characters=["ayame", "kizzie"],
            scene_template_id="ayame_household_entry_evaluation",
            role_assignments={"ayame": "host", "kizzie": "applicant"},
            opening={"mode": "template", "opener_id": openers[0]["opener_id"]},
        )
        fixture = self.repo.require(info.hg_session_id)
        host_name = fixture.setup_snapshot["names_by_file"]["ayame"]
        applicant_name = fixture.setup_snapshot["names_by_file"]["kizzie"]
        self.kernel.attach_opening_perceptual_visibility(
            OpeningPerceptualVisibilityAttachRequest(
                hg_session_id=info.hg_session_id,
                perceptual_visibility=_ayame_opener_nvr(
                    host_name=host_name,
                    applicant_name=applicant_name,
                ),
            )
        )
        return info.hg_session_id, host_name, applicant_name

    def test_mixed_narrator_viewer_specific_rich_subset(self) -> None:
        session_id = self.kernel.create_session(cast=["Alice", "Bob", "Carol"]).hg_session_id
        round_id = self._start_round(session_id)
        move = {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "speech",
                    "dialogue": "This stays between us, Bob.",
                    "audibility": "directed",
                    "audience": ["Bob"],
                }
            ],
        }
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-81-mixed",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move=move,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        presentation = (
            "Rain drummed against the tall windows and pooled on the marble floor. "
            'Alice crossed the room with deliberate steps. "This stays between us, Bob." '
            "Alice felt a spike of guilt she refused to show."
        )
        self.kernel.record_presentation(
            PresentationRecordRequest(
                hg_session_id=session_id,
                domain_commit_id=commit.domain_commit_id,
                hg_round_id=round_id,
                character_id="Alice",
                presentation_text=presentation,
                perceptual_visibility=_mixed_narrator_nvr(),
            )
        )
        fixture = self.repo.require(session_id)
        bob_chat = project_history_to_character_context_chat(
            fixture.rp_history,
            character_id="Bob",
            character_names=["Alice", "Bob", "Carol"],
            present_characters=["Alice", "Bob", "Carol"],
            get_character_display_name_fn=lambda name: name,
        )
        bob_text = " ".join(m["content"] for m in bob_chat)
        self.assertIn("Rain drummed", bob_text)
        self.assertIn("This stays between us, Bob", bob_text)
        self.assertNotIn("guilt", bob_text)

        carol_chat = project_history_to_character_context_chat(
            fixture.rp_history,
            character_id="Carol",
            character_names=["Alice", "Bob", "Carol"],
            present_characters=["Alice", "Bob", "Carol"],
            get_character_display_name_fn=lambda name: name,
        )
        carol_text = " ".join(m["content"] for m in carol_chat)
        self.assertIn("Rain drummed", carol_text)
        self.assertNotIn("This stays between us", carol_text)

    def test_ayame_opener_leak_prevented(self) -> None:
        session_id, host_name, applicant_name = self._create_ayame_session()
        host_transcript = self._manifest_transcript(session_id, character_id=host_name)
        applicant_transcript = self._manifest_transcript(session_id, character_id=applicant_name)
        self.assertNotIn("horrible week", host_transcript)
        self.assertIn("horrible week", applicant_transcript)
        self.assertIn("mansion", host_transcript)

    def test_celina_internal_does_not_leak_to_demi(self) -> None:
        info = self.kernel.create_session(
            characters=["celina", "kizzie"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={"celina": "protector", "kizzie": "recovering_demi_human"},
            opening={"mode": "template", "opener_id": "default"},
        )
        fixture = self.repo.require(info.hg_session_id)
        celina = fixture.setup_snapshot["names_by_file"]["celina"]
        demi = fixture.setup_snapshot["names_by_file"]["kizzie"]
        self.kernel.attach_opening_perceptual_visibility(
            OpeningPerceptualVisibilityAttachRequest(
                hg_session_id=info.hg_session_id,
                perceptual_visibility=_celina_opener_nvr(celina_name=celina, demi_name=demi),
            )
        )
        demi_transcript = self._manifest_transcript(info.hg_session_id, character_id=demi)
        self.assertNotIn("Not her problem", demi_transcript)
        celina_transcript = self._manifest_transcript(info.hg_session_id, character_id=celina)
        self.assertIn("Not her problem", celina_transcript)

    def test_public_opener_reaches_present_characters(self) -> None:
        info = self.kernel.create_session(
            characters=["yukiko", "kizzie"],
            scene_template_id="yukiko_shrine_guided_visit",
            role_assignments={"yukiko": "head_miko", "kizzie": "primary_visitor"},
            opening={"mode": "template", "opener_id": "default"},
        )
        fixture = self.repo.require(info.hg_session_id)
        yukiko = fixture.setup_snapshot["names_by_file"]["yukiko"]
        traveler = fixture.setup_snapshot["names_by_file"]["kizzie"]
        self.kernel.attach_opening_perceptual_visibility(
            OpeningPerceptualVisibilityAttachRequest(
                hg_session_id=info.hg_session_id,
                perceptual_visibility=_yukiko_public_opener_nvr(),
            )
        )
        for character_id in (yukiko, traveler):
            transcript = self._manifest_transcript(info.hg_session_id, character_id=character_id)
            self.assertIn("vermillion torii", transcript)

    def test_missing_nvr_excludes_opener_from_character_cognition(self) -> None:
        openers = list_template_openers_catalog("ayame_household_entry_evaluation")
        info = self.kernel.create_session(
            characters=["ayame", "kizzie"],
            scene_template_id="ayame_household_entry_evaluation",
            role_assignments={"ayame": "host", "kizzie": "applicant"},
            opening={"mode": "template", "opener_id": openers[0]["opener_id"]},
        )
        fixture = self.repo.require(info.hg_session_id)
        host_name = fixture.setup_snapshot["names_by_file"]["ayame"]
        round_id = self._start_round(info.hg_session_id)
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=info.hg_session_id,
                hg_round_id=round_id,
                inference_id="inf-missing-nvr",
                character_id=host_name,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        transcript_kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("recent_scene_transcript", transcript_kinds)

    def test_human_transcript_unchanged(self) -> None:
        session_id, _, _ = self._create_ayame_session()
        fixture = self.repo.require(session_id)
        transcript = project_history_to_transcript(fixture.rp_history)
        opening = next(item for item in transcript if item.get("opening"))
        self.assertIn("horrible week", opening["content"])

    def test_persistence_hydration_identical_projection(self) -> None:
        session_id, host_name, _ = self._create_ayame_session()
        before = self._manifest_transcript(session_id, character_id=host_name)
        reloaded = self.repo.require(session_id)
        after = self._manifest_transcript(reloaded.hg_session_id, character_id=host_name)
        self.assertEqual(before, after)

    def test_audit_provenance_reconstructable(self) -> None:
        session_id, host_name, _ = self._create_ayame_session()
        fixture = self.repo.require(session_id)
        chat = project_history_to_character_context_chat(
            fixture.rp_history,
            character_id=host_name,
            character_names=list(fixture.cast),
            present_characters=list(fixture.cast),
            get_character_display_name_fn=lambda name: name,
        )
        projection = chat[0].get("perceptual_visibility_projection")
        self.assertIsInstance(projection, dict)
        self.assertIn("included_unit_ids", projection)
        self.assertIn("excluded_unit_ids", projection)

    def test_recent_history_retains_environmental_prose(self) -> None:
        session_id = self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id
        round_id = self._start_round(session_id)
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-81-rich",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                validated_move={
                    "move_schema_version": 2,
                    "beats": [{"type": "action", "action": "looked around"}],
                },
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        self.kernel.record_presentation(
            PresentationRecordRequest(
                hg_session_id=session_id,
                domain_commit_id=commit.domain_commit_id,
                hg_round_id=round_id,
                character_id="Alice",
                presentation_text="Brown walls and plush carpet lined the hall.",
                perceptual_visibility={
                    "units": [
                        {
                            "unit_id": "scene",
                            "kind": "observable_scene",
                            "text": "Brown walls and plush carpet lined the hall.",
                            "recipients": {"scope": "public"},
                        }
                    ]
                },
            )
        )
        transcript = self._manifest_transcript(session_id, character_id="Bob")
        self.assertIn("plush carpet", transcript)
        payload = json.loads(transcript.split(":", 1)[1].strip())
        self.assertTrue(any("plush carpet" in item.get("content", "") for item in payload))


if __name__ == "__main__":
    unittest.main()
