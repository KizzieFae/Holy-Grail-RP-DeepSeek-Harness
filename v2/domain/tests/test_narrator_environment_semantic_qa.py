"""Environmental semantic-QA rubric coverage for #49 remediation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.narrator_semantic_qa_context import NARRATOR_SEMANTIC_QA_RUBRIC  # noqa: E402


@pytest.mark.parametrize(
    "dimension",
    [
        "nar_environmental_contradiction",
        "nar_environmental_under_description",
        "nar_environmental_repetition",
        "nar_environmental_invention",
    ],
)
def test_environmental_qa_dimensions_present(dimension: str) -> None:
    assert dimension in NARRATOR_SEMANTIC_QA_RUBRIC


def test_environmental_qa_rubric_requires_authoritative_citation_for_hard_findings() -> None:
    assert "authoritative_citation.ref_id" in NARRATOR_SEMANTIC_QA_RUBRIC
    assert "narrator_environment_baseline" in NARRATOR_SEMANTIC_QA_RUBRIC


def test_environmental_qa_covers_b1_misuse() -> None:
    assert "misuse of B1" in NARRATOR_SEMANTIC_QA_RUBRIC
