"""Issue #164 runtime build/effective configuration provenance persistence."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class RuntimeProvenanceTests(unittest.TestCase):
    def test_update_runtime_provenance_persists_host_metadata(self) -> None:
        repo = SessionRepository(tempfile.mkdtemp(prefix="hg-prov-"))
        kernel = DomainKernel.for_repository(repo)
        session = repo.create_session(cast=["Alice"], hg_session_id="session-prov-1")
        build = {
            "schema": "hg_runtime_build_provenance_v1",
            "repository_slug": "KizzieFae/Holy-Grail-RP-DeepSeek-Harness",
            "repository_commit_sha": "abc123",
            "commit_sha_source": "env",
        }
        effective = {
            "schema": "hg_runtime_effective_configuration_v1",
            "epochs": [
                {
                    "epoch_id": "epoch-1",
                    "effective_from": "session_open",
                    "effective_configuration_fingerprint": "fingerprint-1",
                    "capture_status": "complete",
                    "unavailable_fields": [],
                    "resolved": {"inference_mode": "mock"},
                }
            ],
            "current_epoch_id": "epoch-1",
        }
        result = kernel.update_runtime_provenance(
            session.hg_session_id,
            runtime_build_provenance=build,
            runtime_effective_configuration=effective,
        )
        self.assertTrue(result["persisted"])
        reloaded = repo.open_session(session.hg_session_id)
        self.assertEqual(reloaded.runtime_build_provenance, build)
        self.assertEqual(reloaded.runtime_effective_configuration, effective)


if __name__ == "__main__":
    unittest.main()
