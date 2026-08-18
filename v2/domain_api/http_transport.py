"""Prototype HTTP transport for the Domain API (replaceable; not architectural)."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .contract import (
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionValidationRequest,
    EligibleActorsRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
    ValidationRequest,
)
from .kernel import DomainKernel


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj


class DomainApiHandler(BaseHTTPRequestHandler):
    kernel: DomainKernel

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(_to_jsonable(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/v1/rounds/start":
                req = RoundStartRequest(hg_scene_id=str(data["hg_scene_id"]))
                self._send_json(200, self.kernel.start_round(req))
                return
            if path == "/v1/rounds/eligible-actors":
                req = EligibleActorsRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                )
                self._send_json(200, self.kernel.eligible_actors(req))
                return
            if path == "/v1/director/context/prepare":
                req = DirectorContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    actors_used_this_round=tuple(data.get("actors_used_this_round") or ()),
                )
                self._send_json(200, self.kernel.prepare_director_context(req))
                return
            if path == "/v1/director/decisions/validate":
                req = DirectorDecisionValidationRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    proposed_decision=dict(data.get("proposed_decision") or {}),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.validate_director_decision(req))
                return
            if path == "/v1/context/prepare":
                req = ContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    role=str(data.get("role", "guest")),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                )
                self._send_json(200, self.kernel.prepare_context(req))
                return
            if path == "/v1/moves/validate":
                req = ValidationRequest(
                    inference_id=str(data["inference_id"]),
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    character_id=str(data["character_id"]),
                    role=str(data.get("role", "guest")),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    proposed_move=dict(data.get("proposed_move") or {}),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.validate_move(req))
                return
            if path == "/v1/moves/commit":
                req = CommitRequest(
                    inference_id=str(data["inference_id"]),
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    character_id=str(data["character_id"]),
                    validated_move=dict(data["validated_move"]),
                    director_decision=dict(data["director_decision"]),
                    expected_turn_index=int(data["expected_turn_index"]),
                )
                self._send_json(200, self.kernel.commit_move(req))
                return
            if path == "/v1/narrator/context/prepare":
                req = NarratorContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                )
                self._send_json(200, self.kernel.prepare_narrator_context(req))
                return
            if path == "/v1/scenes":
                fixture = self.kernel.create_scene(
                    hg_scene_id=data.get("hg_scene_id"),
                    location=data.get("location", "Workshop"),
                    cast=data.get("cast"),
                )
                self._send_json(201, self.kernel.scene_snapshot(fixture.hg_scene_id))
                return
            self._send_json(404, {"error": "not found"})
        except (KeyError, TypeError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/v1/scenes/") and path.endswith("/state"):
            hg_scene_id = path.removeprefix("/v1/scenes/").removesuffix("/state")
            try:
                self._send_json(200, self.kernel.scene_snapshot(hg_scene_id))
            except KeyError:
                self._send_json(404, {"error": "unknown scene"})
            return
        self._send_json(404, {"error": "not found"})


def serve(kernel: DomainKernel, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    handler = type(
        "BoundDomainApiHandler",
        (DomainApiHandler,),
        {"kernel": kernel},
    )
    server = ThreadingHTTPServer((host, port), handler)
    return server
