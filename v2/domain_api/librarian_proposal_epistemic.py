"""Epistemic contract helpers for Librarian S4b significance proposals (#80)."""

from __future__ import annotations

from typing import Any

from .librarian_proposal_contract import ProposalEvidenceCatalogItem

INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE = "utterance_occurrence"
INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE = "referenced_authoritative_proposition"

VALID_INTERPRETATION_SCOPES: frozenset[str] = frozenset(
    {
        INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
        INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
    }
)

PROPOSITION_AUTHORITY_OCCURRENCE_ONLY = "occurrence_only"
PROPOSITION_AUTHORITY_SCENARIO_PREMISE = "scenario_premise"
PROPOSITION_AUTHORITY_AUTHORED_ROLE_PRIVATE = "authored_role_private"
PROPOSITION_AUTHORITY_DERIVED_ESTABLISHED = "derived_established"
PROPOSITION_AUTHORITY_STRUCTURED_FACT = "structured_fact_ref"

REASON_MISSING_PROPOSITION_AUTHORITY = "missing_proposition_authority"
REASON_PROPOSITION_TRUTH_UNSUPPORTED = "proposition_truth_unsupported"
REASON_INVALID_INTERPRETATION_SCOPE = "invalid_interpretation_scope"

_MAX_PREMISE_EXCERPT = 2000
_MAX_ROLE_PRIVATE_EXCERPT = 1500

MAX_PREMISE_EXCERPT = _MAX_PREMISE_EXCERPT
MAX_ROLE_PRIVATE_EXCERPT = _MAX_ROLE_PRIVATE_EXCERPT

_OCCURRENCE_ONLY_CLASSES = frozenset(
    {
        PROPOSITION_AUTHORITY_OCCURRENCE_ONLY,
    }
)


def authority_metadata_for_class(
    proposition_authority_class: str,
    *,
    visibility_scope: str,
    world_truth_eligible: bool | None = None,
) -> dict[str, Any]:
    if world_truth_eligible is None:
        world_truth_eligible = proposition_authority_class not in _OCCURRENCE_ONLY_CLASSES and (
            proposition_authority_class
            not in {
                PROPOSITION_AUTHORITY_AUTHORED_ROLE_PRIVATE,
            }
        )
    return {
        "proposition_authority_class": proposition_authority_class,
        "world_truth_eligible": bool(world_truth_eligible),
        "visibility_scope": visibility_scope,
    }


def catalog_item_authority_metadata(item: ProposalEvidenceCatalogItem) -> dict[str, Any]:
    provenance = dict(item.provenance or {})
    raw = provenance.get("authority_metadata")
    if isinstance(raw, dict) and raw.get("proposition_authority_class"):
        return dict(raw)
    kind = str(item.evidence_kind or "").strip()
    if kind in {"public_event", "committed_move"}:
        return authority_metadata_for_class(
            PROPOSITION_AUTHORITY_OCCURRENCE_ONLY,
            visibility_scope=str(item.visibility_scope or "public"),
            world_truth_eligible=False,
        )
    if kind == "scenario_premise":
        return authority_metadata_for_class(
            PROPOSITION_AUTHORITY_SCENARIO_PREMISE,
            visibility_scope=str(item.visibility_scope or "public"),
            world_truth_eligible=True,
        )
    if kind == "authored_role_private":
        return authority_metadata_for_class(
            PROPOSITION_AUTHORITY_AUTHORED_ROLE_PRIVATE,
            visibility_scope=str(item.visibility_scope or "orchestration_only"),
            world_truth_eligible=False,
        )
    if kind == "derived_story_record":
        return authority_metadata_for_class(
            PROPOSITION_AUTHORITY_DERIVED_ESTABLISHED,
            visibility_scope=str(item.visibility_scope or "orchestration_only"),
            world_truth_eligible=True,
        )
    return authority_metadata_for_class(
        PROPOSITION_AUTHORITY_OCCURRENCE_ONLY,
        visibility_scope=str(item.visibility_scope or "orchestration_only"),
        world_truth_eligible=False,
    )


def is_world_truth_eligible_metadata(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("world_truth_eligible"))


def proposition_authority_refs_from_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("proposition_authority_refs")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def validate_revelation_significance_epistemic(
    payload: dict[str, Any],
    *,
    catalog: tuple[ProposalEvidenceCatalogItem, ...] | None,
) -> tuple[bool, str, tuple[str, ...]]:
    scope = str(payload.get("interpretation_scope", "") or "").strip()
    if scope not in VALID_INTERPRETATION_SCOPES:
        return (
            False,
            f"invalid_interpretation_scope:{scope or '<missing>'}",
            (REASON_INVALID_INTERPRETATION_SCOPE,),
        )

    if scope == INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE:
        return True, "", ()

    refs = proposition_authority_refs_from_payload(payload)
    if not refs:
        return (
            False,
            "missing_proposition_authority_refs",
            (REASON_MISSING_PROPOSITION_AUTHORITY,),
        )

    catalog_by_id = {item.anchor_id: item for item in (catalog or ())}
    world_eligible_count = 0
    for ref in refs:
        item = catalog_by_id.get(ref)
        if item is None:
            return (
                False,
                f"unknown_proposition_authority_ref:{ref}",
                (REASON_MISSING_PROPOSITION_AUTHORITY,),
            )
        metadata = catalog_item_authority_metadata(item)
        if is_world_truth_eligible_metadata(metadata):
            world_eligible_count += 1

    if world_eligible_count < 1:
        return (
            False,
            "proposition_truth_unsupported",
            (REASON_PROPOSITION_TRUTH_UNSUPPORTED,),
        )
    return True, "", ()


def sanitize_revelation_annotation_for_catalog(annotation: dict[str, Any]) -> dict[str, Any]:
    """Project scoped annotations for Librarian proposal catalogs; exclude invalid/missing scope."""
    if not isinstance(annotation, dict):
        return {}
    scope = str(annotation.get("interpretation_scope", "") or "").strip()
    if scope not in VALID_INTERPRETATION_SCOPES:
        return {}
    safe: dict[str, Any] = {
        "revelation_significance_level": annotation.get("revelation_significance_level"),
        "subject_character": annotation.get("subject_character"),
        "interpretation_scope": scope,
        "confidence": annotation.get("confidence"),
        "proposal_id": annotation.get("proposal_id"),
    }
    if scope == INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE:
        refs = annotation.get("proposition_authority_refs")
        if isinstance(refs, list):
            safe["proposition_authority_refs"] = [
                str(item).strip() for item in refs if str(item).strip()
            ]
    note = str(annotation.get("annotation_note", "") or "").strip()
    if note:
        safe["annotation_note"] = note
    return {key: value for key, value in safe.items() if value not in (None, "", [])}


def sanitize_revelation_significance_by_character(
    raw: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    sanitized: dict[str, dict[str, Any]] = {}
    for character_id, annotation in raw.items():
        if not str(character_id).strip() or not isinstance(annotation, dict):
            continue
        cleaned = sanitize_revelation_annotation_for_catalog(annotation)
        if cleaned:
            sanitized[str(character_id)] = cleaned
    return sanitized or None
