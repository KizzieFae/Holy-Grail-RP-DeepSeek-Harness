"""Unit tests for Streamlit turn recovery helpers (#86)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

UI_PATH = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"


def load_streamlit_module():
    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = {}
    sys.modules["streamlit"] = fake_st
    spec = importlib.util.spec_from_file_location("streamlit_app_test", UI_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["streamlit_app_test"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeSessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class StreamlitTurnRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = load_streamlit_module()

    def test_recovery_poll_detects_terminal_success(self):
        fake_state = FakeSessionState(
            pending_operation_id="op-1",
            hg_session_id="hg-session-test",
            transcript=[],
            runtime_status="ready",
        )
        status_payload = {
            "health": {
                "application_status": "ready",
                "last_round_terminal": {
                    "operation_id": "op-1",
                    "outcome": "succeeded",
                },
            },
            "transcript": [{"role": "assistant", "content": "done"}],
        }
        with patch.object(self.ui, "st") as mock_st:
            mock_st.session_state = fake_state
            with patch.object(self.ui, "api_request", return_value=status_payload):
                self.assertEqual(self.ui.recovery_poll_once(), "success")
                self.assertEqual(fake_state.transcript[0]["content"], "done")

    def test_recovery_poll_does_not_use_stale_terminal(self):
        fake_state = FakeSessionState(
            pending_operation_id="op-new",
            hg_session_id="hg-session-test",
            transcript=[],
            runtime_status="ready",
        )
        status_payload = {
            "health": {
                "application_status": "ready",
                "last_round_terminal": {
                    "operation_id": "op-old",
                    "outcome": "succeeded",
                },
            },
            "transcript": [],
        }
        with patch.object(self.ui, "st") as mock_st:
            mock_st.session_state = fake_state
            with patch.object(self.ui, "api_request", return_value=status_payload):
                self.assertEqual(self.ui.recovery_poll_once(), "processing")

    def test_wait_expiry_is_not_authoritative_failure(self):
        err = self.ui.ApiResponseWaitExpired("timed out")
        self.assertNotIn("Turn failed", str(err))

    def test_session_create_uses_extended_wait_budget(self):
        with patch.object(self.ui.urllib.request, "urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = b'{"session": {"hg_session_id": "hg-session-test"}}'
            self.ui.api_request(
                "POST",
                "/api/sessions/create",
                {"cast": ["Alice"]},
                timeout=self.ui.SESSION_CREATE_WAIT_SEC,
            )
            request = mock_urlopen.call_args[0][0]
            self.assertEqual(request.full_url, f"{self.ui.API_BASE}/api/sessions/create")
            self.assertEqual(mock_urlopen.call_args[1]["timeout"], 180)

    def test_bare_timeout_error_maps_to_connectivity_error_for_session_create(self):
        with patch.object(self.ui.urllib.request, "urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(self.ui.ApiConnectivityError):
                self.ui.api_request("POST", "/api/sessions/create", {"cast": ["Alice"]}, timeout=30)


if __name__ == "__main__":
    unittest.main()
