"""Issue #142 — Storyteller finalize HTTP transport pass-through for raw inference strings."""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import RoundStartRequest  # noqa: E402
from domain_api.http_transport import DomainApiHandler  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.storyteller_contract import (  # noqa: E402
    STORYTELLER_ASSESSMENT_SCHEMA,
    STORYTELLER_ORIENTATION_SCHEMA,
)


def _scene_round(kernel: DomainKernel) -> tuple[str, str]:
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    return scene_id, round_id


def _valid_orientation(*, hg_round_id: str) -> dict:
    return {
        "schema": STORYTELLER_ORIENTATION_SCHEMA,
        "orientation_id": "orient-http-1",
        "hg_round_id": hg_round_id,
        "turn_index": 0,
        "trigger": "round_start",
        "information_gaps": (
            "What tensions are active in the scene?",
            "Which relationships are under strain?",
        ),
        "temporal_focus": "current",
        "breadth_preference": "broad",
    }


def _valid_assessment() -> dict:
    return {
        "schema": STORYTELLER_ASSESSMENT_SCHEMA,
        "assessment_id": "assess-http-1",
        "observations": [
            {
                "text": "Trust fracture is narratively central.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
                "confidence": "likely",
            }
        ],
        "active_tensions": [
            {
                "label": "Betrayal strain",
                "interpretive_note": "Pressure without forcing confrontation.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "narrative_priorities": [
            {
                "focus": "Trust fracture",
                "why_it_matters": "Reconciliation or avoidance may become meaningful.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "progression_opportunities": [
            {
                "opportunity_label": "Confrontation or avoidance",
                "narrative_hook": "Either path may become meaningful.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "unresolved_threads": [
            {
                "thread_label": "Broken treaty seal",
                "neglect_risk": "May fade if not referenced again.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "uncertainty": [
            {
                "topic": "Hidden passage danger",
                "reason": "Bundle does not fully establish current risk level.",
                "confidence": "speculative",
            }
        ],
        "information_gaps": [
            {"question": "Who knows about the passage now?", "blocking_judgment": False}
        ],
        "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
    }


def _minimal_bundle(*, hg_round_id: str) -> dict:
    return {
        "bundle_id": "bundle-http-1",
        "request_id": "req-http-1",
        "hg_round_id": hg_round_id,
        "turn_index": 0,
        "consumer_role": "storyteller",
        "entries": [],
    }


@pytest.fixture()
def http_server():
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "kernel": kernel,
            "scene_id": scene_id,
            "round_id": round_id,
            "base_url": f"http://127.0.0.1:{port}",
        }
    finally:
        server.shutdown()
        server.server_close()


def _post_json(base_url: str, path: str, body: dict) -> tuple[int, dict]:
    import urllib.request

    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _orientation_finalize_body(
    *,
    scene_id: str,
    round_id: str,
    orientation_result,
) -> dict:
    body = {
        "hg_scene_id": scene_id,
        "hg_round_id": round_id,
        "inference_id": "inf-storyteller-orient-http",
    }
    if orientation_result is not ...:
        body["orientation_result"] = orientation_result
    return body


def _assessment_finalize_body(
    *,
    scene_id: str,
    round_id: str,
    orientation: dict,
    bundle: dict,
    assessment_result,
) -> dict:
    return {
        "hg_scene_id": scene_id,
        "hg_round_id": round_id,
        "inference_id": "inf-storyteller-assess-http",
        "orientation": orientation,
        "bundle": bundle,
        "assessment_result": assessment_result,
        "orientation_inference_id": "inf-storyteller-orient-http",
        "assessment_inference_id": "inf-storyteller-assess-http",
        "follow_up_request_ids": [],
    }


@pytest.mark.parametrize(
    ("orientation_result", "expected_reason"),
    [
        ("{not json", "parse_error:"),
        ("[1, 2]", "not_object"),
        ("42", "not_object"),
        ('"hello"', "not_object"),
        ('{"information_gaps": ["What is happening?"]}', "schema_mismatch"),
        (
            '{"schema": "wrong", "information_gaps": ["What is happening?"]}',
            "schema_mismatch",
        ),
        ("{}", "schema_mismatch"),
        (None, "schema_mismatch"),
        ("", "schema_mismatch"),
    ],
)
def test_storyteller_orientation_finalize_rejects_without_transport_400(
    http_server,
    orientation_result,
    expected_reason,
) -> None:
    body = _orientation_finalize_body(
        scene_id=http_server["scene_id"],
        round_id=http_server["round_id"],
        orientation_result=orientation_result,
    )
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/orientation/finalize",
        body,
    )
    assert status == 200
    assert payload["accepted"] is False
    assert payload["reason"].startswith(expected_reason) or payload["reason"] == expected_reason
    assert payload["knowledge_access_request"] is None
    assert "dictionary update sequence element" not in str(payload)


def test_storyteller_orientation_finalize_missing_key_rejects_without_transport_400(
    http_server,
) -> None:
    body = _orientation_finalize_body(
        scene_id=http_server["scene_id"],
        round_id=http_server["round_id"],
        orientation_result=...,
    )
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/orientation/finalize",
        body,
    )
    assert status == 200
    assert payload["accepted"] is False
    assert payload["reason"] == "schema_mismatch"


def test_storyteller_orientation_finalize_accepts_valid_object(http_server) -> None:
    orientation = _valid_orientation(hg_round_id=http_server["round_id"])
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/orientation/finalize",
        _orientation_finalize_body(
            scene_id=http_server["scene_id"],
            round_id=http_server["round_id"],
            orientation_result=orientation,
        ),
    )
    assert status == 200
    assert payload["accepted"] is True
    assert payload["knowledge_access_request"] is not None


def test_storyteller_orientation_finalize_accepts_valid_json_string(http_server) -> None:
    orientation = _valid_orientation(hg_round_id=http_server["round_id"])
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/orientation/finalize",
        _orientation_finalize_body(
            scene_id=http_server["scene_id"],
            round_id=http_server["round_id"],
            orientation_result=json.dumps(orientation),
        ),
    )
    assert status == 200
    assert payload["accepted"] is True


def test_storyteller_assessment_finalize_rejects_raw_string_without_transport_400(
    http_server,
) -> None:
    orientation = _valid_orientation(hg_round_id=http_server["round_id"])
    raw = json.dumps({"observations": [{"text": "missing schema wrapper"}]})
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/assessment/finalize",
        _assessment_finalize_body(
            scene_id=http_server["scene_id"],
            round_id=http_server["round_id"],
            orientation=orientation,
            bundle=_minimal_bundle(hg_round_id=http_server["round_id"]),
            assessment_result=raw,
        ),
    )
    assert status == 200
    assert payload["accepted"] is False
    assert payload["reason"] == "schema_mismatch"
    assert payload["package"] is None


def test_storyteller_assessment_finalize_accepts_valid_object(http_server) -> None:
    orientation = _valid_orientation(hg_round_id=http_server["round_id"])
    status, payload = _post_json(
        http_server["base_url"],
        "/v1/storyteller/assessment/finalize",
        _assessment_finalize_body(
            scene_id=http_server["scene_id"],
            round_id=http_server["round_id"],
            orientation=orientation,
            bundle=_minimal_bundle(hg_round_id=http_server["round_id"]),
            assessment_result=_valid_assessment(),
        ),
    )
    assert status == 200
    assert payload["accepted"] is True
    assert payload["package"] is not None
