"""Tests for shared authority-reference infrastructure (#25)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.authority_reference import (  # noqa: E402
    CITATION_STATUS_ADVISORY_AUTHORITY_CLASS,
    CITATION_STATUS_MISSING_CITATION,
    CITATION_STATUS_UNKNOWN_REF,
    CITATION_STATUS_VALID,
    validate_authority_reference,
    validate_authority_references,
    validate_finding_citations,
)


def test_valid_authority_reference() -> None:
    ref = {
        "ref_id": "guardrail:player_agency",
        "kind": "guardrail",
        "authority_class": "authoritative",
        "label": "Player agency",
        "text": "Do not invent player behavior.",
    }
    assert validate_authority_reference(ref) == []


def test_unknown_citation_reports_without_severity_mutation() -> None:
    refs = [
        {
            "ref_id": "guardrail:player_agency",
            "kind": "guardrail",
            "authority_class": "authoritative",
            "label": "Player agency",
            "text": "Do not invent player behavior.",
        },
    ]
    findings = [
        {
            "dimension": "D1",
            "severity": "hard",
            "authoritative_citation": {"ref_id": "missing:ref"},
        },
    ]
    validations = validate_finding_citations(findings, refs)
    assert validations[0]["status"] == CITATION_STATUS_UNKNOWN_REF
    assert findings[0]["severity"] == "hard"


def test_advisory_reference_reports_class_without_promotion() -> None:
    refs = [
        {
            "ref_id": "derived:digest",
            "kind": "scene_digest",
            "authority_class": "advisory",
            "label": "Digest",
            "text": "Advisory only.",
        },
    ]
    findings = [
        {
            "dimension": "N1",
            "severity": "hard",
            "authoritative_citation": {"ref_id": "derived:digest"},
        },
    ]
    validations = validate_finding_citations(findings, refs)
    assert validations[0]["status"] == CITATION_STATUS_ADVISORY_AUTHORITY_CLASS
    assert validations[0]["resolved_authority_class"] == "advisory"


def test_missing_hard_citation_reported() -> None:
    validations = validate_finding_citations(
        [{"dimension": "D2", "severity": "hard"}],
        [],
    )
    assert validations[0]["status"] == CITATION_STATUS_MISSING_CITATION


def test_valid_citation_resolves_authority_class() -> None:
    refs = [
        {
            "ref_id": "continuity_fact:scene:location",
            "kind": "continuity_fact",
            "authority_class": "authoritative",
            "label": "Location",
            "text": "Dorm",
        },
    ]
    findings = [
        {
            "dimension": "D3",
            "severity": "hard",
            "authoritative_citation": {"ref_id": "continuity_fact:scene:location"},
        },
    ]
    validations = validate_finding_citations(findings, refs)
    assert validations[0]["status"] == CITATION_STATUS_VALID
    assert validations[0]["resolved_authority_class"] == "authoritative"


def test_validate_authority_references_rejects_duplicate_ref_id() -> None:
    refs = [
        {
            "ref_id": "a:1",
            "kind": "guardrail",
            "authority_class": "authoritative",
            "label": "A",
            "text": "one",
        },
        {
            "ref_id": "a:1",
            "kind": "guardrail",
            "authority_class": "authoritative",
            "label": "A duplicate",
            "text": "two",
        },
    ]
    normalized, errors = validate_authority_references(refs)
    assert len(normalized) == 1
    assert normalized[0]["ref_id"] == "a:1"
    assert any("duplicate ref_id" in err for err in errors)
