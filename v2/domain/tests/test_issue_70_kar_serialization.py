"""Issue #70 — Narrator environmental KAR JSON serialization regression."""

from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorEnvironmentCognitionPrepareRequest,
)
from domain_api.http_transport import DomainApiHandler  # noqa: E402
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.librarian_contract import ALL_INFORMATION_CLASSES  # noqa: E402
from domain_api.narrator_environment_context import build_environment_knowledge_requests  # noqa: E402
from domain.tests.test_issue_54_context_decomposition import _scene_round  # noqa: E402


def _commit_alice_turn(kernel: DomainKernel, scene_id: str, round_id: str, *, inference_id: str):
    commit = kernel.commit_move(
        CommitRequest(
            inference_id=inference_id,
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice acts.",
                "environment_event": "",
                "tension_shift": "steady",
            },
            expected_turn_index=0,
        )
    )
    assert commit.domain_commit_id is not None
    return commit


def _n1_raw_with_needs() -> dict:
    return {
        "baseline_sufficient": False,
        "information_needs": [
            {
                "need_id": "need-70",
                "question": "What is behind the door?",
                "category": "environmental_detail",
            }
        ],
    }


def test_knowledge_access_request_to_dict_converts_frozensets_deterministically() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = _commit_alice_turn(kernel, scene_id, round_id, inference_id="inf-kar-70")
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    turn_record = next(
        t for t in rnd.character_turns if t.domain_commit_id == commit.domain_commit_id
    )
    req = NarratorEnvironmentCognitionPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-kar-70",
        character_id="Alice",
        domain_commit_id=commit.domain_commit_id,
        continuity_turn_index=commit.continuity_turn_index or 1,
    )
    n1_raw = _n1_raw_with_needs()
    kar_list = build_environment_knowledge_requests(
        fixture, rnd, turn_record, req, n1_raw=n1_raw
    )
    assert len(kar_list) == 1
    payload = kar_list[0]
    assert isinstance(payload["requested_information_classes"], list)
    assert payload["requested_information_classes"] == sorted(
        {"authored_static", "compiled_index", "story_derived"}
    )
    assert isinstance(payload["host_allowed_information_classes"], list)
    assert payload["host_allowed_information_classes"] == sorted(ALL_INFORMATION_CLASSES)
    assert isinstance(payload["exclude_source_tiers"], list)
    json.dumps(payload)


def test_build_environment_knowledge_requests_json_serializable() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = _commit_alice_turn(kernel, scene_id, round_id, inference_id="inf-kar-70b")
    req = NarratorEnvironmentCognitionPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-kar-70b",
        character_id="Alice",
        domain_commit_id=commit.domain_commit_id,
        continuity_turn_index=commit.continuity_turn_index or 1,
    )
    n1_raw = _n1_raw_with_needs()
    via_kernel = kernel.build_narrator_environment_knowledge_requests(req, n1_raw=n1_raw)
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    turn_record = next(
        t for t in rnd.character_turns if t.domain_commit_id == commit.domain_commit_id
    )
    via_module = build_environment_knowledge_requests(
        fixture, rnd, turn_record, req, n1_raw=n1_raw
    )
    assert via_kernel == via_module
    assert len(via_kernel) == 1
    json.dumps(via_kernel)
    json.dumps({"knowledge_access_requests": via_kernel})


def test_http_narrator_environment_knowledge_requests_build_serializes() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = _commit_alice_turn(kernel, scene_id, round_id, inference_id="inf-http-kar-70")
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/narrator/environment/knowledge-requests/build",
            data=json.dumps(
                {
                    "hg_scene_id": scene_id,
                    "hg_round_id": round_id,
                    "inference_id": "inf-http-kar-70",
                    "character_id": "Alice",
                    "domain_commit_id": commit.domain_commit_id,
                    "continuity_turn_index": commit.continuity_turn_index or 1,
                    "n1_result": _n1_raw_with_needs(),
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert len(payload["knowledge_access_requests"]) == 1
        kar = payload["knowledge_access_requests"][0]
        assert isinstance(kar["requested_information_classes"], list)
        assert isinstance(kar["host_allowed_information_classes"], list)
        json.dumps(payload)
    finally:
        server.shutdown()
        server.server_close()
