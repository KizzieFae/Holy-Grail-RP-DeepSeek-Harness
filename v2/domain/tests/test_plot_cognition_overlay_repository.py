"""#59 Plot Cognition Overlay repository tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.plot_cognition_overlay_repository import (  # noqa: E402
    PersistenceError,
    PlotCognitionOverlayRepository,
    RevisionConflictError,
)
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    PLOT_COGNITION_OVERLAY_STORE_SCHEMA,
    empty_store,
)


class PlotCognitionOverlayRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = PlotCognitionOverlayRepository(self._tmpdir)
        self.scope = "hg-plot-cognition-scope-test"

    def test_absent_store(self) -> None:
        raw = self.repo.load_raw(self.scope)
        self.assertEqual(raw.status, "absent")
        self.assertIsNone(raw.payload)

    def test_valid_round_trip(self) -> None:
        store = empty_store(self.scope)
        revision = self.repo.save_raw(self.scope, store.to_dict(), expected_revision=0)
        self.assertEqual(revision, 1)
        raw = self.repo.load_raw(self.scope)
        self.assertEqual(raw.status, "present")
        assert raw.payload is not None
        self.assertEqual(raw.payload["store_revision"], 1)
        self.assertEqual(
            raw.payload["store_schema"],
            PLOT_COGNITION_OVERLAY_STORE_SCHEMA,
        )

    def test_revision_cas_conflict(self) -> None:
        store = empty_store(self.scope)
        self.repo.save_raw(self.scope, store.to_dict(), expected_revision=0)
        with self.assertRaises(RevisionConflictError):
            self.repo.save_raw(self.scope, store.to_dict(), expected_revision=0)

    def test_unsupported_version(self) -> None:
        path = self.repo.store_path(self.scope)
        path.write_text(
            json.dumps({"store_schema": "hg_plot_cognition_overlay_store_v0"}),
            encoding="utf-8",
        )
        raw = self.repo.load_raw(self.scope)
        self.assertEqual(raw.status, "unsupported_version")

    def test_corrupt_store_quarantined(self) -> None:
        path = self.repo.store_path(self.scope)
        path.write_text("{not-json", encoding="utf-8")
        raw = self.repo.load_raw(self.scope)
        self.assertEqual(raw.status, "corrupt")
        self.assertFalse(path.exists())
        self.assertTrue(raw.quarantine_path)
        self.assertTrue(Path(str(raw.quarantine_path)).exists())

    def test_corrupt_quarantine_remains_blocked_not_absent(self) -> None:
        path = self.repo.store_path(self.scope)
        path.write_text("{not-json", encoding="utf-8")
        first = self.repo.load_raw(self.scope)
        self.assertEqual(first.status, "corrupt")
        second = self.repo.load_raw(self.scope)
        self.assertEqual(second.status, "corrupt")
        self.assertNotEqual(second.status, "absent")
        with self.assertRaises(PersistenceError):
            self.repo.save_raw(self.scope, empty_store(self.scope).to_dict(), expected_revision=0)

    def test_unsupported_version_remains_blocked(self) -> None:
        path = self.repo.store_path(self.scope)
        path.write_text(
            json.dumps({"store_schema": "hg_plot_cognition_overlay_store_v0"}),
            encoding="utf-8",
        )
        first = self.repo.load_raw(self.scope)
        self.assertEqual(first.status, "unsupported_version")
        second = self.repo.load_raw(self.scope)
        self.assertEqual(second.status, "unsupported_version")
        with self.assertRaises(PersistenceError):
            self.repo.save_raw(self.scope, empty_store(self.scope).to_dict(), expected_revision=0)

    def test_atomic_save_replaces_content(self) -> None:
        store = empty_store(self.scope)
        store.assimilated_through_domain_commit_id = "hg-commit-a"
        self.repo.save_raw(self.scope, store.to_dict(), expected_revision=0)
        store.assimilated_through_domain_commit_id = "hg-commit-b"
        self.repo.save_raw(self.scope, store.to_dict(), expected_revision=1)
        raw = self.repo.load_raw(self.scope)
        assert raw.payload is not None
        self.assertEqual(raw.payload["assimilated_through_domain_commit_id"], "hg-commit-b")


if __name__ == "__main__":
    unittest.main()
