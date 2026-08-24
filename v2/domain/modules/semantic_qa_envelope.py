"""Shared semantic-QA result envelope parser (#25)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .authority_reference import (
    validate_authority_references,
    validate_finding_citations,
)

SEMANTIC_QA_RESULT_SCHEMA = "hg_semantic_qa_result_v1"
VALID_EVALUATION_TARGET_ROLES = frozenset({"director", "narrator", "character"})
VALID_OVERALL_RESULTS = frozenset({"pass", "reject_soft", "reject_hard"})
VALID_SEVERITIES = frozenset({"hard", "soft"})


@dataclass(frozen=True)
class SemanticQaParseResult:
    ok: bool
    error: str | None
    result: dict[str, Any] | None
    citation_validations: tuple[dict[str, Any], ...] = ()
    parse_warnings: tuple[str, ...] = ()


def _load_json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("evaluator output not an object")
        return parsed
    raise ValueError("evaluator output must be JSON object or string")


def _normalize_finding(raw: Any, *, finding_index: int) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if not isinstance(raw, dict):
        warnings.append(f"findings[{finding_index}] is not an object")
        return None, warnings

    dimension = str(raw.get("dimension") or "").strip()
    if not dimension:
        warnings.append(f"findings[{finding_index}].dimension is required")
        return None, warnings

    severity = str(raw.get("severity") or "").strip()
    if severity not in VALID_SEVERITIES:
        warnings.append(
            f"findings[{finding_index}].severity must be hard or soft",
        )
        return None, warnings

    citation = raw.get("authoritative_citation")
    normalized_citation = None
    if isinstance(citation, dict):
        ref_id = str(
            citation.get("ref_id") or citation.get("authority_ref_id") or "",
        ).strip()
        if ref_id:
            normalized_citation = {"ref_id": ref_id}
    elif severity == "hard":
        warnings.append(
            f"findings[{finding_index}] hard severity requires authoritative_citation.ref_id",
        )

    finding = {
        "dimension": dimension,
        "severity": severity,
        "finding": str(raw.get("finding") or ""),
        "rationale": str(raw.get("rationale") or ""),
        "candidate_evidence": raw.get("candidate_evidence"),
        "authoritative_citation": normalized_citation,
    }
    return finding, warnings


def parse_semantic_qa_result(
    raw: Any,
    authority_references: list[dict[str, Any]] | None = None,
    *,
    expected_evaluation_pass_id: str | None = None,
    expected_evaluation_target_role: str | None = None,
) -> SemanticQaParseResult:
    """Parse hg_semantic_qa_result_v1 without applying role semantic policy."""
    try:
        parsed = _load_json_object(raw)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        return SemanticQaParseResult(ok=False, error=str(error), result=None)

    warnings: list[str] = []

    schema = str(parsed.get("schema") or "").strip()
    if schema != SEMANTIC_QA_RESULT_SCHEMA:
        return SemanticQaParseResult(
            ok=False,
            error=f"unsupported schema {schema or '<missing>'}",
            result=None,
        )

    evaluation_target_role = str(parsed.get("evaluation_target_role") or "").strip()
    if evaluation_target_role not in VALID_EVALUATION_TARGET_ROLES:
        return SemanticQaParseResult(
            ok=False,
            error="evaluation_target_role must be director, narrator, or character",
            result=None,
        )
    if (
        expected_evaluation_target_role
        and evaluation_target_role != expected_evaluation_target_role
    ):
        warnings.append(
            "evaluation_target_role does not match expected evaluation target",
        )

    evaluation_pass_id = str(parsed.get("evaluation_pass_id") or "").strip()
    if not evaluation_pass_id:
        return SemanticQaParseResult(
            ok=False,
            error="evaluation_pass_id is required",
            result=None,
        )
    if expected_evaluation_pass_id and evaluation_pass_id != expected_evaluation_pass_id:
        warnings.append("evaluation_pass_id does not match expected correlation id")

    overall_result = str(parsed.get("overall_result") or "").strip()
    if overall_result not in VALID_OVERALL_RESULTS:
        return SemanticQaParseResult(
            ok=False,
            error="overall_result must be pass, reject_soft, or reject_hard",
            result=None,
        )

    refs_input = authority_references if authority_references is not None else []
    normalized_refs, ref_errors = validate_authority_references(refs_input)
    if ref_errors:
        warnings.extend(ref_errors)

    findings_raw = parsed.get("findings")
    if findings_raw is None:
        findings_raw = []
    if not isinstance(findings_raw, list):
        return SemanticQaParseResult(
            ok=False,
            error="findings must be an array",
            result=None,
        )

    findings: list[dict[str, Any]] = []
    for index, item in enumerate(findings_raw):
        finding, finding_warnings = _normalize_finding(item, finding_index=index)
        warnings.extend(finding_warnings)
        if finding is not None:
            findings.append(finding)

    citation_validations = validate_finding_citations(findings, normalized_refs)

    evaluator_summary = parsed.get("evaluator_summary")
    if evaluator_summary is not None and not isinstance(evaluator_summary, str):
        warnings.append("evaluator_summary must be a string when present")

    residual = parsed.get("residual_soft_concerns")
    if residual is None:
        residual_list: list[Any] = []
    elif isinstance(residual, list):
        residual_list = [str(item) for item in residual]
    else:
        warnings.append("residual_soft_concerns must be an array when present")
        residual_list = []

    result = {
        "schema": SEMANTIC_QA_RESULT_SCHEMA,
        "evaluation_target_role": evaluation_target_role,
        "evaluation_pass_id": evaluation_pass_id,
        "overall_result": overall_result,
        "findings": findings,
        "evaluator_summary": str(evaluator_summary) if evaluator_summary else None,
        "residual_soft_concerns": residual_list,
    }

    return SemanticQaParseResult(
        ok=True,
        error=None,
        result=result,
        citation_validations=tuple(citation_validations),
        parse_warnings=tuple(warnings),
    )
