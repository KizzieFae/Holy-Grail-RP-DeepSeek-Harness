"""Deterministic Host validation of DSH Librarian proposal results (#34 S4a)."""

from __future__ import annotations

from typing import Any

from .librarian_proposal_contract import (
    LIBRARIAN_PROPOSAL_ORIGIN,
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    EvidenceAnchor,
    HostProposalBatchValidation,
    HostProposalItemValidation,
    LibrarianSemanticProposal,
    ProposalCommitBinding,
    ProposalEvidenceCatalogItem,
    ProposalProvenance,
    S4A_ACTIVE_PROPOSAL_KINDS,
    new_proposal_id,
    validate_proposal_payload_schema,
)
from .librarian_proposal_epistemic import validate_revelation_significance_epistemic

_VALID_CONFIDENCE = frozenset({"confirmed", "likely", "speculative"})
_PRESERVATION_SIGNAL_PREFIXES = (
    "preservation_signal",
    "storyteller_preservation",
    "attention_ref",
)


def _as_anchor_list(raw: Any) -> tuple[EvidenceAnchor, ...]:
    if not isinstance(raw, list):
        return ()
    anchors: list[EvidenceAnchor] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        anchor_id = str(item.get("anchor_id", "") or "").strip()
        kind = str(item.get("evidence_kind", "") or "").strip()
        if not anchor_id or not kind:
            continue
        anchors.append(
            EvidenceAnchor(
                anchor_id=anchor_id,
                evidence_kind=kind,  # type: ignore[arg-type]
                anchor_path=str(item.get("anchor_path", "") or "").strip() or None,
                anchor_commit_id=str(item.get("anchor_commit_id", "") or "").strip() or None,
            )
        )
    return tuple(anchors)


def parse_librarian_proposal_result(
    raw: Any,
    *,
    batch_id: str,
    commit_binding: ProposalCommitBinding,
    librarian_inference_id: str,
) -> tuple[tuple[LibrarianSemanticProposal, ...] | None, str]:
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, f"invalid_json:{exc.msg}"
    if not isinstance(raw, dict):
        return None, "malformed:not_object"
    schema = str(raw.get("schema", "") or "").strip()
    if schema != LIBRARIAN_PROPOSAL_RESULT_SCHEMA:
        return None, f"malformed:schema:{schema or '<missing>'}"

    proposals: list[LibrarianSemanticProposal] = []
    for index, item in enumerate(raw.get("proposals") or []):
        if not isinstance(item, dict):
            return None, f"malformed:proposals[{index}]"
        proposal_kind = str(item.get("proposal_kind", "") or "").strip()
        derivation = str(item.get("derivation_summary", "") or "").strip()
        confidence = str(item.get("confidence", "") or "").strip()
        payload = item.get("proposed_payload")
        anchors = _as_anchor_list(item.get("evidence_anchors"))
        if not proposal_kind or not derivation or confidence not in _VALID_CONFIDENCE:
            return None, f"malformed:proposals[{index}].required_fields"
        if not isinstance(payload, dict):
            return None, f"malformed:proposals[{index}].proposed_payload"
        proposal_id = str(item.get("proposal_id", "") or "").strip() or new_proposal_id()
        affected_entities = tuple(
            str(x).strip() for x in (item.get("affected_entities") or []) if str(x).strip()
        )
        affected_state_classes = tuple(
            str(x).strip()
            for x in (item.get("affected_state_classes") or [])
            if str(x).strip()
        )
        proposals.append(
            LibrarianSemanticProposal(
                proposal_id=proposal_id,
                proposal_batch_id=batch_id,
                proposal_origin=LIBRARIAN_PROPOSAL_ORIGIN,
                proposal_kind=proposal_kind,  # type: ignore[arg-type]
                evidence_anchors=anchors,
                derivation_summary=derivation,
                confidence=confidence,  # type: ignore[arg-type]
                proposed_payload=dict(payload),
                commit_binding=commit_binding,
                provenance=ProposalProvenance(
                    librarian_inference_id=librarian_inference_id,
                    source_bundle_id=(
                        str(item.get("source_bundle_id", "") or "").strip() or None
                    ),
                ),
                affected_entities=affected_entities,
                affected_state_classes=affected_state_classes,
            )
        )
    return tuple(proposals), ""


def _anchor_is_preservation_signal(anchor: EvidenceAnchor) -> bool:
    anchor_id = str(anchor.anchor_id or "").lower()
    kind = str(anchor.evidence_kind or "").lower()
    path = str(anchor.anchor_path or "").lower()
    if kind == "preservation_signal":
        return True
    for prefix in _PRESERVATION_SIGNAL_PREFIXES:
        if anchor_id.startswith(prefix) or path.startswith(prefix):
            return True
    return False


def _catalog_index(
    catalog: tuple[ProposalEvidenceCatalogItem, ...],
) -> dict[str, ProposalEvidenceCatalogItem]:
    return {item.anchor_id: item for item in catalog}


def validate_host_proposal_item(
    proposal: LibrarianSemanticProposal,
    *,
    catalog: tuple[ProposalEvidenceCatalogItem, ...],
    domain_commit_id: str,
) -> HostProposalItemValidation:
    codes: list[str] = []
    if not proposal.evidence_anchors:
        codes.append("missing_evidence_anchors")
    catalog_by_id = _catalog_index(catalog)
    for anchor in proposal.evidence_anchors:
        if _anchor_is_preservation_signal(anchor):
            codes.append("preservation_signal_not_evidence")
        item = catalog_by_id.get(anchor.anchor_id)
        if item is None:
            codes.append("unknown_evidence_anchor")
            continue
        if (
            anchor.anchor_commit_id
            and anchor.anchor_commit_id != domain_commit_id
            and item.anchor_commit_id
            and anchor.anchor_commit_id != item.anchor_commit_id
        ):
            codes.append("anchor_outside_commit_closure")
        if item.authority_class == "suggestive" and proposal.confidence == "confirmed":
            if proposal.proposal_kind not in {
                "persistence_promotion_candidate",
                "knowledge_propagation_augmentation",
            }:
                codes.append("authority_elevation_attempt")
    ok, reason, payload_codes = validate_proposal_payload_schema(
        str(proposal.proposal_kind),
        proposal.proposed_payload,
    )
    if not ok:
        codes.extend(payload_codes)
    if proposal.proposal_kind not in S4A_ACTIVE_PROPOSAL_KINDS:
        codes.append("invalid_proposal_kind")
    if proposal.proposed_payload.get("direct_continuity_mutation") is True:
        codes.append("direct_mutation_attempt")
    if proposal.proposed_payload.get("manufactured_fact"):
        codes.append("manufactured_fact_ungrounded")
    if str(proposal.proposal_kind) == "knowledge_revelation_significance":
        event_ref = str(proposal.proposed_payload.get("event_ref", "") or "").strip()
        if event_ref:
            matched = False
            for item in catalog:
                if str(item.evidence_kind) != "public_event":
                    continue
                provenance = dict(item.provenance or {})
                event_id = str(provenance.get("event_id", "") or "").strip()
                if event_ref in {event_id, item.stable_ref}:
                    matched = True
                    break
            if not matched:
                codes.append("unknown_event_reference")
        epistemic_ok, _detail, epistemic_codes = validate_revelation_significance_epistemic(
            proposal.proposed_payload,
            catalog=catalog,
        )
        if not epistemic_ok:
            codes.extend(epistemic_codes)
    deduped = tuple(dict.fromkeys(codes))
    accepted = not deduped
    return HostProposalItemValidation(
        proposal_id=proposal.proposal_id,
        accepted=accepted,
        reason=reason or ("accepted" if accepted else "host_validation_failed"),
        rejection_codes=deduped,
    )


def validate_host_proposal_batch(
    proposals: tuple[LibrarianSemanticProposal, ...],
    *,
    catalog: tuple[ProposalEvidenceCatalogItem, ...],
    domain_commit_id: str,
) -> HostProposalBatchValidation:
    item_results = tuple(
        validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=domain_commit_id,
        )
        for proposal in proposals
    )
    accepted = all(item.accepted for item in item_results) if item_results else False
    codes: list[str] = []
    for item in item_results:
        codes.extend(item.rejection_codes)
    deduped = tuple(dict.fromkeys(codes))
    return HostProposalBatchValidation(
        accepted=accepted and bool(proposals),
        reason="accepted" if accepted and proposals else "host_validation_failed",
        item_results=item_results,
        rejection_codes=deduped,
    )
