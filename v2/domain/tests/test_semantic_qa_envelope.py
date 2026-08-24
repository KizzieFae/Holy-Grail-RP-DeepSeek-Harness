"""Tests for hg_semantic_qa_result_v1 envelope (#25)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.authority_reference import CITATION_STATUS_UNKNOWN_REF  # noqa: E402
from domain.modules.semantic_qa_envelope import (  # noqa: E402
    SEMANTIC_QA_RESULT_SCHEMA,
    parse_semantic_qa_result,
)


def _base_payload(**overrides):
    payload = {
        "schema": SEMANTIC_QA_RESULT_SCHEMA,
        "evaluation_target_role": "director",
        "evaluation_pass_id": "eval-pass-1",
        "overall_result": "pass",
        "findings": [],
    }
    payload.update(overrides)
    return payload


def test_valid_parse_preserves_opaque_dimension() -> None:
    raw = _base_payload(
        findings=[
            {
                "dimension": "custom_director_dimension",
                "severity": "soft",
                "finding": "note",
                "rationale": "because",
            },
        ],
    )
    parsed = parse_semantic_qa_result(raw)
    assert parsed.ok is True
    assert parsed.result is not None
    assert parsed.result["findings"][0]["dimension"] == "custom_director_dimension"


def test_malformed_json_fails() -> None:
    parsed = parse_semantic_qa_result("{not-json")
    assert parsed.ok is False
    assert parsed.result is None


def test_missing_required_fields_fail() -> None:
    parsed = parse_semantic_qa_result({"schema": SEMANTIC_QA_RESULT_SCHEMA})
    assert parsed.ok is False


def test_unknown_hard_citation_does_not_downgrade_severity() -> None:
    raw = _base_payload(
        overall_result="reject_hard",
        findings=[
            {
                "dimension": "D1",
                "severity": "hard",
                "finding": "bad",
                "rationale": "why",
                "authoritative_citation": {"ref_id": "missing:ref"},
            },
        ],
    )
    parsed = parse_semantic_qa_result(raw, authority_references=[])
    assert parsed.ok is True
    assert parsed.result is not None
    assert parsed.result["findings"][0]["severity"] == "hard"
    assert parsed.citation_validations[0]["status"] == CITATION_STATUS_UNKNOWN_REF


def test_evaluation_target_role_and_pass_correlation_warnings() -> None:
    raw = _base_payload(
        evaluation_target_role="narrator",
        evaluation_pass_id="eval-pass-2",
    )
    parsed = parse_semantic_qa_result(
        raw,
        expected_evaluation_pass_id="eval-pass-1",
        expected_evaluation_target_role="director",
    )
    assert parsed.ok is True
    assert any("evaluation_pass_id" in warning for warning in parsed.parse_warnings)
    assert any("evaluation_target_role" in warning for warning in parsed.parse_warnings)


def test_invalid_overall_result_fails() -> None:
    raw = _base_payload(overall_result="maybe")
    parsed = parse_semantic_qa_result(raw)
    assert parsed.ok is False


def test_no_correction_request_field_required() -> None:
    raw = _base_payload()
    parsed = parse_semantic_qa_result(json.dumps(raw))
    assert parsed.ok is True
    assert parsed.result is not None
    assert "correction_request" not in parsed.result
