"""Cross-boundary failure attribution tests for Domain API HTTP transport (#76)."""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import DirectorContextPrepareRequest  # noqa: E402
from domain_api.http_transport import (  # noqa: E402
    HOST_INTERNAL_ERROR_KIND,
    HOST_INTERNAL_ERROR_MESSAGE,
    DomainApiHandler,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import PersistenceError, SessionRepository  # noqa: E402


def _start_server(kernel: DomainKernel) -> tuple[ThreadingHTTPServer, int]:
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _post(port: int, path: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _get(port: int, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


@pytest.fixture
def kernel(tmp_path: Path) -> DomainKernel:
    return DomainKernel.for_repository(SessionRepository(tmp_path))


def test_post_unexpected_exception_returns_host_internal_error(kernel: DomainKernel) -> None:
    secret = "TEST_UNIQ_INTERNAL_HOST_MARKER_SECRET"
    original = kernel.prepare_director_context

    def boom(req: DirectorContextPrepareRequest):
        raise RuntimeError(secret)

    kernel.prepare_director_context = boom  # type: ignore[method-assign]
    server, port = _start_server(kernel)
    try:
        status, body = _post(
            port,
            "/v1/director/context/prepare",
            {
                "hg_scene_id": "scene-1",
                "hg_round_id": "round-1",
                "inference_id": "inf-1",
                "turn_index": 0,
                "attempt_index": 0,
            },
        )
        payload = json.loads(body)
        assert status == 500
        assert payload["error_kind"] == HOST_INTERNAL_ERROR_KIND
        assert payload["error"] == HOST_INTERNAL_ERROR_MESSAGE
        assert secret not in body
        assert "RuntimeError" not in body
        assert "Traceback" not in body
        assert "http_transport" not in body.lower()

        health_status, health_body = _get(port, "/health")
        assert health_status == 200
        assert json.loads(health_body)["status"] == "ok"
    finally:
        kernel.prepare_director_context = original  # type: ignore[method-assign]
        server.shutdown()
        server.server_close()


def test_get_unexpected_exception_returns_host_internal_error(kernel: DomainKernel) -> None:
    secret = "GET_UNIQ_INTERNAL_HOST_MARKER_SECRET"

    def boom():
        raise RuntimeError(secret)

    kernel.list_characters = boom  # type: ignore[method-assign]
    server, port = _start_server(kernel)
    try:
        status, body = _get(port, "/v1/catalog/characters")
        payload = json.loads(body)
        assert status == 500
        assert payload["error_kind"] == HOST_INTERNAL_ERROR_KIND
        assert secret not in body
        assert "RuntimeError" not in body
    finally:
        server.shutdown()
        server.server_close()


def test_post_invalid_request_still_returns_400(kernel: DomainKernel) -> None:
    server, port = _start_server(kernel)
    try:
        status, body = _post(port, "/v1/director/context/prepare", {})
        payload = json.loads(body)
        assert status == 400
        assert "error_kind" not in payload
    finally:
        server.shutdown()
        server.server_close()


def test_get_unknown_session_still_returns_404(kernel: DomainKernel) -> None:
    server, port = _start_server(kernel)
    try:
        status, body = _get(port, "/v1/sessions/missing-session/state")
        payload = json.loads(body)
        assert status == 404
        assert payload["error"] == "unknown session"
    finally:
        server.shutdown()
        server.server_close()


def test_post_persistence_error_still_returns_503(kernel: DomainKernel) -> None:
    def boom(req: DirectorContextPrepareRequest):
        raise PersistenceError("test persistence unavailable")

    kernel.prepare_director_context = boom  # type: ignore[method-assign]
    server, port = _start_server(kernel)
    try:
        status, body = _post(
            port,
            "/v1/director/context/prepare",
            {
                "hg_scene_id": "scene-1",
                "hg_round_id": "round-1",
                "inference_id": "inf-1",
                "turn_index": 0,
                "attempt_index": 0,
            },
        )
        payload = json.loads(body)
        assert status == 503
        assert payload["error_kind"] == "persistence_failure"
    finally:
        server.shutdown()
        server.server_close()
