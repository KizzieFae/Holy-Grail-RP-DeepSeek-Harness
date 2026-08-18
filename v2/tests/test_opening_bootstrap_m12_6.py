"""M12.6 opening/bootstrap parity tests."""

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

from v2.domain_api.contract import OpeningContextPrepareRequest, OpeningPersistRequest
from v2.domain_api.kernel import DomainKernel
from v2.domain_api.session_history import append_history_entry
from v2.domain_api.session_repository import SessionRepository
from v2.domain_api.setup_catalog import list_template_openers_catalog


class OpeningBootstrapM126Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_minimal_opening_does_not_append_history(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "minimal"},
        )
        session = self.repo.require(info.hg_session_id)
        self.assertEqual(session.rp_history, [])
        assert session.manager.scene_state is not None
        self.assertIn("apartment", session.manager.scene_state.opening_description.lower())

    def test_template_opening_persists_authored_prose(self) -> None:
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
        session = self.repo.require(info.hg_session_id)
        self.assertEqual(len(session.rp_history), 1)
        opening = session.rp_history[0]
        self.assertEqual(opening["kind"], "opening")
        self.assertEqual(opening["entry_id"], f"opening-{info.hg_session_id}")
        self.assertIn("Walking out of one of her boss's hotels", opening["content"])
        self.assertEqual(opening["metadata"]["mode"], "template")

    def test_template_opening_unknown_opener_fails(self) -> None:
        with self.assertRaises(ValueError):
            self.kernel.create_session(
                characters=["kizzie", "willow"],
                scene_template_id="celina_apartment_recovery_watch",
                role_assignments={
                    "kizzie": "recovering_demi_human",
                    "willow": "protector",
                },
                opening={"mode": "template", "opener_id": "missing-opener"},
            )

    def test_generated_opening_deferred_until_persist(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "generated"},
        )
        session = self.repo.require(info.hg_session_id)
        self.assertEqual(session.rp_history, [])
        self.assertEqual(session.setup_snapshot["opening"]["mode"], "generated")

        manifest = self.kernel.prepare_opening_context(
            OpeningContextPrepareRequest(
                hg_session_id=info.hg_session_id,
                inference_id="inf-opening-1",
            )
        )
        self.assertEqual(manifest.role, "opening")
        instruction = next(
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        )
        self.assertIn("Do not invent new canonical world facts", instruction.content)

        entry = self.kernel.persist_opening_presentation(
            OpeningPersistRequest(
                hg_session_id=info.hg_session_id,
                inference_id="inf-opening-1",
                presentation_text="Rain taps the window as the scene begins.",
                manifest_id=manifest.manifest_id,
            )
        )
        self.assertEqual(entry["kind"], "opening")
        self.assertEqual(entry["entry_id"], f"opening-{info.hg_session_id}")

        duplicate = self.kernel.persist_opening_presentation(
            OpeningPersistRequest(
                hg_session_id=info.hg_session_id,
                inference_id="inf-opening-1",
                presentation_text="Rain taps the window as the scene begins.",
            )
        )
        self.assertEqual(duplicate["entry_id"], entry["entry_id"])
        reopened = self.repo.open_session(info.hg_session_id)
        self.assertEqual(len(reopened.rp_history), 1)

    def test_restart_restores_opening_without_regeneration(self) -> None:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "custom", "text": "Custom durable opening."},
        )
        session_id = info.hg_session_id
        self.repo.clear_cache()
        reopened = self.repo.open_session(session_id)
        self.assertEqual(len(reopened.rp_history), 1)
        self.assertEqual(reopened.rp_history[0]["content"], "Custom durable opening.")

        with self.assertRaises(ValueError):
            self.kernel.prepare_opening_context(
                OpeningContextPrepareRequest(
                    hg_session_id=session_id,
                    inference_id="inf-opening-blocked",
                )
            )

    def test_history_entry_id_is_idempotent(self) -> None:
        history: list[dict] = []
        first = append_history_entry(
            history,
            kind="opening",
            content="Once.",
            entry_id="opening-test",
        )
        second = append_history_entry(
            history,
            kind="opening",
            content="Twice.",
            entry_id="opening-test",
        )
        self.assertEqual(first["entry_id"], second["entry_id"])
        self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
