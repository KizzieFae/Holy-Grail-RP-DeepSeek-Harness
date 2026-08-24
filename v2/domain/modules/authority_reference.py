"""Shared authority-reference model for semantic QA (#25)."""

from __future__ import annotations

from typing import Any, Literal

SemanticQaAuthorityClass = Literal["authoritative", "derived", "advisory"]

SEMANTIC_QA_AUTHORITY_CLASSES: frozenset[str] = frozenset(
    {"authoritative", "derived", "advisory"},
)

CITATION_STATUS_VALID = "valid"
CITATION_STATUS_UNKNOWN_REF = "unknown_ref"
CITATION_STATUS_MISSING_CITATION = "missing_citation"
CITATION_STATUS_ADVISORY_AUTHORITY_CLASS = "advisory_authority_class"
CITATION_STATUS_DERIVED_AUTHORITY_CLASS = "derived_authority_class"

MAX_AUTHORITY_TEXT_LENGTH = 8000


def normalize_authority_class(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text in SEMANTIC_QA_AUTHORITY_CLASSES:
        return text
    return None


def validate_authority_reference(ref: Any) -> list[str]:
    """Structural validation for one authority reference record."""
    errors: list[str] = []
    if not isinstance(ref, dict):
        return ["authority reference must be an object"]

    ref_id = str(ref.get("ref_id") or ref.get("authority_ref_id") or "").strip()
    if not ref_id:
        errors.append("ref_id is required")

    kind = str(ref.get("kind") or "").strip()
    if not kind:
        errors.append("kind is required")

    authority_class = normalize_authority_class(ref.get("authority_class"))
    if authority_class is None:
        errors.append(
            "authority_class must be one of: authoritative, derived, advisory",
        )

    label = str(ref.get("label") or "").strip()
    if not label:
        errors.append("label is required")

    text = ref.get("text")
    if text is None or str(text).strip() == "":
        errors.append("text is required")
    elif len(str(text)) > MAX_AUTHORITY_TEXT_LENGTH:
        errors.append(f"text exceeds max length {MAX_AUTHORITY_TEXT_LENGTH}")

    return errors


def validate_authority_references(refs: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate a list of authority references; return normalized refs and errors."""
    if not isinstance(refs, list):
        return [], ["authority_references must be a list"]

    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, ref in enumerate(refs):
        item_errors = validate_authority_reference(ref)
        if item_errors:
            errors.extend([f"authority_references[{index}]: {msg}" for msg in item_errors])
            continue
        ref_id = str(ref.get("ref_id") or ref.get("authority_ref_id") or "").strip()
        if ref_id in seen_ids:
            errors.append(f"authority_references[{index}]: duplicate ref_id {ref_id}")
            continue
        seen_ids.add(ref_id)
        normalized.append(
            {
                "ref_id": ref_id,
                "kind": str(ref.get("kind") or "").strip(),
                "authority_class": normalize_authority_class(ref.get("authority_class")),
                "label": str(ref.get("label") or "").strip(),
                "text": str(ref.get("text") or ""),
                **(
                    {"provenance": dict(ref["provenance"])}
                    if isinstance(ref.get("provenance"), dict)
                    else {}
                ),
            },
        )
    return normalized, errors


def authority_reference_index(
    refs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for ref in refs:
        ref_id = str(ref.get("ref_id") or "").strip()
        if ref_id:
            index[ref_id] = ref
    return index


def validate_finding_citations(
    findings: list[dict[str, Any]],
    authority_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return citation-validation sidecar entries without mutating finding severity."""
    ref_index = authority_reference_index(authority_refs)
    validations: list[dict[str, Any]] = []

    for finding_index, finding in enumerate(findings):
        severity = str(finding.get("severity") or "").strip()
        citation = finding.get("authoritative_citation")
        ref_id = ""
        if isinstance(citation, dict):
            ref_id = str(
                citation.get("ref_id") or citation.get("authority_ref_id") or "",
            ).strip()

        if severity == "hard" and not ref_id:
            validations.append(
                {
                    "finding_index": finding_index,
                    "ref_id": None,
                    "status": CITATION_STATUS_MISSING_CITATION,
                    "resolved_authority_class": None,
                },
            )
            continue

        if not ref_id:
            continue

        resolved = ref_index.get(ref_id)
        if resolved is None:
            validations.append(
                {
                    "finding_index": finding_index,
                    "ref_id": ref_id,
                    "status": CITATION_STATUS_UNKNOWN_REF,
                    "resolved_authority_class": None,
                },
            )
            continue

        resolved_class = normalize_authority_class(resolved.get("authority_class"))
        status = CITATION_STATUS_VALID
        if resolved_class == "advisory":
            status = CITATION_STATUS_ADVISORY_AUTHORITY_CLASS
        elif resolved_class == "derived":
            status = CITATION_STATUS_DERIVED_AUTHORITY_CLASS

        validations.append(
            {
                "finding_index": finding_index,
                "ref_id": ref_id,
                "status": status,
                "resolved_authority_class": resolved_class,
            },
        )

    return validations
