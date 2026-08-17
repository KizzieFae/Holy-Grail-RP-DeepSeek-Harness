"""State authority and traceability tests for the V2 Domain API."""

from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    ValidationRequest,
)
from domain_api.http_transport import DomainApiHandler  # noqa: E402
from domain_api.kernel import PROTOTYPE_VALID_MOVE, DomainKernel  # noqa: E402


def _invalid_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [],
        "motivation": {
            "goal": "x",
            "tactic": "x",
            "emotional_driver": "x",
            "risk_level": "x",
        },
    }


@pytest.fixture
def kernel() -> DomainKernel:
    k = DomainKernel()
    k.create_scene()
    return k


def test_prepare_context_preserves_provenance(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=fixture.hg_scene_id,
            inference_id="inf-1",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
        )
    )
    assert manifest.manifest_id
    assert manifest.inference_id == "inf-1"
    assert len(manifest.contributions) >= 2
    scene_contrib = manifest.contributions[0]
    assert scene_contrib.source_kind == "scene_state"
    assert scene_contrib.provenance["hg_scene_id"] == fixture.hg_scene_id


def test_validation_rejects_invalid_before_commit(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    before = kernel.scene_snapshot(fixture.hg_scene_id).turn_counter
    result = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-2",
            hg_scene_id=fixture.hg_scene_id,
            character_id="Alice",
            role="guest",
            turn_index=before,
            attempt_index=0,
            proposed_move=_invalid_move(),
            raw_model_output=json.dumps(_invalid_move()),
        )
    )
    assert result.accepted is False
    assert result.retryable is True
    after = kernel.scene_snapshot(fixture.hg_scene_id).turn_counter
    assert after == before


def test_proposal_without_commit_does_not_mutate_continuity(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    before = kernel.scene_snapshot(fixture.hg_scene_id)
    kernel.record_uncommitted_proposal(fixture.hg_scene_id)
    kernel.validate_move(
        ValidationRequest(
            inference_id="inf-3",
            hg_scene_id=fixture.hg_scene_id,
            character_id="Alice",
            role="guest",
            turn_index=before.turn_counter,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    after = kernel.scene_snapshot(fixture.hg_scene_id)
    assert after.turn_counter == before.turn_counter
    assert after.committed_move_count == before.committed_move_count


def test_commit_uses_authoritative_continuity_path(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-4",
            hg_scene_id=fixture.hg_scene_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    assert validation.accepted is True
    assert validation.normalized_move is not None

    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-4",
            hg_scene_id=fixture.hg_scene_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.continuity_turn_index == 1
    assert commit.domain_commit_id
    snapshot = kernel.scene_snapshot(fixture.hg_scene_id)
    assert snapshot.turn_counter == 1
    assert snapshot.committed_move_count == 1


def test_rejected_validation_leaves_no_commit_record(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    kernel.validate_move(
        ValidationRequest(
            inference_id="inf-5",
            hg_scene_id=fixture.hg_scene_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=_invalid_move(),
        )
    )
    snapshot = kernel.scene_snapshot(fixture.hg_scene_id)
    assert snapshot.committed_move_count == 0


def test_http_transport_round_trip(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/context/prepare",
            data=json.dumps(
                {
                    "hg_scene_id": fixture.hg_scene_id,
                    "inference_id": "inf-http",
                    "character_id": "Alice",
                    "role": "guest",
                    "turn_index": 0,
                    "attempt_index": 0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["manifest_id"]
        assert payload["contributions"]
    finally:
        server.shutdown()
        server.server_close()
